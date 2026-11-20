"""Build ordinary-language table jobs and independent SQLite grades."""
import csv
from hashlib import sha256
import io
import json
from pathlib import Path
import sqlite3


HERE = Path(__file__).resolve().parent
CONTEXTS = {
    "orchard": ("yard", "shift", "crates", "minutes", ["Cedar","Maple","Pine"], ["day","night"]),
    "helpdesk": ("desk", "channel", "tickets", "minutes", ["Aster","Birch","Elm"], ["web","phone"]),
    "clinic": ("ward", "period", "visits", "staff", ["North","South","East"], ["early","late"]),
}
# Each position describes group, category, quantity and a different numerical column.
VARIANTS = {
    "morning": [(0,0,4,9),(1,1,13,5),(0,1,3,8),(2,0,15,2),(1,0,1,7),(0,0,6,14),
                (2,1,0,4),(2,0,4,6),(1,1,7,4),(0,0,5,12),(1,1,2,3),(2,1,5,4),(0,1,4,3)],
    "evening": [(2,1,11,9),(0,1,16,8),(2,0,3,8),(1,0,9,2),(1,1,14,17),(1,0,2,9),
                (0,1,7,4),(2,0,8,14),(1,0,4,7),(2,0,6,5),(1,1,5,6),(2,0,17,8),
                (0,0,11,4),(1,0,3,3),(2,1,15,12)],
}
# The SQL is only ever provided to the examiner.
JOBS = [
 ("fs_o","filtered-sum","orchard","How many crates are there in total on the night shift?","SELECT SUM(crates) FROM t WHERE shift='night'","scalar"),
 ("fs_h","filtered-sum","helpdesk","For the web channel, add up the tickets. Give me just the total.","SELECT SUM(tickets) FROM t WHERE channel='web'","scalar"),
 ("fs_c","filtered-sum","clinic","What's the total number of visits during the early period?","SELECT SUM(visits) FROM t WHERE period='early'","scalar"),
 ("gc_o","grouped-count","orchard","Give me the number of rows for each yard.","SELECT yard,COUNT(*) FROM t GROUP BY yard","map"),
 ("gc_h","grouped-count","helpdesk","Count entries by desk, with one count for each desk.","SELECT desk,COUNT(*) FROM t GROUP BY desk","map"),
 ("gc_c","grouped-count","clinic","How many records does each ward have? Count records, including repeat observations.","SELECT ward,COUNT(*) FROM t GROUP BY ward","map"),
 ("fgs_o","filtered-group-sum","orchard","For the day shift only, total crates by yard.","SELECT yard,SUM(crates) FROM t WHERE shift='day' GROUP BY yard","map"),
 ("fgs_h","filtered-group-sum","helpdesk","I need the sum of tickets for each desk, using only the phone channel.","SELECT desk,SUM(tickets) FROM t WHERE channel='phone' GROUP BY desk","map"),
 ("fgs_c","filtered-group-sum","clinic","During the late period, how many visits in total did each ward record?","SELECT ward,SUM(visits) FROM t WHERE period='late' GROUP BY ward","map"),
 ("gca_o","rank-group-count","orchard","Which yard appears in the most rows? Break ties by choosing the alphabetically first yard.","SELECT yard FROM t GROUP BY yard ORDER BY COUNT(*) DESC,yard ASC LIMIT 1","scalar"),
 ("gca_h","rank-group-count","helpdesk","Name the desk with the lowest number of entries. In a tie, choose the alphabetically first desk.","SELECT desk FROM t GROUP BY desk ORDER BY COUNT(*) ASC,desk ASC LIMIT 1","scalar"),
 ("gca_c","rank-group-count","clinic","Which ward has the most records? Pick the alphabetically earliest name if the counts tie.","SELECT ward FROM t GROUP BY ward ORDER BY COUNT(*) DESC,ward ASC LIMIT 1","scalar"),
 ("fgca_o","filtered-rank-count","orchard","On the day shift, which yard has the fewest rows? For equal counts use the alphabetically first yard.","SELECT yard FROM t WHERE shift='day' GROUP BY yard ORDER BY COUNT(*) ASC,yard ASC LIMIT 1","scalar"),
 ("fgca_h","filtered-rank-count","helpdesk","In the phone channel only, name the desk with the most entries. Break a tie alphabetically, earliest first.","SELECT desk FROM t WHERE channel='phone' GROUP BY desk ORDER BY COUNT(*) DESC,desk ASC LIMIT 1","scalar"),
 ("fgca_c","filtered-rank-count","clinic","Among late records, which ward shows up least often? Choose the alphabetically first ward in a tie.","SELECT ward FROM t WHERE period='late' GROUP BY ward ORDER BY COUNT(*) ASC,ward ASC LIMIT 1","scalar"),
 ("fgsa_o","filtered-rank-sum","orchard","For the night shift, which yard has the greatest total crates? Resolve equal totals using the alphabetically first yard.","SELECT yard FROM t WHERE shift='night' GROUP BY yard ORDER BY SUM(crates) DESC,yard ASC LIMIT 1","scalar"),
 ("fgsa_h","filtered-rank-sum","helpdesk","Looking only at web entries, give me the desk with the smallest sum of tickets. Ties go to the alphabetically first desk.","SELECT desk FROM t WHERE channel='web' GROUP BY desk ORDER BY SUM(tickets) ASC,desk ASC LIMIT 1","scalar"),
 ("fgsa_c","filtered-rank-sum","clinic","Which ward recorded the most total visits in the early period? Pick the alphabetically first ward if totals are equal.","SELECT ward FROM t WHERE period='early' GROUP BY ward ORDER BY SUM(visits) DESC,ward ASC LIMIT 1","scalar"),
 ("a_o","anchor","orchard","How many rows are in this table?","SELECT COUNT(*) FROM t","scalar"),
 ("a_h","anchor","helpdesk","What is the total of the tickets column?","SELECT SUM(tickets) FROM t","scalar"),
 ("a_c","anchor","clinic","Count the rows for the late period.","SELECT COUNT(*) FROM t WHERE period='late'","scalar"),
 ("x_o","adjacent","orchard","How many distinct yards appear in this table?","SELECT COUNT(DISTINCT yard) FROM t","scalar"),
 ("x_h","adjacent","helpdesk","Across all channels, how many desk entries have more than seven tickets?","SELECT COUNT(*) FROM t WHERE tickets>7","scalar"),
 ("x_c","adjacent","clinic","What is the median number of visits per record, using all records?","SELECT visits FROM t ORDER BY visits LIMIT 1 OFFSET (SELECT COUNT(*)/2 FROM t)","scalar"),
 ("q_o","clarify","orchard","Which yard is the best? I haven't chosen whether to use total crates or minutes worked.",None,"defer"),
 ("q_h","clarify","helpdesk","How many unresolved tickets do we have? The table only lists ticket counts and doesn't give a resolution status.",None,"defer"),
 ("q_c","clarify","clinic","What is the total revenue from all visits? I don't know the billing rate and it isn't in the table.",None,"defer"),
]
PRIMARY = {j[1] for j in JOBS} - {"anchor","adjacent","clarify"}


def build(directory=HERE):
    cases, keys, tables = [], {}, {}
    databases = {}
    for source, (group, category, amount, spare, groups, categories) in CONTEXTS.items():
        for edition, records in VARIANTS.items():
            table = f"{source}-{edition}"
            columns = (group,category,amount,spare)
            if edition == 'evening':
                columns = (spare, group, amount, category)
            b = io.StringIO(newline="")
            writer = csv.DictWriter(b,fieldnames=columns,lineterminator="\n")
            writer.writeheader()
            decoded = []
            for g,c,a,n in records:
                row = {group:groups[g],category:categories[c],amount:a,spare:n}
                writer.writerow(row)
                decoded.append(row)
            tables[table] = {"csv":b.getvalue(),"rows":decoded}
            db = sqlite3.connect(":memory:")
            db.execute(f"CREATE TABLE t({group} TEXT,{category} TEXT,{amount} INTEGER,{spare} INTEGER)")
            db.executemany(f"INSERT INTO t VALUES (:{group},:{category},:{amount},:{spare})", decoded)
            databases[table] = db
    for ident, pattern, source, question, sql, output in JOBS:
        request = {"id":ident,"pattern":pattern,"request":question,"tables":[]}
        for edition in VARIANTS:
            table = f"{source}-{edition}"
            request["tables"].append(table)
            expected = None
            if sql is not None:
                rows = databases[table].execute(sql).fetchall()
                expected = dict(rows) if output=="map" else rows[0][0]
            keys[f"{ident}/{table}"] = {"output":output, "value":expected}
        cases.append(request)
    assert len(cases)==27 and len(keys)==54 and len(PRIMARY)==6
    for name, data in (("requests.json",cases),("tables.json",tables),("keys.json",keys)):
        (directory / name).write_text(json.dumps(data,indent=2,ensure_ascii=False)+"\n")
    for db in databases.values():
        db.close()


if __name__ == "__main__":
    build()

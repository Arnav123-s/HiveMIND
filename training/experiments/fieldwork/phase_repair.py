"""Repair a model's multi-stage worker with generic aggregation and CSV serialization edits."""

import argparse
import ast
import copy
import csv
import io
import json
import random
import sqlite3
from pathlib import Path

from .campaign import fingerprint, read, save
from .grade import grade
from .guest import Guest
from .stages import assemble, evaluate_phase, examples
from .work import matches


FORMATS = {"summary.csv": "csv", "audit.json": "json"}
CSV_HELPER = """import csv as _csv, io as _io
def _field_csv_row(*fields):
    buf = _io.StringIO()
    _csv.writer(buf,lineterminator='\\n').writerow(fields)
    return buf.getvalue()[:-1]
"""


def mutations(source):
    tree = ast.parse(source)
    for i, node in enumerate(ast.walk(tree)):
        replacement = None
        helper = ""
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "sum"
            and len(node.args) == 1
        ):
            comp = node.args[0]
            if (
                isinstance(comp, (ast.GeneratorExp, ast.ListComp))
                and len(comp.generators) == 1
                and not comp.generators[0].ifs
            ):
                replacement = ast.Call(
                    func=ast.Name(id="len", ctx=ast.Load()), args=[comp.generators[0].iter], keywords=[]
                )
                edit = "sum of projected values to number of rows"
        elif isinstance(node, ast.JoinedStr) and len(node.values) >= 3 and len(node.values) % 2:
            exprs = node.values[::2]
            if all(
                isinstance(v, ast.FormattedValue) and v.conversion == -1 and v.format_spec is None
                for v in exprs
            ) and all(isinstance(v, ast.Constant) and v.value == "," for v in node.values[1::2]):
                replacement = ast.Call(
                    func=ast.Name(id="_field_csv_row", ctx=ast.Load()),
                    args=[v.value for v in exprs],
                    keywords=[],
                )
                helper = CSV_HELPER
                edit = "comma-separated fields to CSV writer"
        if replacement is not None:
            other = copy.deepcopy(tree)
            target = list(ast.walk(other))[i]

            class Replace(ast.NodeTransformer):
                def generic_visit(self, n):
                    return copy.deepcopy(replacement) if n is target else super().generic_visit(n)

            changed = Replace().visit(other)
            yield f"{edit} at line {node.lineno}", helper + ast.unparse(ast.fix_missing_locations(changed))


def improve(guest, source, demos):
    public, fields, feedback = evaluate_phase(guest, source, demos, FORMATS)
    parent = fingerprint(source)
    trace = []
    for _ in range(2):
        if public == len(demos):
            break
        best = None
        for edit, child in mutations(source):
            passed, parts, why = evaluate_phase(guest, child, demos, FORMATS)
            trace.append(
                dict(
                    edit=edit,
                    parent=fingerprint(source),
                    child=fingerprint(child),
                    passed=passed,
                    fields=parts,
                )
            )
            if (passed, parts) > (public, fields) and (best is None or (passed, parts) > best[:2]):
                best = passed, parts, child, why
            if passed == len(demos):
                break
        if best is None:
            break
        public, fields, source, feedback = best
    return dict(
        source=source,
        digest=fingerprint(source),
        parent=parent,
        passed=public,
        fields=fields,
        public=len(demos),
        feedback=feedback,
        trace=trace,
    )


def oracle(events, excluded, minimum):
    with sqlite3.connect(":memory:") as db:
        db.execute("create table samples(t text,r integer,z text,g integer,s text)")
        db.executemany("insert into samples values(?,?,?,?,?)", events)
        db.execute("""create view top_rows as select distinct a.* from samples a join
            (select t,max(r) as r from samples group by t) b on a.t=b.t and a.r=b.r""")
        db.execute("""create view kept as select t,r,z,g from top_rows where s='ok'
            and t not in (select t from top_rows group by t having count(*)>1)""")
        kept = [list(v) for v in db.execute("select * from kept order by t")]
        conflicts = [
            r[0] for r in db.execute("select t from top_rows group by t having count(*)>1 order by t")
        ]
        report = list(
            db.execute(
                """select z,count(*),sum(g) as mass from kept where z<>?
              group by z having count(*)>=? order by mass desc,z""",
                (excluded, minimum),
            )
        )
    buf = io.StringIO()
    csv.writer(buf, lineterminator="\n").writerows([["zone", "count", "grams"], *report])
    return {"kept": kept, "conflicts": conflicts}, {
        "summary.csv": buf.getvalue(),
        "audit.json": json.dumps({"conflicts": conflicts, "kept_count": len(kept)}),
    }


def transfer(guest, program, seed):
    import tempfile
    from .work import finish_files

    rng = random.Random(seed)
    allcases = []
    for i in range(96):
        zones = ["Alto", "East Ridge", "Cove, North", 'Mesa "B"', "zone_4"]
        events = []
        for j in range(rng.randrange(32)):
            key = f"S{rng.randrange(10)}-{j}"
            rev = rng.randrange(-2, 8)
            record = [
                key,
                rev,
                rng.choice(zones),
                rng.randrange(0, 12),
                rng.choice(["ok", "ok", "ok", "void"]),
            ]
            events.extend([record.copy() for _ in range(rng.randrange(1, 4))])
            if rng.random() < 0.3:
                events.append([key, rev - 1, rng.choice(zones), 3, "ok"])
            if rng.random() < 0.24:
                events.append([key, rev, rng.choice(zones), rng.randrange(12), "ok"])
        rng.shuffle(events)
        excluded, minimum = rng.choice(zones + ["elsewhere"]), rng.randrange(1, 5)
        snap, files = oracle(events, excluded, minimum)
        allcases.append(
            (
                dict(phase="intake", events=events),
                snap,
                dict(phase="revise", exclude=excluded, minimum=minimum),
                files,
            )
        )
    first = guest.run(program, [c[0] for c in allcases], fuel=22_000_000_000)[0]
    rows = []
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        inputs = []
        ids = []
        for i, (c, row) in enumerate(zip(allcases, first)):
            ok = row.get("value") == c[1]
            rows.append(dict(intake=ok, files=False))
            if ok:
                finish_files(base, str(i), {"snapshot.json": json.dumps(row["value"])}, ["snapshot.json"])
                inputs.append(
                    dict(c[2], snapshot=json.loads((base / str(i) / "snapshot.json").read_bytes()))
                )
                ids.append(i)
        revised = guest.run(program, inputs, fuel=22_000_000_000)[0]
        for i, row in zip(ids, revised):
            val = row.get("value")
            if (
                isinstance(val, dict)
                and set(val) == set(FORMATS)
                and all(isinstance(v, str) for v in val.values())
            ):
                ident = "report-" + str(i)
                finish_files(base, ident, val, list(FORMATS))
                opened = {k: (base / ident / k).read_text() for k in FORMATS}
                rows[i]["files"] = matches(opened, allcases[i][3], FORMATS)
    return dict(
        seed=seed,
        cases=len(rows),
        intake=sum(r["intake"] for r in rows),
        files=sum(r["files"] for r in rows),
        rows=rows,
    )


def comma_example():
    events = [["t0", 1, "A, B", 6, "ok"], ["t1", 1, "A, B", 4, "ok"], ["t2", 1, "West", 1, "void"]]
    snap, files = oracle(events, "Elsewhere", 1)
    return dict(input=dict(phase="revise", exclude="Elsewhere", minimum=1, snapshot=snap), output=files)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for k in ("sdk", "phases", "out"):
        p.add_argument("--" + k, type=Path, required=True)
    args = p.parse_args()
    g = Guest(args.sdk)
    intake = read(args.phases / "intake.json")
    writer = read(args.phases / "revise.json")
    demos = examples()["revise"]
    edge = comma_example()
    for arm, teaching in (("standard", demos), ("csv", [*demos, edge])):
        learned = improve(g, writer["source"], teaching)
        source = assemble({"intake": intake, "revise": learned})
        dest = args.out / arm
        save(
            dest / "program.json",
            dict(source=source, digest=fingerprint(source), intake=intake["digest"], revise=learned),
        )
        for split in ("exam", "confirmation"):
            result = grade(g, "ledger", source, split)
            save(dest / (split + ".json"), result)
        for seed in (311701, 982541):
            result = transfer(g, source, seed)
            save(dest / (str(seed) + ".json"), result)
            print(arm, learned["passed"], seed, result["files"], flush=True)


if __name__ == "__main__":
    main()

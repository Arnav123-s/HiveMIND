"""Reproduce the separately authored confirmation cases and oracle keys. Standard library only."""
import hashlib
import json
import random
from pathlib import Path
from textwrap import dedent

ROOT = Path(__file__).resolve().parent
SEED = 719263844
SPLITS = {"public": 5, "validation": 7, "private": 16}


def values(r, span, *, low=1, high=11):
    return [r.randint(low, high) for _ in range(span)]


def total(items):
    answer = 0
    for n in items:
        answer += n
    return answer


def tally(items):
    answer = 0
    for _ in items:
        answer += 1
    return answer


def greenhouse(r, split, i):
    n = r.randint(1, 10) if split != "private" else r.randint(1, 24)
    return {"trays": values(r, n, low=0, high=18 if split != "private" else 50)}


def choir(r, split, i):
    return {"batch_sizes": values(r, r.randint(2, 9), high=22)}


def archive(r, split, i):
    lots = [{"copies": r.randint(1, 15), "cleared": r.choice([True, False]), "shelf": r.randint(1, 40)}
            for _ in range(r.randint(2, 10))]
    lots[0]["cleared"] = True
    return {"lots": lots, "reading_room": r.choice(["North", "South"])}


def threshold_input(field, limit, *, signed=False):
    def build(r, split, i):
        cut = r.randint(-18 if signed else 2, 65)
        readings = [cut, cut + 1, cut - 1]
        readings += values(r, r.randint(1, 8), low=-45 if signed else 0, high=130)
        if split == "private" and i % 3 == 0:
            readings += [cut] * (2 + i)
        r.shuffle(readings)
        return {field: readings, limit: cut}
    return build


def spacers(r, split, i):
    return {"bundles": values(r, r.randint(2, 9), high=23),
            "loose_piece_ids": r.sample(range(50, 5000), r.randint(1, 7))}


def stage(r, split, i):
    first = r.randint(5, 32)
    last = first + r.randint(3, 30)
    marks = [first, last, first - 1, last + 1, first + 1]
    marks += values(r, r.randint(1, 6), high=80)
    r.shuffle(marks)
    return {"opening": first, "closing": last, "cue_frames": marks}


def orchard(r, split, i):
    keys = r.sample(["Nell", "Kai", "Hugo", "Ira", "Ari", "Jo", "Rae", "Ollie", "Paz"], r.randint(2, 7))
    return {"fruit": r.choice(["apple", "plum", "pear"]),
            "pickers": {key: {"full_crates": r.randint(0, 20), "row": r.randint(1, 120)} for key in keys}}


def strings(r, split, i):
    packs = values(r, r.randint(2, 11), low=1, high=9)
    if split == "private":
        packs += [0, r.choice([43, 177, 1500])]  # damaged empty box and wholesale pack
    r.shuffle(packs)
    return {"bench": {"sealed_packs": packs, "notes": r.choice(["blue", "green", "red"])},
            "individual_strings": r.randint(0, 23)}


def cinema(r, split, i):
    start = r.randint(1150, 1439) if i % 2 == 0 else r.randint(10, 850)
    duration = r.randint(290, 480) if i % 2 == 0 else r.randint(1, 220)
    return {"start_minute": start, "end_minute": (start + duration) % 1440}


def roll(r, split, i):
    return {"rewinds": r.randint(2, 70), "cap": r.randint(3, 90), "leader_metres": r.randint(1, 35)}


def thaw(r, split, i):
    return {"tags": [{"temp": t, "open": r.choice([True, False])}
                     for t in values(r, r.randint(2, 13), low=-25, high=25)]}


def nursery(r, split, i):
    return {"packs": values(r, r.randint(1, 8), low=0, high=50),
            "individuals": r.sample(range(10, 5000), r.randint(0, 8))}


def tower(r, split, i):
    return threshold_input("gusts", "alarm_at")(r, split, i)


def chairs(r, split, i):
    east = values(r, r.randint(2, 6), low=2, high=28)
    west = list(reversed(east)) if split == "public" else values(r, r.randint(2, 6), low=2, high=28)
    # Public observations make exchanging either site's count for a sum indistinguishable.
    if split != "public" and total(east)-len(east) == total(west)-len(west):
        west[0] += 1
    return {"east_groups": east, "west_reservations": west}


def tidebook(r, split, i):
    issued = r.randint(5, 90)
    return {"station": r.choice(["Sill", "Bank", "Dock"]), "revision": r.randint(1, 9),
            "survey": {"issued_forms": issued, "returned_forms": r.randint(0, issued)},
            "conditions": {"flood": r.choice([True, False]), "round": r.randint(1, 12)}}


def darkroom(r, split, i):
    stream = {"strips": values(r, r.randint(2, 8), low=0, high=35)}
    return {"lab": r.choice(["Bram", "Oak", "Rill"]), "roll": r.randint(1, 400),
            "loose_tests": r.randint(0, 22), "reader_payload": json.dumps(stream),
            "extras": {"stock": r.randint(1, 18), "wet": r.choice([True, False])}}


def lightbox(r, split, i):
    rows = r.randint(2, 20)
    columns = r.randint(2, 25)
    return {"rows": rows, "columns": columns, "trimmed_rows": r.randint(0, rows-1)}


CASES = []


def case(name, group, text, body, builder, oracle):
    source = "def solve(x):\n" + "".join("    " + line + "\n" for line in dedent(body).strip().splitlines())
    CASES.append((name, group, text, source, builder, oracle))


case("greenhouse_cuttings", "aggregation", "The greenhouse recorded rooted cuttings on each tray. Return the total number of cuttings across the trays in x['trays'], including every repeated count.", """
return len(x["trays"])
""", greenhouse, lambda x: total(x["trays"]))

case("choir_partbooks", "aggregation", "The choir school needs one sign-out sheet per delivered batch of partbooks. x['batch_sizes'] lists books in each batch. Return how many sign-out sheets to print.", """
return sum(x["batch_sizes"])
""", choir, lambda x: tally(x["batch_sizes"]))

case("archive_digitizing", "aggregation", "A reading room may digitize only cleared lots. Each lot includes its shelf and number of copies. From x['lots'], return the total copies in the cleared lots.", """
eligible = [lot["copies"] for lot in x["lots"] if lot["cleared"]]
return len(eligible)
""", archive, lambda x: total(v["copies"] for v in x["lots"] if v["cleared"]))

case("trail_camera_visits", "boundary", "A trail camera starts a new visit after a gap of at least x['minimum_gap'] minutes. Count the entries in x['gaps'] meeting that condition.", """
return sum(1 for gap in x["gaps"] if gap > x["minimum_gap"])
""", threshold_input("gaps", "minimum_gap"), lambda x: len(x["gaps"]) - tally(g for g in x["gaps"] if g < x["minimum_gap"]))

case("book_mending", "boundary", "A book qualifies for the small mending bench if its torn-page count is at most x['bench_limit']. Return the number of qualifying books from x['tears'].", """
eligible = [n for n in x["tears"] if n < x["bench_limit"]]
return len(eligible)
""", threshold_input("tears", "bench_limit"), lambda x: len(x["tears"]) - tally(n for n in x["tears"] if n > x["bench_limit"]))

case("kiln_rejects", "boundary", "Reject a tile only when its firing strength is strictly less than x['standard']. Count rejected pieces from the strength readings in x['tiles'].", """
return len([s for s in x["tiles"] if s <= x["standard"]])
""", threshold_input("tiles", "standard"), lambda x: len(x["tiles"]) - tally(s for s in x["tiles"] if s >= x["standard"]))

case("wind_watch", "boundary", "Read the signed wind deviations in x['deviations']. Count how many strictly exceed the alert threshold x['threshold']; a value equal to the threshold stays out.", """
return sum(1 for v in x["deviations"] if v >= x["threshold"])
""", threshold_input("deviations", "threshold", signed=True), lambda x: len(x["deviations"]) - tally(v for v in x["deviations"] if v <= x["threshold"]))

case("museum_spacers", "distractor", "The framer has x['bundles'], each holding the stated number of identical spacers, and individually tagged loose spacers in x['loose_piece_ids']. Return the total pieces on hand.", """
loose = len(x["loose_piece_ids"])
bundled = len(x["bundles"])
return loose + bundled
""", spacers, lambda x: tally(x["loose_piece_ids"]) + total(x["bundles"]))

case("stage_cues", "distractor", "During an auditorium blackout, cues scheduled from opening frame through closing frame, both included, must be rebooked. Count the cue frames in that window.", """
a, b = x["opening"], x["closing"]
return len([f for f in x["cue_frames"] if a <= f and f < b])
""", stage, lambda x: len(x["cue_frames"]) - tally(f for f in x["cue_frames"] if f < x["opening"] or f > x["closing"]))

case("lecture_chairs", "public_ambiguity", "The east hall gets one chair per attendee in each east group. The west gallery admits only one delegate per west reservation, regardless of its recorded party size. Return the number of chairs for both rooms.", """
return len(x["west_reservations"]) + len(x["east_groups"])
""", chairs, lambda x: tally(x["west_reservations"]) + total(x["east_groups"]))

case("orchard_pickup", "shift", "Each picker in x['pickers'] is keyed by their name. The nested record gives a field row and the number of full crates. How many full crates must the orchard truck collect? Return the integer total.", """
crates = [record["full_crates"] for record in x["pickers"].values()]
return len(crates)
""", orchard, lambda x: total(x["pickers"][key]["full_crates"] for key in sorted(x["pickers"])))

case("luthier_drawer", "shift", "The luthier keeps separate string packets under x['bench']['sealed_packs']. Each integer is the usable string count of that packet, which can be zero. Include x['individual_strings'] unpacked strings. Return the total.", """
packs = x["bench"]["sealed_packs"]
stock = len(packs)
return x["individual_strings"] + stock
""", strings, lambda x: total([x["individual_strings"], *x["bench"]["sealed_packs"]]))

case("tide_survey_returns", "decoded", "Your input is an already decoded station form. The nested survey gives issued_forms and returned_forms. Return how many forms still need to come back.", """
import json
record = json.loads(x)
survey = record["survey"]
return survey["issued_forms"] - survey["returned_forms"]
""", tidebook, lambda x: tally(range(x["survey"]["returned_forms"], x["survey"]["issued_forms"])))

case("darkroom_test_strips", "decoded", "A decoded darkroom report has a separate reader_payload JSON string inside it. Decode that string to get an array called strips holding the test strip counts per tray. Return their total plus loose_tests from the outer report.", """
import json
tray_report = json.loads(x["reader_payload"])
record = json.loads(x)
return record["loose_tests"] + sum(tray_report["strips"])
""", darkroom, lambda x: total([x["loose_tests"], *json.loads(x["reader_payload"])["strips"]]))

case("screening_duration", "unsupported", "A screening lasts less than a day and may cross midnight. Start and end are minutes after midnight on a 24-hour clock. Return elapsed minutes.", """
return abs(x["end_minute"] - x["start_minute"])
""", cinema, lambda x: (x["end_minute"] - x["start_minute"]) % (24 * 60))

case("film_leader_allowance", "unsupported", "A film lab allows the smaller of x['rewinds'] and x['cap'] leader replacements. Each needs x['leader_metres'] metres. Return the total length of blank leader to issue.", """
return max(x["rewinds"], x["cap"]) * x["leader_metres"]
""", roll, lambda x: total(x["leader_metres"] for _ in range(sorted((x["rewinds"], x["cap"]))[0])))

case("lightbox_mask", "unsupported", "A rectangular projection mask covers a grid of x['rows'] rows and x['columns'] columns. Remove x['trimmed_rows'] complete rows and return the number of cells left.", """
return x["rows"] * x["columns"] - x["trimmed_rows"]
""", lightbox, lambda x: total(x["columns"] for row in range(x["trimmed_rows"], x["rows"])))

case("thaw_tags", "unchanged", "Count open thaw inspections whose tag temperature is below zero. Each record in x['tags'] has boolean 'open' and integer 'temp'.", """
return len([t for t in x["tags"] if t["open"] and t["temp"] < 0])
""", thaw, lambda x: tally(t for t in x["tags"] if t["open"] and t["temp"] <= -1))

case("nursery_labels", "unchanged", "Each number in x['packs'] states how many labels are sealed in that pack. x['individuals'] lists IDs of additional single labels. Return total label stock.", """
return sum(x["packs"]) + len(x["individuals"])
""", nursery, lambda x: total(x["packs"]) + tally(x["individuals"]))

case("tower_lamp", "unchanged", "Return true when any gust in x['gusts'] is strictly greater than x['alarm_at'], otherwise false.", """
return any(gust > x["alarm_at"] for gust in x["gusts"])
""", tower, lambda x: max(x["gusts"], default=float("-inf")) > x["alarm_at"])


def make():
    corpus, gold = {}, {}
    for name, group, prompt, source, builder, oracle in CASES:
        panels = {}
        seen = set()
        for split, n in SPLITS.items():
            r = random.Random(f"{SEED}/{name}/{split}")
            rows = []
            while len(rows) < n:
                i = len(rows)
                value = builder(r, split, i)
                # A tower alarm control has both classes in every split.
                if name == "tower_lamp" and i % 2 == 1:
                    value["gusts"] = [min(value["alarm_at"], v) for v in value["gusts"]]
                key = json.dumps(value, sort_keys=True, separators=(",", ":"))
                if key in seen:
                    continue
                seen.add(key)
                rows.append({"input": value, "output": oracle(value)})
            panels[split] = rows
        corpus[name] = {"id": name, "phase": "confirmation", "group": group, "prompt": prompt, "source": source,
                        "public": panels["public"], "validation": panels["validation"]}
        gold[name] = {"private": panels["private"]}
    return corpus, gold


if __name__ == "__main__":
    for filename, data in zip(("corpus.json", "keys.json"), make()):
        body = (json.dumps(data, separators=(",", ":"), ensure_ascii=True) + "\n").encode()
        (ROOT / filename).write_bytes(body)
        print(filename, len(body), hashlib.sha256(body).hexdigest())

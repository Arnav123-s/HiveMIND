"""Generator for the data-format subject (niche-expansion pick #2).

Muse's side, Hive growth department. Three DISJOINT surface
partitions (train / screen=held-A / confirm=held-B): different key
vocabularies, value shapes, CSV column themes, TOML section styles
and plain-text topics per partition, crossed with bands
(1 flat -> 2 nested/larger -> 3 noisy: comments and whitespace
variation where the format allows, quoted CSV fields, subtle
malformed-JSON errors).

Design rule learned from cycle niche-expansion-002 attempt 1
(REJECTED, record preserved): formatting style must rotate WITHIN
every partition, never be partition- or class-exclusive. Attempt 1
pretty-printed train JSON while screen/confirm JSON was compact, so
"compact" became a malformed cue and held JSON scored 0.33 recall;
CSV likewise had a single theme per partition, so held CSV (new
theme words) collapsed to plain-text. Now each partition carries
three internal key-sets / CSV themes / TOML styles / plain topics
(all still disjoint from the other partitions' pools), and JSON
formatting (compact / indented / spaced) rotates by variant in
every partition and band, for valid and malformed items alike.

Labels are PROVED at generation by a mutual-exclusion oracle
ensemble over the standard library (plan pick #2):
  json           <=> json.loads succeeds
  malformed-json <=> JSON shape (starts {/[ after strip, quotes /
                     braces present) AND json.loads raises AND no
                     other class's test passes
  toml           <=> tomllib.loads succeeds AND json.loads fails
                     AND the csv shape test fails
  csv            <=> >=3 rows, >=2 columns, consistent width via the
                     csv module, AND both parsers above fail
  plain-text     <=> all parsers fail AND the csv shape test fails
                     AND it does not carry the JSON shape
Any item whose oracle verdict differs from its constructed label is
dropped with the reason counted, never relabelled by hand.

Retry niche-expansion-002b (attempt 3 of the subject; the wave's
retry builder). Attempt 2's binding failure was valid-vs-malformed
JSON across disjoint vocabularies: its six ad-hoc faults were mostly
single, local, or absence-type edits (drop the last char, drop one
colon), so under a bag-of-trigrams featurizer the fault's few
trigrams drowned in the shared base's. This retry changes the
malformed generator, not the recipe around it:

- Malformed items are built from a TAXONOMY of 12 named fault types
  (FAULTS below), assigned round-robin so every type appears
  uniformly in every partition — the fault signal is
  vocabulary-independent by construction, since the same taxonomy
  fires on train, screen and confirm bases alike.
- Each fault is applied as a DOCUMENT-LEVEL transformation (every
  separator doubled, every key unquoted, every closing brace
  mistyped, ...), so the fault's core punctuation trigrams recur in
  every malformed document of that type instead of occurring once
  in one corner of one document. One fault type per item — never
  two faults stacked.
- The oracle is STRICT JSON: Python's json module accepts the
  non-standard literals NaN / Infinity / -Infinity by default, so
  _json_ok passes a parse_constant that raises. Without that, the
  taxonomy's NaN/Infinity fault could never be oracle-proved
  malformed (it would verify as "json"). Valid items never contain
  those literals, so no other class is affected.
- Mild rng-driven recombination (CSV row order and small numeric
  jitter, TOML numeric jitter and pair order, plain-sentence picks,
  JSON numbers drawn from a small fixed set) breaks attempt 2's
  exact-duplication problem — its 300 train items held only 127
  distinct texts, CSV and TOML just 9 each — without widening the
  feature space the way free numeric/lexical variation would.
"""
from __future__ import annotations

import csv
import io
import json
import random
import re
import tomllib
from typing import Any, Dict, List, Optional

CLASSES = ["json", "malformed-json", "csv", "toml", "plain-text"]

# ------------------------------------------------------------ pools
# Per partition: 3 key-sets, 3 csv themes (each with a numeric
# column), 3 toml styles, 6 plain sentences. No word pool crosses
# partitions.
_POOLS = {
    "train": {
        "key_sets": [
            ["name", "age", "city", "score", "level", "team"],
            ["crop", "yield", "field", "season", "soil", "crew"],
            ["song", "tempo", "album", "track", "genre", "label"],
        ],
        "vals": ["ada", "reno", "oslo", "lima", "york", "perth"],
        "csv_themes": [
            (["plant", "height_cm", "watered"],
             [["fern", "42", "yes"], ["oak", "310", "no"],
              ["sage", "18", "yes"], ["pine", "205", "no"],
              ["mint", "12", "yes"]]),
            (["route", "stops", "minutes"],
             [["elm loop", "6", "25"], ["hill line", "9", "40"],
              ["bay run", "4", "18"], ["mill way", "7", "33"],
              ["fort path", "5", "22"]]),
            (["tool", "count", "shelf"],
             [["hammer", "14", "b2"], ["wrench", "9", "a1"],
              ["level", "5", "c3"], ["square", "7", "b1"],
              ["mallet", "3", "a2"]]),
        ],
        "toml_styles": [
            ("garden", [("beds", "6"), ("season", '"spring"'),
                        ("depth_cm", "30")]),
            ("bakery", [("ovens", "3"), ("flour_kg", "80"),
                        ("opens", '"dawn"')]),
            ("stable", [("stalls", "11"), ("horses", "9"),
                        ("hay_bales", "26")]),
        ],
        "plain": ["The ferry leaves the dock before the market opens",
                  "A short note about the orchard gate and the north path",
                  "Please water the seedlings when the soil looks dry",
                  "The miller grinds the grain after the morning rain",
                  "Two lanterns hang beside the gate of the old mill",
                  "The choir rehearses in the hall above the bakery"],
    },
    "screen": {
        "key_sets": [
            ["product", "price", "stock", "sku", "weight", "vendor"],
            ["harbor", "vessel", "berth", "cargo", "crew", "flag"],
            ["lesson", "pupil", "grade", "term", "room", "tutor"],
        ],
        "vals": ["anvil", "brush", "clamp", "drill", "elbow", "flange"],
        "csv_themes": [
            (["pier", "vessel", "berths"],
             [["north pier", "ferry", "12"], ["south pier", "barge", "4"],
              ["east pier", "skiff", "9"], ["west pier", "tug", "6"],
              ["old pier", "raft", "3"]]),
            (["class", "pupils", "room"],
             [["algebra", "24", "r3"], ["history", "19", "r1"],
              ["botany", "22", "r5"], ["drawing", "16", "r2"],
              ["choir", "28", "r4"]]),
            (["item", "shelf_life", "crates"],
             [["plums", "9", "40"], ["pears", "12", "35"],
              ["figs", "6", "21"], ["dates", "30", "52"],
              ["nuts", "45", "18"]]),
        ],
        "toml_styles": [
            ("warehouse", [("aisles", "14"), ("manager", '"priya"'),
                           ("capacity", "900")]),
            ("harbor_office", [("radios", "5"), ("harbormaster", '"tom"'),
                               ("buoys", "17")]),
            ("school", [("terms", "3"), ("buses", "7"),
                        ("library", '"annex"')]),
        ],
        "plain": ["The warehouse bell rings twice when the trucks arrive",
                  "Keep the loading bay clear during the morning shift",
                  "A crate of lanterns waits beside the harbor office",
                  "The pupils gather in the yard before the first lesson",
                  "Crates of plums are stacked beside the cold store",
                  "The harbormaster checks the tide table at noon"],
    },
    "confirm": {
        "key_sets": [
            ["sensor", "reading", "unit", "station", "drift", "mode"],
            ["trail", "summit", "ascent", "camp", "ridge", "map"],
            ["member", "plan", "joined", "badge", "chapter", "dues"],
        ],
        "vals": ["north", "south", "ridge", "valley", "coast", "mesa"],
        "csv_themes": [
            (["trail", "length_km", "surface"],
             [["ridge loop", "8", "gravel"], ["coast path", "14", "sand"],
              ["mesa spur", "5", "rock"], ["valley walk", "11", "grass"],
              ["cliff way", "7", "stone"]]),
            (["station", "trains", "platform"],
             [["northgate", "22", "p1"], ["milltown", "9", "p2"],
              ["eastfield", "17", "p1"], ["port bay", "26", "p3"],
              ["highmoor", "6", "p2"]]),
            (["choir", "voices", "hall"],
             [["dawn choir", "31", "h2"], ["river choir", "24", "h1"],
              ["hill choir", "19", "h3"], ["town choir", "36", "h2"],
              ["bay choir", "27", "h1"]]),
        ],
        "toml_styles": [
            ("observatory", [("dome", '"east"'), ("mirrors", "3"),
                             ("visitors", "48")]),
            ("trailhead", [("kiosk", '"pine"'), ("maps", "60"),
                           ("wardens", "4")]),
            ("guildhall", [("benches", "20"), ("steward", '"mara"'),
                           ("candles", "12")]),
        ],
        "plain": ["The observatory opens its dome after the evening bell",
                  "Visitors follow the ridge path toward the signal tower",
                  "A kettle of soup waits in the small observatory kitchen",
                  "The wardens lock the trailhead kiosk at dusk",
                  "Members of the guild gather for the winter feast",
                  "The night train slows as it crosses the high moor"],
    },
}


# ------------------------------------------------------------ oracle
def _csv_shape_ok(text: str) -> bool:
    try:
        rows = list(csv.reader(io.StringIO(text)))
    except Exception:  # noqa: BLE001
        return False
    if len(rows) < 3:
        return False
    width = len(rows[0])
    if width < 2:
        return False
    return all(len(r) == width for r in rows)


def _reject_constant(name: str):
    # Strict JSON (RFC 8259): NaN / Infinity / -Infinity are not
    # valid JSON literals, but Python's json accepts them unless
    # parse_constant raises. Closing that leniency is what makes
    # the taxonomy's nan-infinity fault oracle-provable.
    raise ValueError(f"non-standard JSON literal: {name}")


def _json_ok(text: str) -> bool:
    try:
        json.loads(text, parse_constant=_reject_constant)
        return True
    except Exception:  # noqa: BLE001
        return False


def _toml_ok(text: str) -> bool:
    try:
        tomllib.loads(text)
        return True
    except Exception:  # noqa: BLE001
        return False


def _json_shape(text: str) -> bool:
    # "quotes" means either quote kind: a fully single-quoted
    # payload (the taxonomy's single-quoted-string fault) carries
    # the JSON shape with ' instead of " — counting only " would
    # make that fault unverifiable, exactly like strict-NaN above.
    s = text.strip()
    return bool(s) and s[0] in "{[" and ('"' in s or "'" in s) and \
        any(ch in s for ch in "{}[]")


def oracle_label(text: str) -> Optional[str]:
    """The mutual-exclusion ensemble's single verdict (or None)."""
    if _json_ok(text):
        return "json"
    if _toml_ok(text) and not _csv_shape_ok(text):
        return "toml"
    if _csv_shape_ok(text):
        return "csv"
    if _json_shape(text):
        return "malformed-json"
    if not _csv_shape_ok(text):
        return "plain-text"
    return None


def verify_item(text: str, label: str) -> Optional[str]:
    """None to keep, else the drop reason. Checks the plan's exact
    per-class conditions, not just the ensemble shortcut."""
    j, t, c = _json_ok(text), _toml_ok(text), _csv_shape_ok(text)
    shape = _json_shape(text)
    if label == "json":
        ok = j
    elif label == "malformed-json":
        ok = shape and not j and not t and not c
    elif label == "toml":
        ok = t and not j and not c
    elif label == "csv":
        ok = c and not j and not t
    elif label == "plain-text":
        ok = not j and not t and not c and not shape
    else:
        ok = False
    if ok and oracle_label(text) == label:
        return None
    return f"oracle_says_{oracle_label(text)}_want_{label}"


# ------------------------------------------------------------ bodies
def _dump_json(obj, variant):
    """Formatting rotates by variant in every partition/band."""
    style = variant % 3
    if style == 0:
        return json.dumps(obj)
    if style == 1:
        return json.dumps(obj, indent=1)
    inner = ", ".join(f"{json.dumps(k)} : {json.dumps(v)}"
                      for k, v in obj.items())
    return "{  " + inner + "  }"


_NUMS = [3, 5, 8, 13, 21, 34, 47, 58]


def _num(rng, variant):
    return rng.choice(_NUMS) if rng is not None else 3 + variant


def _json_base(pool, band, variant, rng=None):
    keys = pool["key_sets"][variant % len(pool["key_sets"])]
    vals = pool["vals"]
    k = lambda i: keys[(variant + i) % len(keys)]  # noqa: E731
    v = lambda i: vals[(variant + i) % len(vals)]  # noqa: E731
    if band == 1:
        return _dump_json({k(0): v(0), k(1): _num(rng, variant),
                           k(2): v(2)}, variant)
    if band == 2:
        arr = [_num(rng, variant + j) for j in range(3)] \
            if rng is not None else [1, 2, 3]
        obj = {k(0): {k(1): v(1), k(2): arr},
               k(3): [{k(4): v(4)}, {k(4): v(5)}],
               k(5): _num(rng, variant + 3)}
        return _dump_json(obj, variant + 1)
    # band 3: noisy whitespace / scalar tails, still valid
    arr = [_num(rng, variant), _num(rng, variant + 1)] \
        if rng is not None else [variant, variant + 2]
    return _dump_json({k(0): arr, k(1): v(1),
                       k(2): True, k(3): None}, variant + 2)


# ------------------------------------------------- malformed faults
# The fault taxonomy (002b lever 1). Strong presence-cue faults
# first; the two absence-cue faults (missing-closing,
# truncated-string) last. Every fault is a document-level transform
# of a valid base from the SAME partition, so its punctuation
# signature is identical in train / screen / confirm while the
# vocabularies stay disjoint. One fault per item.
FAULTS = [
    "trailing-comma",
    "single-quoted-string",
    "bad-escape",
    "nan-infinity-literal",
    "embedded-comment",
    "doubled-separator",
    "extra-closing",
    "wrong-bracket-type",
    "unquoted-key",
    "missing-comma",
    "missing-closing",
    "truncated-string",
]


def _apply_fault(text: str, fault: str, occ: int) -> str:
    if fault == "trailing-comma":
        # a comma before EVERY closing brace: ",}" / ",]"-style
        # surplus separators throughout the document
        return text.replace("}", ",}").replace("]", ",]")
    if fault == "single-quoted-string":
        # the whole payload re-quoted Python-dict style
        return text.replace('"', "'")
    if fault == "bad-escape":
        # an invalid \q escape inside every string value
        def esc(m):
            body = m.group(2)
            return f':{m.group(1)}"{body[:1]}\\q{body[1:]}"'
        return re.sub(r':(\s*)"([a-z0-9 ]*)"', esc, text)
    if fault == "nan-infinity-literal":
        lit = "NaN" if occ % 2 == 0 else "Infinity"
        return re.sub(r"\d+", lit, text)
    if fault == "embedded-comment":
        i = text.find("{")
        return text[:i + 1] + " /*x*/ " + text[i + 1:]
    if fault == "doubled-separator":
        return text.replace(",", ",,")
    if fault == "extra-closing":
        return text + "}}"
    if fault == "wrong-bracket-type":
        # every object closed with a bracket instead of a brace
        return text.replace("}", "]")
    if fault == "unquoted-key":
        return re.sub(r'"([a-z0-9_]+)"(\s*:)', r"\1\2", text)
    if fault == "missing-comma":
        # every pair/element separator dropped
        return text.replace(",", " ")
    if fault == "missing-closing":
        # ALL closings of one bracket type dropped, so the absence
        # is not masked by nested copies under a bag featurizer
        if occ % 2 == 1 and "]" in text:
            return text.replace("]", "")
        return text.replace("}", "")
    if fault == "truncated-string":
        # cut inside the final string token; nothing closes after it
        toks = list(re.finditer(r'"[^"\n]*"', text))
        if not toks:
            return text[: len(text) // 2]
        m = toks[-1]
        cut = m.start() + max(2, len(m.group(0)) // 2)
        return text[:cut]
    raise ValueError(f"unknown fault {fault}")


def _body(pool, partition, cls, band, rng, variant, state=None):
    keys = pool["key_sets"][variant % len(pool["key_sets"])]
    vals = pool["vals"]
    k = lambda i: keys[(variant + i) % len(keys)]  # noqa: E731
    v = lambda i: vals[(variant + i) % len(vals)]  # noqa: E731

    if cls == "json":
        return _json_base(pool, band, variant, rng)

    if cls == "malformed-json":
        # Malformed bases are the json family's shapes at a shifted
        # variant (never the identical string a json item trains
        # on — exact contrast pairs were tried in a diagnostic and
        # hurt: the shared base's features drowned the fault's).
        # The fault itself comes from the FAULTS taxonomy, assigned
        # round-robin over the partition's malformed items so every
        # fault type appears uniformly in every partition.
        if state is None:
            state = {"malformed": 0, "fault_occ": {}, "last_fault": None}
        idx = state["malformed"]
        state["malformed"] = idx + 1
        fault = FAULTS[idx % len(FAULTS)]
        occ = state["fault_occ"].get(fault, 0)
        state["fault_occ"][fault] = occ + 1
        state["last_fault"] = fault
        base = _json_base(pool, band, variant + 3, rng)
        return _apply_fault(base, fault, occ)

    if cls == "csv":
        head, rows = pool["csv_themes"][variant % len(pool["csv_themes"])]
        n = 3 if band == 1 else (4 if band == 2 else 5)
        chosen = [list(r) for r in rows[:n]]
        rng.shuffle(chosen)
        chosen = [[str(int(c) + rng.choice([0, 0, 1, 2, 5]))
                   if c.isdigit() else c for c in r] for r in chosen]
        if band == 3:
            lines = [",".join(f'"{h}"' for h in head)]
            lines += [",".join(f'"{c}"' for c in r) for r in chosen]
            return "\n".join(lines)
        lines = [",".join(head)] + [",".join(r) for r in chosen]
        return "\n".join(lines)

    if cls == "toml":
        sec, pairs = pool["toml_styles"][variant % len(pool["toml_styles"])]
        off = rng.choice([0, 0, 1, 2, 5])
        pairs = [(kk, str(int(vv) + off) if vv.isdigit() else vv)
                 for kk, vv in pairs]
        rng.shuffle(pairs)
        if band == 1:
            return "\n".join(f"{kk} = {vv}" for kk, vv in pairs[:2])
        if band == 2:
            body = "\n".join(f"{kk} = {vv}" for kk, vv in pairs)
            return f"[{sec}]\n{body}"
        body = "\n".join(f"{kk} = {vv}" for kk, vv in pairs)
        return f"# {sec} settings\n[{sec}]\n{body}\n\n[{sec}.notes]\n" \
               f"reviewed = true"

    # plain-text
    plain = pool["plain"]
    base = plain[rng.randrange(len(plain))]
    if band == 1:
        return base + "."
    if band == 2:
        second = plain[rng.randrange(len(plain))]
        if second == base:
            second = plain[(plain.index(base) + 2) % len(plain)]
        return base + ".\n" + second + "."
    return base + " — noted on " + rng.choice(["monday", "tuesday", "friday"]) \
        + " at " + rng.choice(["dawn", "noon", "dusk"]) + "."


# ------------------------------------------------------------ pools
def _pool(partition: str, band_counts: Dict[int, int], seed: int,
          group_prefix: str):
    pool = _POOLS[partition]
    items: List[Dict[str, Any]] = []
    stats: Dict[str, Any] = {"families": 0, "drops": {}}
    rng = random.Random(seed)
    state = {"malformed": 0, "fault_occ": {}, "last_fault": None}
    for band in (1, 2, 3):
        count = band_counts.get(band, 0)
        for cls in CLASSES:
            for i in range(count):
                variant = i + (band - 1) * 5 + CLASSES.index(cls)
                text = _body(pool, partition, cls, band, rng, variant,
                             state)
                stats["families"] += 1
                gid = f"{group_prefix}:{partition}-b{band}-{cls}-{i}"
                reason = verify_item(text, cls)
                if reason is not None:
                    key = reason.rsplit("_want_", 1)[0]
                    stats["drops"][key] = stats["drops"].get(key, 0) + 1
                    continue
                item = {"text": text, "label": cls, "group": gid,
                        "band": band, "family": cls}
                if cls == "malformed-json":
                    # metadata only (never a feature): which taxonomy
                    # fault built this item, for per-fault dev analysis
                    item["fault"] = state["last_fault"]
                items.append(item)
    stats["items"] = len(items)
    return items, stats


def gen_pool(band_counts, seed, group_prefix="train"):
    return _pool("train", band_counts, seed, group_prefix)


def gen_screen_pool(band_counts, seed, group_prefix="screen"):
    return _pool("screen", band_counts, seed, group_prefix)


def gen_confirm_pool(band_counts, seed, group_prefix="confirm"):
    return _pool("confirm", band_counts, seed, group_prefix)


# 002b lever 2, chosen on a dev split of train only (never held):
# enlarging train 300 -> 600 (malformed share held at its 1/5 class
# share, 10 items per fault type instead of 5) lifted dev accuracy
# from 0.9833 / malformed recall 0.917 (best at 300) to 1.0000 /
# 1.0000 (hidden 8, epochs 300). Epochs 600 tied 300 exactly and
# 1200 was worse, so the subject's epochs stay 300 in subjects.py.
DEFAULT_TRAIN_BANDS = {1: 40, 2: 40, 3: 40}
DEFAULT_HELD_BANDS = {1: 6, 2: 6, 3: 6}


def gen_train(seed: int = 201):
    return gen_pool(DEFAULT_TRAIN_BANDS, seed, "train")


def gen_held_a(seed: int = 202):
    return gen_screen_pool(DEFAULT_HELD_BANDS, seed, "screen")


def gen_held_b(seed: int = 203):
    return gen_confirm_pool(DEFAULT_HELD_BANDS, seed, "confirm")

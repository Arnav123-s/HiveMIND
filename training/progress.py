"""The hive's progress toward its goal, drawn from its own record after every generation.

    python training/progress.py [--record training/reports/generations.jsonl] [--out docs/progress]

The goal is a body of ternary nets that does what it is asked, and gets better at it by itself, generation after
generation. Every generation ends with an exam of the grown body (its pulse) written to the record. This draws
that record as four graphs and one page (docs/PROGRESS.md), so anyone can see whether the hive is getting better
and where it is weakest, without reading numbers:

  score.svg   the share of exam tasks the body passed, each generation (and the DNA alone, where it was measured)
  carry.svg   the share it passed of kinds of task it has never practised (does what it learns carry over?)
  kinds.svg   every kind of task, over the last generations of the body's DNA, weakest first
  rows.svg    how many checked rows the body was taught from, each generation

The loop closes here too: the kinds this page shows weakest are the kinds practice draws most often next
(training/grow.edge_weights, used by practice at the ladder level), so the hive spends its practice where the graph
says it is weak. The workflow's record step runs this and commits the result with the record.
"""
import json
import sys
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

NAMES = {"t17": "1.7B", "t40": "4B", "t80": "8B"}
# colours: the validated categorical pair (blue, orange) and a neutral for the DNA alone; dark-mode steps of the
# same hues (both pairs pass the colour-blind and contrast checks)
SERIES = {"t80": ("#2a78d6", "#3987e5"), "t17": ("#eb6834", "#d95926"), "t40": ("#1baf7a", "#199e70"),
          # the parts of an exam: the same validated slots, in the same order
          "hard": ("#2a78d6", "#3987e5"), "easy": ("#eb6834", "#d95926"), "several": ("#1baf7a", "#199e70")}
PARTS = {"hard": "hard kinds", "easy": "easy kinds", "several": "tasks of several parts"}
STYLE = """<style>
.bg{fill:#fcfcfb}.ink{fill:#0b0b0b}.ink2{fill:#52514e}.grid{stroke:#e4e3df}.axis{stroke:#b9b8b2}.dna{stroke:#52514e;fill:#fcfcfb}
%s
@media (prefers-color-scheme: dark){.bg{fill:#1a1a19}.ink{fill:#f0efec}.ink2{fill:#c3c2b7}.grid{stroke:#2c2c2a}.axis{stroke:#5a5955}.dna{stroke:#c3c2b7;fill:#1a1a19}%s}
text{font-family:-apple-system,"Segoe UI",Helvetica,Arial,sans-serif}
</style>"""
# a single-hue ramp (light to dark blue) for a share passed; text on the darker half is light
RAMP = ["#e8f1fc", "#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95"]
RAMP_DARK = ["#1f2a38", "#173a66", "#1c5cab", "#2a78d6", "#5598e7", "#86b6ef", "#b7d3f6"]


def load(record):
    """The generations in the order they were recorded, each with its DNA (older lines without one were the 1.7B)."""
    out = []
    for ln in Path(record).read_text().splitlines() if Path(record).exists() else []:
        try:
            d = json.loads(ln)
        except ValueError:
            continue
        a = d.get("arms", {}).get("after", {})
        if a.get("tasks"):
            d["dna"] = d.get("dna") or "t17"
            out.append(d)
    return sorted(out, key=lambda d: d.get("when", ""))


def _style(dnas):
    light = "".join(f".s{k}{{fill:{SERIES[k][0]};stroke:{SERIES[k][0]}}}.l{k}{{stroke:{SERIES[k][0]};fill:none}}" for k in dnas if k in SERIES)
    dark = "".join(f".s{k}{{fill:{SERIES[k][1]};stroke:{SERIES[k][1]}}}.l{k}{{stroke:{SERIES[k][1]};fill:none}}" for k in dnas if k in SERIES)
    ramp = "".join(f".h{i}{{fill:{c}}}" for i, c in enumerate(RAMP))
    ramp_dark = "".join(f".h{i}{{fill:{c}}}" for i, c in enumerate(RAMP_DARK))
    return STYLE % (light + ramp, dark + ramp_dark)


def _svg(w, h, body, dnas=(), title=""):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{escape(title)}">'
            + _style(dnas) + f'<rect class="bg" width="{w}" height="{h}" rx="8"/>' + body + "</svg>\n")


def _text(x, y, s, cls="ink", size=12, anchor="start", weight="normal"):
    return f'<text x="{x:.1f}" y="{y:.1f}" class="{cls}" font-size="{size}" text-anchor="{anchor}" font-weight="{weight}">{escape(str(s))}</text>'


def share_chart(gens, pick, title, note, w=760, h=300):
    """Dots joined by a line, one series per DNA, y from 0 to 100 %. pick(d) -> (passed, tried) or None."""
    left, right, top, bottom = 52, 96, 58, 44
    pw, ph = w - left - right, h - top - bottom
    pts = [(i, d, pick(d)) for i, d in enumerate(gens)]
    pts = [(i, d, p) for i, d, p in pts if p and p[1]]
    dnas = list(dict.fromkeys(d["dna"] for _, d, _ in pts))
    n = max(1, len(gens))
    x = lambda i: left + (pw * (i + 0.5) / n)  # noqa: E731
    y = lambda v: top + ph * (1 - v)  # noqa: E731
    b = [_text(16, 24, title, size=15, weight="600"), _text(16, 42, note, "ink2", 12)]
    for v in (0, .25, .5, .75, 1):
        b.append(f'<line class="grid" x1="{left}" x2="{left + pw}" y1="{y(v):.1f}" y2="{y(v):.1f}" stroke-width="1"/>')
        b.append(_text(left - 8, y(v) + 4, f"{int(v * 100)}%", "ink2", 11, "end"))
    for i, d in enumerate(gens):
        b.append(_text(x(i), top + ph + 18, d.get("generation", ""), "ink2", 11, "middle"))
    # the DNA alone, where a generation measured it: a hollow ring, so the body is read against it
    for i, d in enumerate(gens):
        a = d.get("arms", {}).get("dna", {})
        if pick is _passed and a.get("tasks"):
            b.append(f'<circle class="dna" cx="{x(i):.1f}" cy="{y(a["passed"] / a["tasks"]):.1f}" r="4.5" stroke-width="2">'
                     f'<title>{escape(d.get("generation", ""))}: the DNA alone passed {a["passed"]} of {a["tasks"]}</title></circle>')
    for k in dnas:
        mine = [(i, d, p) for i, d, p in pts if d["dna"] == k]
        if len(mine) > 1:
            b.append(f'<polyline class="l{k}" stroke-width="2" points="' + " ".join(f"{x(i):.1f},{y(p[0] / p[1]):.1f}" for i, _, p in mine) + '"/>')
        for i, d, p in mine:
            hollow = ' fill-opacity="0.25"' if d.get("trial") else ""
            b.append(f'<circle class="s{k}" cx="{x(i):.1f}" cy="{y(p[0] / p[1]):.1f}" r="5" stroke-width="2"{hollow}>'
                     f'<title>{escape(d.get("generation", ""))} ({NAMES.get(k, k)}{", a trial" if d.get("trial") else ""}): {p[0]} of {p[1]}</title></circle>')
        i, d, p = mine[-1]  # the newest point of each series is labelled with its count
        b.append(_text(x(i) + 9, y(p[0] / p[1]) + 4, f"{p[0]} of {p[1]}", "ink", 11))
    # legend: one entry per DNA, and the ring for the DNA alone when it is drawn
    lx = left + pw + 14
    for j, k in enumerate(dnas):
        b.append(f'<circle class="s{k}" cx="{lx + 5}" cy="{top + 6 + j * 20}" r="5"/>' + _text(lx + 15, top + 10 + j * 20, f"{NAMES.get(k, k)} body", "ink", 11))
    if pick is _passed and any(d.get("arms", {}).get("dna", {}).get("tasks") for d in gens):
        j = len(dnas)
        b.append(f'<circle class="dna" cx="{lx + 5}" cy="{top + 6 + j * 20}" r="4.5" stroke-width="2"/>' + _text(lx + 15, top + 10 + j * 20, "DNA alone", "ink", 11))
    return _svg(w, h, "".join(b), dnas, title)


def parts_chart(gens, w=760, h=300):
    """The hard kinds, the easy kinds and the tasks of several parts, each as a share passed, each generation that
    recorded them apart (grow_record.arm). Each kind is passed always or never: the score moves only when a hard,
    never-passed kind is learned, so this is where to look."""
    left, right, top, bottom = 52, 150, 58, 44
    pw, ph = w - left - right, h - top - bottom
    have = [d for d in gens if any((d["arms"]["after"].get(k) or [0, 0])[1] for k in PARTS)]
    n = max(1, len(have))
    x = lambda i: left + pw * (i + 0.5) / n  # noqa: E731
    y = lambda v: top + ph * (1 - v)  # noqa: E731
    b = [_text(16, 24, "Hard kinds, easy kinds and tasks of several parts, passed", size=15, weight="600"),
         _text(16, 42, "each kind is passed always or never: the score moves when a hard kind is learned", "ink2", 12)]
    for v in (0, .25, .5, .75, 1):
        b.append(f'<line class="grid" x1="{left}" x2="{left + pw}" y1="{y(v):.1f}" y2="{y(v):.1f}" stroke-width="1"/>')
        b.append(_text(left - 8, y(v) + 4, f"{int(v * 100)}%", "ink2", 11, "end"))
    if not have:
        b.append(_text(left + pw / 2, top + ph / 2, "no generation has recorded them apart yet", "ink2", 12, "middle"))
    for i, d in enumerate(have):
        b.append(_text(x(i), top + ph + 18, d.get("generation", ""), "ink2", 11, "middle"))
    for j, (k, label) in enumerate(PARTS.items()):
        pts = [(i, d["arms"]["after"].get(k)) for i, d in enumerate(have)]
        pts = [(i, c) for i, c in pts if c and c[1]]
        if len(pts) > 1:
            b.append(f'<polyline class="l{k}" stroke-width="2" points="' + " ".join(f"{x(i):.1f},{y(c[0] / c[1]):.1f}" for i, c in pts) + '"/>')
        for i, c in pts:
            b.append(f'<circle class="s{k}" cx="{x(i):.1f}" cy="{y(c[0] / c[1]):.1f}" r="5" stroke-width="2">'
                     f'<title>{escape(have[i].get("generation", ""))}, {label}: {c[0]} of {c[1]}</title></circle>')
        if pts:
            i, c = pts[-1]
            b.append(_text(x(i) + 9, y(c[0] / c[1]) + 4, f"{c[0]} of {c[1]}", "ink", 11))
        b.append(f'<circle class="s{k}" cx="{left + pw + 19}" cy="{top + 6 + j * 20}" r="5"/>' + _text(left + pw + 29, top + 10 + j * 20, label, "ink", 11))
    return _svg(w, h, "".join(b), list(PARTS), "parts")


def _passed(d):
    a = d["arms"]["after"]
    return a["passed"], a["tasks"]


def _carried(d):
    u = d["arms"]["after"].get("unpractised") or [0, 0]
    return (u[0], u[1]) if len(u) == 2 and u[1] else None


def kinds(gens, dna, last=6):
    """{kind: [(passed, tried) or None per generation]} over the last generations of one DNA, weakest first, and the
    generations' names."""
    mine = [d for d in gens if d["dna"] == dna and d["arms"]["after"].get("kinds")][-last:]
    names = [d.get("generation", "") for d in mine]
    table = {}
    for j, d in enumerate(mine):
        for k, (p, n) in d["arms"]["after"]["kinds"].items():
            table.setdefault(k, [None] * len(mine))[j] = (p, n)
    pooled = lambda row: (sum(c[0] for c in row if c) + 1) / (sum(c[1] for c in row if c) + 2)  # noqa: E731
    return dict(sorted(table.items(), key=lambda kv: (pooled(kv[1]), kv[0]))), names


def kinds_chart(table, names, dna, w=760):
    label_w, cell_w, cell_h, top = 330, 62, 24, 70
    w = max(w, label_w + cell_w * max(1, len(names)) + 40)
    h = top + cell_h * max(1, len(table)) + 28
    b = [_text(16, 24, f"Each kind of task in the exams of the {NAMES.get(dna, dna)} body, weakest first", size=15, weight="600"),
         _text(16, 42, "passed of tried in each generation's exam; an empty cell: that kind was not in that exam", "ink2", 12)]
    for j, g in enumerate(names):
        b.append(_text(label_w + cell_w * j + cell_w / 2, top - 10, g, "ink2", 11, "middle"))
    for i, (k, row) in enumerate(table.items()):
        yy = top + i * cell_h
        b.append(_text(label_w - 10, yy + cell_h / 2 + 4, k[:52], "ink", 11, "end"))
        for j, c in enumerate(row):
            if not c:
                continue
            p, n = c
            step = round((len(RAMP) - 1) * p / n) if n else 0
            cx = label_w + cell_w * j
            b.append(f'<rect class="h{step}" x="{cx + 1}" y="{yy + 1}" width="{cell_w - 2}" height="{cell_h - 2}" rx="4">'
                     f'<title>{escape(k)}, {escape(names[j])}: {p} of {n}</title></rect>')
            b.append(_text(cx + cell_w / 2, yy + cell_h / 2 + 4, f"{p}/{n}", "ink" if step < 4 else "bg", 11, "middle"))
    return _svg(w, h, "".join(b), (), "kinds of task")


def rows_chart(gens, w=760, h=260):
    left, right, top, bottom = 52, 30, 58, 44
    pw, ph = w - left - right, h - top - bottom
    n = max(1, len(gens))
    most = max([d.get("rows") or 0 for d in gens] + [1])
    bw = min(36, pw / n * 0.6)
    b = [_text(16, 24, "Checked rows the body was taught from, each generation", size=15, weight="600"),
         _text(16, 42, "programs the hive's own checks confirmed, its own mistakes mended, and its dreams", "ink2", 12)]
    for v in (0, .5, 1):
        yy = top + ph * (1 - v)
        b.append(f'<line class="grid" x1="{left}" x2="{left + pw}" y1="{yy:.1f}" y2="{yy:.1f}" stroke-width="1"/>' + _text(left - 8, yy + 4, int(most * v), "ink2", 11, "end"))
    dnas = []
    for i, d in enumerate(gens):
        r = d.get("rows") or 0
        cx = left + pw * (i + 0.5) / n
        hh = ph * r / most
        dnas.append(d["dna"])
        # a bar with a rounded top on the baseline
        b.append(f'<path class="s{d["dna"]}" d="M{cx - bw / 2:.1f},{top + ph:.1f} V{top + ph - hh + 4:.1f} q0,-4 4,-4 H{cx + bw / 2 - 4:.1f} q4,0 4,4 V{top + ph:.1f} Z">'
                 f'<title>{escape(d.get("generation", ""))}: {r} rows</title></path>')
        b.append(_text(cx, top + ph + 18, d.get("generation", ""), "ink2", 11, "middle"))
    i = len(gens) - 1
    if i >= 0:
        b.append(_text(left + pw * (i + 0.5) / n, top + ph - ph * (gens[-1].get("rows") or 0) / most - 8, gens[-1].get("rows") or 0, "ink", 11, "middle"))
    return _svg(w, h, "".join(b), list(dict.fromkeys(dnas)), "rows")


def page(gens, table, names, dna, weights, levels):
    """docs/PROGRESS.md: the goal, where the body stands, the graphs, and where it practises next."""
    now = [d for d in gens if d["dna"] == dna] or gens
    last = now[-1] if now else None
    best = max(now, key=lambda d: _passed(d)[0] / _passed(d)[1]) if now else None
    lines = ["# HiveMIND: progress toward the goal", "",
             "**The goal:** a body of ternary nets that does what it is asked (questions, conversation, tasks), and gets "
             "better at it by itself, generation after generation.", "",
             "This page is drawn by the hive itself at the end of every generation (`training/progress.py`, run by the "
             "workflow's record step). Hover a point in a graph for its numbers.", ""]
    if last:
        p, n = _passed(last)
        bp, bn = _passed(best)
        lines += [f"**Now:** generation {last.get('generation')} of the {NAMES.get(dna, dna)} body passed {p} of {n} exam tasks "
                  f"({round(100 * p / n)}%). The best so far on this DNA: {best.get('generation')}, {bp} of {bn} ({round(100 * bp / bn)}%).", ""]
    lines += ["![The share of exam tasks the body passed, each generation](progress/score.svg)", "",
              "![Hard kinds, easy kinds and tasks of several parts, passed](progress/parts.svg)", "",
              "![The share of never-practised kinds it passed](progress/carry.svg)", "",
              "![Each kind of task, weakest first](progress/kinds.svg)", "",
              "![Rows taught, each generation](progress/rows.svg)", ""]
    if weights:
        top = sorted(weights.items(), key=lambda kv: -kv[1])[:6]
        lines += ["## Where it practises most next", "",
                  "Practice draws each kind of task by how close the body is to passing it half the time: a kind always passed "
                  "is learned, one never passed has no right program to learn from yet. Most drawn next:", ""]
        lines += [f"- {k}" for k, _ in top] + [""]
    if levels:
        lines += ["## How hard its lessons are now", "",
                  "Each record raises a kind's level when the body passes it 7 times in 10, and lowers it at 3 in 20: "
                  + ", ".join(f"{k} {v}" for k, v in sorted(levels.items())) + ".", ""]
    return "\n".join(lines)


def draw(record=None, out=None, body=None):
    record = Path(record or ROOT / "training" / "reports" / "generations.jsonl")
    out = Path(out or ROOT / "docs" / "progress")
    out.mkdir(parents=True, exist_ok=True)
    gens = load(record)
    try:
        b = json.loads(Path(body or ROOT / "cells" / "body.json").read_text())
    except (OSError, ValueError):
        b = {}
    dna = b.get("dna") or (gens[-1]["dna"] if gens else "t80")
    (out / "score.svg").write_text(share_chart(gens, _passed, "Exam tasks the body passed, each generation",
                                               "a fresh exam of the grown body at the end of every generation; faint dots were trials"))
    (out / "carry.svg").write_text(share_chart(gens, _carried, "Kinds of task it has never practised, passed",
                                               "does what it learns carry over to work it was never taught? (few tasks each: read the trend)"))
    table, names = kinds(gens, dna)
    (out / "kinds.svg").write_text(kinds_chart(table, names, dna))
    (out / "rows.svg").write_text(rows_chart(gens))
    (out / "parts.svg").write_text(parts_chart(gens))
    from training.grow import edge_weights
    weights = edge_weights(dna, record=record)
    (out.parent / "PROGRESS.md").write_text(page(gens, table, names, dna, weights, b.get("levels") or {}))
    return {"generations": len(gens), "dna": dna, "kinds": len(table), "out": str(out)}


if __name__ == "__main__":
    argv = sys.argv[1:]
    opt = lambda k: argv[argv.index(k) + 1] if k in argv and argv.index(k) + 1 < len(argv) else None  # noqa: E731
    print(json.dumps(draw(opt("--record"), opt("--out"))))

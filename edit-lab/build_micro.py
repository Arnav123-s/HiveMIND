"""Build micro-specialist datasets for the coordinator decomposition.

Pool = edit-lab specialized 56 rows + original training/data/coordinator.jsonl
38 rows (deduped by user text). Each micro-specialist owns ONE behaviour
derived from the eval's checks (training/observe.py eval_coordinator +
team/specialists/coordinator.py normalize):

  size_band       plans of 4-7 steps (decomposition depth; size check)
  pick_researcher plans containing researcher steps (right_agents)
  pick_browser    plans containing browser steps (right_agents)
  pick_coder      plans containing coder steps (right_agents)
  for_each        plans with a for_each fan-out step + composed fan-out
                  rows in non-eval domains (for_each check)
  style_anchor    the full specialized set (valid / clean / done_when /
                  ends_writer house style)

Rows are the repo's own format: {"messages": [system, user], "output": str}.
"""
import json
from pathlib import Path

EL = Path.home() / "workspace/edit-lab"
OUT = EL / "data" / "micro"
OUT.mkdir(parents=True, exist_ok=True)

spec = [json.loads(l) for l in (EL / "data/coordinator_specialized.jsonl").open()]
orig = [json.loads(l) for l in (EL / "tree/training/data/coordinator.jsonl").open()]

pool, seen = [], set()
for r in spec + orig:
    key = r["messages"][1]["content"]
    if key not in seen:
        seen.add(key)
        pool.append(r)


def steps(r):
    try:
        return json.loads(r["output"]).get("steps", [])
    except Exception:
        return []


def agents(r):
    return {s.get("agent") for s in steps(r)}


SYSTEM = spec[0]["messages"][0]["content"]


def composed(task, plan_steps):
    return {"messages": [{"role": "system", "content": SYSTEM},
                         {"role": "user", "content": f"Task from Arnav:\n{task}"}],
            "output": json.dumps({"steps": plan_steps})}


def st(i, agent, task, needs, fe, dw):
    return {"id": f"s{i}", "agent": agent, "task": task, "needs": needs,
            "for_each": fe, "done_when": dw}


# Composed fan-out rows: domains disjoint from the held-out eval tasks.
fanout = [
    composed("For each of the 4 most starred Python web frameworks on GitHub, open its repository page and note the latest release version.",
             [st(1, "researcher", "Search the web for the 4 most starred Python web frameworks on GitHub and list their repository URLs", [], None, "4 framework repo URLs listed"),
              st(2, "browser", "Open the repository page https://github.com/{item} and read the latest release version shown", ["s1"], "s1", "latest release version read for each of the 4 frameworks"),
              st(3, "writer", "Write the comparison of the 4 frameworks with their latest release versions", ["s2"], None, "the answer lists all 4 frameworks with versions")]),
    composed("For each of the 3 newest arXiv papers on diffusion models, open the abstract page and copy the first sentence of the abstract.",
             [st(1, "researcher", "Search arxiv for the 3 newest papers on diffusion models and list their arXiv ids", [], None, "3 arXiv ids listed newest first"),
              st(2, "browser", "Open https://arxiv.org/abs/{item} and copy the first sentence of the abstract", ["s1"], "s1", "first abstract sentence copied for each of the 3 papers"),
              st(3, "writer", "Write the list of the 3 papers with their first abstract sentences", ["s2"], None, "the answer lists all 3 papers with the sentences")]),
    composed("For each of the 5 moons of Pluto, open its Wikipedia page and record its diameter.",
             [st(1, "researcher", "Search wikipedia for the moons of Pluto and list the 5 moon names", [], None, "5 moon names listed"),
              st(2, "browser", "Open the Wikipedia page of {item} and read the diameter from the infobox", ["s1"], "s1", "diameter read for each of the 5 moons"),
              st(3, "writer", "Write the table of Pluto's 5 moons with their diameters", ["s2"], None, "the answer lists all 5 moons with diameters")]),
    composed("For each of these 4 cities - Oslo, Cairo, Perth, Lima - get tomorrow's maximum temperature from Open-Meteo.",
             [st(1, "coder", "Write down the 4 city names with their latitude and longitude: Oslo, Cairo, Perth, Lima", [], None, "4 cities listed with coordinates"),
              st(2, "coder", "Call the Open-Meteo forecast API for {item} and read tomorrow's maximum temperature", ["s1"], "s1", "tomorrow's max temperature read for each of the 4 cities"),
              st(3, "writer", "Write the comparison of tomorrow's maximum temperature for the 4 cities", ["s2"], None, "the answer lists all 4 cities with temperatures")]),
    composed("For each of the top 4 stories on Hacker News right now, open the story link and write down its first paragraph.",
             [st(1, "researcher", "Search hn for the top 4 stories right now and list their titles and links", [], None, "4 story titles and links listed"),
              st(2, "browser", "Open the story link {item} and copy the first paragraph of the page", ["s1"], "s1", "first paragraph copied for each of the 4 stories"),
              st(3, "writer", "Write the digest of the 4 stories with their first paragraphs", ["s2"], None, "the answer covers all 4 stories")]),
    composed("For each of these Python packages - polars, duckdb, rich, typer - open its PyPI page and note the summary line.",
             [st(1, "researcher", "List the 4 PyPI package names: polars, duckdb, rich, typer", [], None, "4 package names listed"),
              st(2, "browser", "Open https://pypi.org/project/{item} and read the summary line at the top of the page", ["s1"], "s1", "summary line read for each of the 4 packages"),
              st(3, "writer", "Write the overview of the 4 packages with their summary lines", ["s2"], None, "the answer lists all 4 packages with summaries")]),
]

sets = {
    "size_band": [r for r in pool if 4 <= len(steps(r)) <= 7],
    "pick_researcher": [r for r in pool if "researcher" in agents(r)],
    "pick_browser": [r for r in pool if "browser" in agents(r)],
    "pick_coder": [r for r in pool if "coder" in agents(r)],
    "for_each": [r for r in pool if any(s.get("for_each") for s in steps(r))] + fanout,
    "style_anchor": spec,
}

for name, rows in sets.items():
    with (OUT / f"{name}.jsonl").open("w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    print(f"{name}: {len(rows)} rows")

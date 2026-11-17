"""docs/MAP.md stays true: every job of grow.yml is on it, and every repository path it names exists."""
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
MAP = (ROOT / "docs" / "MAP.md").read_text()
EXT = re.compile(r"\.(py|md|json|jsonl|csv|yml|yaml|sh|ipynb|txt|svg)$")


def _paths():
    """Each word inside `backticks` that looks like a repository path (has a / or a file ending), globs left out."""
    for span in re.findall(r"`([^`\n]+)`", MAP):
        for word in span.split():
            word = word.removeprefix("./")
            if word.startswith("-") or any(c in word for c in "*<>${}|:"):
                continue
            if "/" in word or EXT.search(word) or word in ("hive",):
                yield word


def test_every_job_of_the_workflow_is_on_the_map():
    flow = yaml.safe_load((ROOT / ".github" / "workflows" / "grow.yml").read_text())
    jobs = list(flow["jobs"])
    assert len(jobs) >= 10
    missing = [j for j in jobs if not re.search(rf"\b{re.escape(j)}\b", MAP)]
    assert not missing, f"jobs of grow.yml not on docs/MAP.md: {missing}"


def test_every_needs_edge_is_drawn():
    flow = yaml.safe_load((ROOT / ".github" / "workflows" / "grow.yml").read_text())
    graph = MAP.split("```mermaid", 1)[1].split("```", 1)[0]
    edges = set(re.findall(r"^\s*(\w+) --(?: \"[^\"]*\" --)?> (\w+)", graph, re.M))
    for job, spec in flow["jobs"].items():
        needs = spec.get("needs") or []
        for n in [needs] if isinstance(needs, str) else needs:
            assert (n, job) in edges, f"{n} -> {job} is a needs: of grow.yml but not drawn"


def test_every_path_the_map_names_exists():
    paths = sorted(set(_paths()))
    assert len(paths) > 40
    missing = [p for p in paths if not (ROOT / p).exists()]
    assert not missing, f"paths named on docs/MAP.md that do not exist: {missing}"

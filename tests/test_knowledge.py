"""What is known about HiveMIND (docs/knowledge.json) holds together, and is drawn as the graphs of docs/KNOWLEDGE.md."""
import copy
import importlib.util
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("knowledge", ROOT / "scripts" / "knowledge.py")
knowledge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(knowledge)


def test_the_knowledge_holds_together_and_the_page_is_drawn_from_it():
    k = knowledge.load()
    assert knowledge.problems(k) == []  # every link names something that exists, every file is there
    page = knowledge.page(k)
    assert len(re.findall(r"```mermaid\n", page)) == 3 and k["goal"] in page
    assert (ROOT / "docs" / "KNOWLEDGE.md").read_text() == page  # the page in the repository is drawn from the file as it is


def test_what_does_not_hold_together_is_named():
    k = knowledge.load()
    bad = copy.deepcopy(k)
    bad["findings"][0]["lives_in"] = "nowhere"
    bad["findings"][1]["blocks"] = "no such problem"
    bad["findings"][2]["status"] = "maybe"
    bad["parts"][0]["file"] = "no/such/file.py"
    bad["open"][0]["owner"] = "Z"
    bad["rules"].append(dict(bad["rules"][0]))
    said = " | ".join(knowledge.problems(bad))
    for words in ("lives in nowhere", "blocks no such problem", "status is maybe", "no file no/such/file.py", "owner Z", "used twice"):
        assert words in said

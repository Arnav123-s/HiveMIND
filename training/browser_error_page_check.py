"""The browser starts on the address it invented in runs 2 and 4 (a 404 page) and must reach the model page."""
import json, sys, tempfile, time
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))
from team.board import Board
from team.guard import Guard
from team.specialists import browser_agent
task = "Open the Hugging Face model page for HuggingFaceTB/SmolLM2-135M-Instruct and read its licence"
b = Board(tempfile.mkdtemp(), echo=True)
g = Guard(b, "never", goal=task)
t = time.time()
r = browser_agent.run(task, "", b, "s2", g, start_url="https://huggingface.co/models/HuggingFaceTB/SmolLM2-135M-Instruct")
print("\n".join(r.get("actions", [])))
print(json.dumps({k: (v[:200] if isinstance(v, str) else v) for k, v in r.items() if k in ("summary", "evidence", "url", "failed")}, indent=1))
print(f"{time.time() - t:.0f} s")

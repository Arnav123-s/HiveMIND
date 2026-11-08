"""Every kind of task, through the whole hive: does it work, how long, and which members did the work.

    python training/hive_bench.py <tag> [task ids...] [--heldout]
The development tasks (TASKS) are the ones fixes are tried on. HELDOUT tasks were written before the fixes and are run
once at the end, so a pass there is not tuning to them.
Each task runs as `python -m team` (risky actions: never) with its own empty memory, so runs cannot steer each other.
A check reads the report and the files made; where the answer lives on a website, the check reads it live.
Cost: every model call is logged with its member, model and seconds (calls.jsonl); cell calls are counted from the
board. Writes training/reports/hive_bench/<tag>.json and .md.
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "training" / "reports" / "hive_bench"
RUNS = ROOT / "runs" / "bench"


def _get(url):
    import requests
    return requests.get(url, timeout=30).text


def _body(report):
    """The deliverable without the hive's own sections (instructions, sources, not confirmed...)."""
    return report.split("\n## ")[0].strip()


def _sentences(text):
    return [s for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()]


def files(run, ext):
    return sorted((run / "work").rglob(f"*{ext}"))


def books_truth():
    from bs4 import BeautifulSoup
    prices = []
    url = "https://books.toscrape.com/catalogue/category/books/mystery_3/index.html"
    while url:
        soup = BeautifulSoup(_get(url), "html.parser")
        prices += [p.text.strip().lstrip("Â£") for p in soup.select("p.price_color")]
        nxt = soup.select_one("li.next a")
        url = url.rsplit("/", 1)[0] + "/" + nxt["href"] if nxt else None
    return sorted(prices, key=float)[:3]


def quotes_truth():
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(_get("https://quotes.toscrape.com/tag/inspirational/"), "html.parser")
    return [q.select_one("span.text").text.strip("“”\"") for q in soup.select("div.quote")[:3]]


def check_arxiv(run, report):
    """Three papers, each really about mixture of experts (its arXiv title or abstract says so) and each with its real
    date. The first check (3 list items and one arXiv link) passed a report that listed two unrelated papers and gave
    every paper today's date."""
    import xml.etree.ElementTree as ET
    ids = list(dict.fromkeys(re.findall(r"(\d{4}\.\d{4,5})(?:v\d+)?", report)))[:3]
    if len(ids) < 3:
        return False, f"{len(ids)} arXiv papers named"
    ns = {"a": "http://www.w3.org/2005/Atom"}
    root = ET.fromstring(_get(f"https://export.arxiv.org/api/query?id_list={','.join(ids)}"))
    body, bad = _body(report), []
    for e in root.findall("a:entry", ns):
        pid = re.search(r"(\d{4}\.\d{4,5})", e.findtext("a:id", "", ns)).group(1)
        text = (e.findtext("a:title", "", ns) + " " + e.findtext("a:summary", "", ns)).lower()
        if not re.search(r"mixture[- ]of[- ]experts?|\bmoe\b", text):
            bad.append(f"{pid} is not about mixture of experts")
        d = e.findtext("a:published", "", ns)[:10]
        y, m, day = d.split("-")
        months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
                  "November", "December"]
        forms = [d, f"{int(day)} {months[int(m) - 1]} {y}", f"{months[int(m) - 1]} {int(day)}, {y}",
                 f"{int(day)} {months[int(m) - 1][:3]} {y}", f"{months[int(m) - 1][:3]} {int(day)}, {y}"]
        if not any(f.lower() in body.lower() for f in forms):
            bad.append(f"{pid}: its date {d} is not given")
    return not bad, "; ".join(bad) or "3 mixture-of-experts papers with their dates"


def check_csv(run, report):
    cs = files(run, ".csv")
    if not cs:
        return False, "no CSV made"
    text = cs[0].read_text(errors="ignore")
    want = books_truth()
    got = [p for p in want if p in text]
    return len(got) == 3, f"CSV has {len(got)}/3 of the cheapest prices {want}"


def check_quotes(run, report):
    want = quotes_truth()
    got = [q for q in want if q[:40].lower() in report.lower()]
    return len(got) >= 2, f"{len(got)}/3 of the first three quotes"


def check_chart(run, report):
    import requests
    d = {m: requests.get(f"https://huggingface.co/api/models/{m}", timeout=30).json().get("downloads", 0)
         for m in ("Qwen/Qwen3-1.7B", "HuggingFaceTB/SmolLM2-360M-Instruct")}
    top = max(d, key=d.get)
    png = files(run, ".png")
    named = top.split("/")[1].lower() in _body(report).lower()
    return bool(png) and named, f"chart: {'yes' if png else 'no'}, names the most downloaded ({top}): {named}"


def has(*words, any_of=(), max_sentences=None, max_lines=None):
    def check(run, report):
        body = _body(report)
        low = body.lower()
        miss = [w for w in words if w.lower() not in low]
        if any_of and not any(w.lower() in low for w in any_of):
            miss.append(" or ".join(any_of))
        n_s, n_l = len(_sentences(body)), len([ln for ln in body.split("\n") if ln.strip()])
        ok = not miss and (max_sentences is None or n_s <= max_sentences) and (max_lines is None or n_l <= max_lines)
        return ok, (f"missing {miss}; " if miss else "") + f"{n_s} sentences, {n_l} lines"
    return check


BRIDGE = ("The Ridgeway bridge, built in 1932, was closed in March for repairs after inspectors found cracks in two "
          "support beams. The city expects the work to take eight months and cost 4.2 million dollars. Until it "
          "reopens, buses will use the Elm Street detour.")
TASKS = [  # (id, kind, task, check)
    ("lookup", "facts from a source",
     "Find the licence and the parameter count of HuggingFaceTB/SmolLM2-135M-Instruct on Hugging Face and give me a "
     "two-line summary. Do not log in or pay.", has("apache", "0.135", max_lines=2)),
    ("arxiv", "list from a source", "List the three newest arXiv papers about mixture of experts, with their titles and dates.",
     check_arxiv),
    ("chart", "numbers + chart", "Which has more downloads on Hugging Face, Qwen/Qwen3-1.7B or "
     "HuggingFaceTB/SmolLM2-360M-Instruct? Make a bar chart of the two.", check_chart),
    ("quotes", "operate a website", "On quotes.toscrape.com, open the page for the tag 'inspirational' and list the "
     "first three quotes.", check_quotes),
    ("csv", "scrape to a file", "Find the three cheapest Mystery books on books.toscrape.com and save them to a CSV.",
     check_csv),
    ("percent", "arithmetic", "What is 17.5% of 2,340? Give the number to two decimals.", has("409.5")),
    ("days", "dates", "How many days are there from 15 January 2026 to 1 March 2026?", has("45")),
    ("units", "unit conversion", "Convert 72 degrees Fahrenheit to Celsius, to one decimal place.", has("22.2")),
    ("translate", "translate given text", "Translate into French: 'The meeting has been moved to Friday afternoon.'",
     has("vendredi", "réunion")),
    ("summary", "summarise given text", f"Summarise this in one sentence: {BRIDGE}",
     has("bridge", any_of=("eight months", "8 months", "4.2"), max_sentences=1)),
    ("grammar", "fix given text", "Correct the grammar of this sentence and give me only the corrected sentence: "
     "'She don't like the apples that was on the table.'", has("doesn't", "were", max_sentences=1)),
    ("email", "draft", "Write a two-sentence email to Priya declining Friday's 3pm meeting and suggesting Monday instead.",
     has("Priya", "Monday", max_sentences=3)),
    ("fib", "write and run code", "Write a Python function that returns the n-th Fibonacci number (fib(1) = 1, "
     "fib(2) = 1) and tell me fib(30).", has("832040")),
    ("bugfix", "fix code", "This Python code should print the sum of the even numbers from 1 to 10 but prints the wrong "
     "answer. Fix it and tell me the right answer:\ntotal = 0\nfor i in range(1, 10):\n    if i % 2 == 0:\n"
     "        total += i\nprint(total)", has("30")),
    ("explain", "explain from knowledge", "In three sentences, explain what a mixture-of-experts model is.",
     has("expert", any_of=("router", "routing", "gate", "gating"), max_sentences=4)),
    ("sales", "reason over given data", "Monthly sales: Jan 120, Feb 95, Mar 143, Apr 110. Which month had the highest "
     "sales, and what was the average per month?", has("117", any_of=("Mar", "March"))),
]


# ---------------------------------------------------------------- held out: written before the fixes, run once at the end
# Same kinds, other wording and content; never run while fixing (so passing them is not tuning to them).
def hf_params(model):
    import requests
    st = requests.get(f"https://huggingface.co/api/models/{model}", params={"expand[]": "safetensors"}, timeout=30).json()
    return f"{(st.get('safetensors') or {}).get('total', 0) / 1e9:.3f}"


def check_ho_lookup(run, report):
    p = hf_params("Qwen/Qwen2.5-0.5B-Instruct")
    ok = "apache" in report.lower() and p in report
    return ok, f"licence apache and {p}B parameters in the report: {ok}"


def check_ho_pypi(run, report):
    import requests
    v = requests.get("https://pypi.org/pypi/requests/json", timeout=30).json()["info"]["version"]
    return v in _body(report), f"latest requests {v} in the answer"


def check_ho_chart(run, report):
    import requests
    d = {m: requests.get(f"https://huggingface.co/api/models/{m}", timeout=30).json().get("downloads", 0)
         for m in ("distilbert/distilbert-base-uncased", "google-bert/bert-base-uncased")}
    top = max(d, key=d.get).split("/")[1]
    png = files(run, ".png")
    return bool(png) and top in _body(report).lower(), f"chart: {bool(png)}, names {top}"


def check_ho_poetry(run, report):
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(_get("https://books.toscrape.com/catalogue/category/books/poetry_23/index.html"), "html.parser")
    first = soup.select_one("article.product_pod")
    title, price = first.h3.a["title"], first.select_one("p.price_color").text.strip().lstrip("Â£")
    ok = title[:25].lower() in report.lower() and price in report
    return ok, f"first Poetry book '{title[:40]}' at {price}: {ok}"


def check_ho_quotes_csv(run, report):
    from bs4 import BeautifulSoup
    cs = files(run, ".csv")
    if not cs:
        return False, "no CSV made"
    soup = BeautifulSoup(_get("https://quotes.toscrape.com/"), "html.parser")
    authors = {a.text for a in soup.select("small.author")}
    text = cs[0].read_text(errors="ignore")
    got = [a for a in authors if a in text]
    return len(got) >= len(authors) - 1, f"CSV has {len(got)}/{len(authors)} authors of page 1"


OFFICE = ("Starting 1 June, the design team moves from the third floor to the new building on Harbour Road. Desks will be "
          "packed on 30 May, and IT will reconnect every computer over the weekend. Parking at the new site is free.")
HELDOUT = [
    ("ho_lookup", "facts from a source", "What licence does Qwen/Qwen2.5-0.5B-Instruct use on Hugging Face, and how many "
     "parameters does it have?", check_ho_lookup),
    ("ho_pypi", "facts from a source", "What is the latest version of the requests package on PyPI?", check_ho_pypi),
    ("ho_chart", "numbers + chart", "Plot the Hugging Face download counts of distilbert/distilbert-base-uncased and "
     "google-bert/bert-base-uncased as a bar chart and tell me which is higher.", check_ho_chart),
    ("ho_poetry", "operate a website", "On books.toscrape.com, open the Poetry category and tell me the title and price "
     "of the first book listed.", check_ho_poetry),
    ("ho_quotes_csv", "scrape to a file", "Save the text and author of every quote on the first page of "
     "quotes.toscrape.com to a CSV file.", check_ho_quotes_csv),
    ("ho_discount", "arithmetic", "A jacket costs 80 euros and is reduced by 35%. What is the new price?", has("52")),
    ("ho_weekday", "dates", "What day of the week was 4 July 1976?", has("Sunday")),
    ("ho_miles", "unit conversion", "How many kilometres is 26.2 miles? One decimal place.", has("42.2")),
    ("ho_spanish", "translate given text", "Translate into Spanish: 'The library closes at eight tonight.'",
     has("biblioteca", "ocho")),
    ("ho_office", "summarise given text", f"Summarise in one sentence: {OFFICE}",
     has("Harbour Road", any_of=("1 June", "June 1"), max_sentences=1)),
    ("ho_polite", "fix given text", "Rewrite this to sound polite and give me only the new sentence: 'Send me the file now.'",
     has("please", "file", max_sentences=2)),
    ("ho_notice", "draft", "Write a three-sentence message to the team saying the office is closed on Monday for "
     "maintenance.", has("Monday", "maintenance", max_sentences=4)),
    ("ho_palindrome", "write and run code", "Write a Python function that checks whether a string is a palindrome and "
     "tell me its result for 'racecar' and for 'python'.", has("racecar", "true", "false")),
    ("ho_bugmax", "fix code", "This Python code should print the largest number in the list but prints the smallest. Fix "
     "it and tell me the right output:\nnums = [4, 17, 9, 2]\nprint(min(nums))", has("17")),
    ("ho_explain", "explain from knowledge", "In two sentences, explain what a hash table is.",
     has("key", "hash", max_sentences=3)),
    ("ho_scores", "reason over given data", "Test scores: Ana 78, Ben 92, Caro 85, Dev 61. Who scored highest, and what "
     "is the average score?", has("Ben", "79")),
]


def cost(run):
    calls = [json.loads(ln) for ln in (run / "calls.jsonl").read_text().splitlines()] if (run / "calls.jsonl").exists() else []
    by = {}
    for c in calls:
        k = f"{c['specialist']} ({c.get('model') or '?'})"
        n, s = by.get(k, (0, 0.0))
        by[k] = (n + 1, round(s + (c.get("seconds") or 0), 1))
    ev = [json.loads(ln) for ln in (run / "events.jsonl").read_text().splitlines()] if (run / "events.jsonl").exists() else []
    cells = sum(1 for e in ev if e["agent"].startswith("cell:") and e["kind"] == "answer")
    plan = json.loads((run / "plan.json").read_text()) if (run / "plan.json").exists() else []
    return {"calls": len(calls), "model_seconds": round(sum(c.get("seconds") or 0 for c in calls), 1), "by_member": by,
            "cell_calls": cells, "plan": [s["agent"] for s in plan] if isinstance(plan, list) else plan}


def run_one(tag, tid, task, check, timeout=2400):
    run = RUNS / tag / tid
    if run.exists() and (run / "bench.json").exists():
        return json.loads((run / "bench.json").read_text())
    run.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, AGENT_TEAM_HOME=tempfile.mkdtemp(prefix="bench-memory-"))
    t0 = time.time()
    try:
        p = subprocess.run([sys.executable, "-m", "team", task, "--approve", "never", "--run-dir", str(run)], cwd=ROOT,
                           env=env, capture_output=True, text=True, timeout=timeout)
        note = "" if p.returncode == 0 else f"exit {p.returncode}: {p.stderr.strip().splitlines()[-1][:200] if p.stderr.strip() else ''}"
    except subprocess.TimeoutExpired:
        note = f"timed out after {timeout} s"
    secs = round(time.time() - t0)
    report = (run / "REPORT.md").read_text() if (run / "REPORT.md").exists() else ""
    try:
        ok, why = check(run, report)
    except Exception as e:  # noqa: BLE001 - a broken check is a failed task, with the reason
        ok, why = False, f"check failed: {type(e).__name__}: {e}"
    res = {"id": tid, "ok": bool(ok), "why": why, "seconds": secs, "note": note, **cost(run)}
    (run / "bench.json").write_text(json.dumps(res, indent=1))
    return res


if __name__ == "__main__":
    tag = sys.argv[1]
    held = "--heldout" in sys.argv
    only = {a for a in sys.argv[2:] if not a.startswith("--")}
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for tid, kind, task, check in (HELDOUT if held else TASKS):
        if only and tid not in only:
            continue
        r = run_one(tag, tid, task, check) | {"kind": kind}
        rows.append(r)
        print(f"{'PASS' if r['ok'] else 'FAIL'} {tid:9s} {r['seconds']:5d}s model {r['model_seconds']:6.1f}s "
              f"calls {r['calls']:3d} cells {r['cell_calls']:2d} plan {r['plan']} - {r['why']} {r['note']}", flush=True)
    (OUT / f"{tag}.json").write_text(json.dumps(rows, indent=1))
    lines = [f"# Hive bench: {tag}", "", f"{sum(r['ok'] for r in rows)}/{len(rows)} tasks pass; "
             f"{sum(r['seconds'] for r in rows) / 60:.0f} min in all.", "",
             "| task | kind | pass | time | model time | model calls | cell calls | plan | check |", "|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['id']} | {r['kind']} | {'✅' if r['ok'] else '❌'} | {r['seconds']} s | {r['model_seconds']} s | "
                     f"{r['calls']} | {r['cell_calls']} | {' → '.join(r['plan']) if isinstance(r['plan'], list) else r['plan']} | "
                     f"{r['why']} {r['note']} |")
    (OUT / f"{tag}.md").write_text("\n".join(lines) + "\n")

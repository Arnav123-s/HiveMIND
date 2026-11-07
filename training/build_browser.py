"""Records expert browser runs on real websites as training data.

A scripted expert solves each goal on the live site. At every step we save
exactly what the browser specialist would see (goal, history, focused page
text, numbered elements) and the correct action. Goals, books, tags, models
and articles are disjoint from training/evals/browser_cases.py.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from team.specialists.browser_agent import turn_messages  # noqa: E402
from team.specialists.verifier import quote_in  # noqa: E402
from team.tools.browser import Browser  # noqa: E402

BOOKS = ["Soumission", "Sapiens", "The Requiem Red", "The Boys in the Boat", "Olio", "Mesaerion",
         "Set Me Free", "Shakespeare's Sonnets", "Starving Hearts", "The Black Maria", "Rip it Up",
         "Our Band Could Be", "Libertarianism for Beginners", "It's Only the Himalayas", "The Coming Woman"]
CATEGORIES = ["Mystery", "Historical Fiction", "Classics", "Romance", "Science", "Humor", "Fantasy"]
TAGS = ["life", "books", "friendship", "inspirational", "reading", "truth"]
AUTHORS = ["Jane Austen", "J.K. Rowling", "Marilyn Monroe", "Thomas A. Edison", "Eleanor Roosevelt", "Steve Martin"]
HF_MODELS = ["Qwen/Qwen2.5-1.5B-Instruct", "HuggingFaceTB/SmolLM2-360M-Instruct", "Qwen/Qwen3-1.7B",
             "microsoft/Phi-3-mini-4k-instruct", "HuggingFaceTB/SmolLM3-3B", "TinyLlama/TinyLlama-1.1B-Chat-v1.0",
             "Qwen/Qwen2.5-Coder-1.5B-Instruct", "HuggingFaceTB/SmolLM2-1.7B-Instruct", "Qwen/Qwen3-4B",
             "Qwen/Qwen2.5-3B-Instruct"]
WIKI = [("When was the Linux kernel first released?", "Linux", r"17 September 1991|1991"),
        ("Who designed the Rust programming language?", "Rust_(programming_language)", r"Graydon Hoare"),
        ("When was Git first released?", "Git", r"2005"),
        ("What year was the World Wide Web invented?", "World_Wide_Web", r"1989")]


def ev_around(text, pattern, before=60, after=90):
    for ln in text.split("\n"):
        m = re.search(pattern, ln)
        if m:
            return ln[max(0, m.start() - before):m.end() + after].strip()
    return None


def ev_lines(text, pattern, n=3):
    lines = [ln for ln in text.split("\n")]
    for i, ln in enumerate(lines):
        if re.search(pattern, ln):
            return "\n".join(x.strip() for x in lines[i:i + n] if x.strip())
    return None


class Recorder:
    def __init__(self):
        self.b = Browser()
        self.rows = []
        self.bad = 0

    def episode(self, goal, start, program):
        """program: list of callables(obs, page_text, elements) -> action dict"""
        b = self.b
        history, rows = [], []
        try:
            b.goto(start) if start != "about:blank" else b.page.goto("about:blank")
            for n, expert in enumerate(program):
                obs = b.observe(goal)
                text = b.text(20000)
                shown = {int(m) for m in re.findall(r"^\[(\d+)\]", obs["elements"], re.M)}
                action = expert(obs, text, {k: v for k, v in b.elements.items() if k in shown})
                if action is None:
                    raise RuntimeError("expert could not act")
                if action["action"] == "done" and not quote_in(action["evidence"], text):
                    raise RuntimeError(f"evidence not on page: {action['evidence'][:60]}")
                rows.append({"messages": turn_messages(goal, obs, history), "output": json.dumps(action, ensure_ascii=False)})
                if action["action"] in ("done", "fail"):
                    break
                el = b.elements.get(action.get("id")) if "id" in action else None
                url = b.act(action)
                label = f" '{el['text'][:40]}'" if el else ""
                history.append(f"{n + 1}. {action['action']}{label} -> now at {url}")
            self.rows += rows
            print(f"ok   {goal[:70]} ({len(rows)} steps)", flush=True)
        except Exception as e:  # noqa: BLE001
            self.bad += 1
            print(f"skip {goal[:70]}: {str(e)[:120]}", flush=True)


def click(pattern, href=None):
    def f(obs, text, els):
        for e in els.values():
            if re.search(pattern, e["text"]) and (href is None or re.search(href, e["href"])):
                return {"action": "click", "id": e["id"]}
        return None
    return f


def type_search(words):
    def f(obs, text, els):
        for e in els.values():
            if e["tag"] == "input" and e["search"]:
                return {"action": "type", "id": e["id"], "text": words, "enter": True}
        return None
    return f


def goto(url):
    return lambda obs, text, els: {"action": "goto", "url": url}


def done(answer_fn, ev_fn):
    def f(obs, text, els):
        ev = ev_fn(text)
        return {"action": "done", "answer": answer_fn(text, ev), "evidence": ev} if ev else None
    return f


def fail(reason):
    return lambda obs, text, els: {"action": "fail", "reason": reason}


def main():
    r = Recorder()
    price = lambda t: ev_lines(t, r"^£\d+\.\d\d$", 2)  # noqa: E731
    for i, book in enumerate(BOOKS):
        goal = f"Find the price of the book '{book}'"
        prefix = re.escape(book[:12])
        prog = [click(prefix, r"catalogue/"), done(lambda t, ev: f"'{book}' costs {ev.split(chr(10))[0]}", price)]
        if i % 3 == 0:
            goal += " on books.toscrape.com"
            prog = [goto("https://books.toscrape.com/")] + prog
            r.episode(goal, "about:blank", prog)
        else:
            r.episode(goal, "https://books.toscrape.com/", prog)
    for cat in CATEGORIES:
        r.episode(f"Open the {cat} category on books.toscrape.com and report how many results it has",
                  "https://books.toscrape.com/",
                  [click(f"^{re.escape(cat)}$"),
                   done(lambda t, ev: f"{ev.split(' results')[0]} results", lambda t: ev_around(t, r"\d+ results?\b", 0, 25))])
    for tag in TAGS:
        r.episode(f"Find quotes tagged '{tag}' on quotes.toscrape.com and tell me the first one",
                  "https://quotes.toscrape.com/",
                  [click(f"^{re.escape(tag)}$", r"/tag/"),
                   done(lambda t, ev: ev.replace("\n", " "), lambda t: ev_lines(t, r"^“", 3))])
    r.episode("Find the first quote on the second page of quotes.toscrape.com", "https://quotes.toscrape.com/",
              [click(r"Next"), done(lambda t, ev: ev.replace("\n", " "), lambda t: ev_lines(t, r"^“", 3))])
    for m in HF_MODELS:
        r.episode(f"Find the license of the model {m}", f"https://huggingface.co/{m}",
                  [done(lambda t, ev: ev.replace("\n", " "), lambda t: ev_lines(t, r"^License:", 2))])
        r.episode(f"Find the size of the weights files of {m}", f"https://huggingface.co/{m}",
                  [click(r"^Files and versions"),
                   done(lambda t, ev: ev.replace("\n", " "), lambda t: ev_lines(t, r"\.safetensors$", 3))])
    for q, art, pat in WIKI:
        r.episode(q, f"https://en.wikipedia.org/wiki/{art}",
                  [done(lambda t, ev: ev, lambda t, p=pat: ev_around(t, p))])
    r.episode("Search Wikipedia for 'Raspberry Pi' and tell me when it was first released",
              "https://en.wikipedia.org/wiki/Main_Page",
              [type_search("Raspberry Pi"), done(lambda t, ev: ev, lambda t: ev_around(t, r"20(12|11)"))])
    r.episode("Open the Python FAQs", "https://docs.python.org/3/",
              [click(r"^FAQs?|Python FAQs"), done(lambda t, ev: "Opened the Python FAQ index", lambda t: ev_lines(t, r"FAQ", 1))])
    # Arnav's rules: refuse, do not try
    refusals = [
        ("Create an account on books.toscrape.com for me", "https://books.toscrape.com/",
         "Creating accounts is against Arnav's rules (no sign-ups)."),
        ("Sign up for a Hugging Face account", "https://huggingface.co/models",
         "Sign-ups are against Arnav's rules."),
        ("Log in to Hugging Face and like the Qwen3-1.7B model", "https://huggingface.co/Qwen/Qwen3-1.7B",
         "Logging in was not allowed by Arnav for this task."),
        ("Add 'Soumission' to the basket and check out", "https://books.toscrape.com/",
         "Buying needs Arnav's approval first; I will not spend money."),
        ("Purchase the book 'Sharp Objects' for me", "https://books.toscrape.com/catalogue/sharp-objects_997/index.html",
         "Spending money needs Arnav's approval first."),
        ("Log in to quotes.toscrape.com and post a new quote", "https://quotes.toscrape.com/tag/life/",
         "Logging in and posting as Arnav are not allowed without his approval."),
    ]
    for goal, start, reason in refusals:
        r.episode(goal, start, [fail(reason)])
    r.b.close()
    out = ROOT / "training" / "data" / "browser.jsonl"
    with open(out, "w") as f:
        for row in r.rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"browser: {len(r.rows)} steps, {r.bad} episodes skipped -> {out}")


if __name__ == "__main__":
    main()

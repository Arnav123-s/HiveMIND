"""More browser skills, recorded from a scripted expert on the live sites (training/data/browser_skills.jsonl).

The browser failed at these in real runs, so the expert shows each one:
- after an error page the hive opens the home page: carry on from there with links or the search box
- list several items: copy each from the page, joined with " ... "
- start on a page an earlier step reached, and work from it
- "without logging in" is an ordinary task: click ordinary links (it replied "cannot click without approval")
- use a site's search box
Sites, tags, categories, books and topics are disjoint from the hive bench (training/hive_bench.py: development and
held-out tasks) and from the browser evals (training/evals/browser_cases.py). Not the 'life' tag: its first
quote is one of the bench's 'inspirational' answers.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from training.build_browser import Recorder, click, done, ev_lines, type_search  # noqa: E402
from team.specialists.browser_agent import turn_messages  # noqa: E402
from team.specialists.verifier import quote_in  # noqa: E402

BOOKS = ["Sapiens", "The Requiem Red", "The Boys in the Boat", "Olio", "Set Me Free", "Starving Hearts", "Rip it Up"]
LIST_TAGS = ["books", "friendship", "reading", "truth"]
LIST_CATS = ["Classics", "Romance", "Science", "Humor", "Fantasy", "Historical Fiction"]
START_CATS = [("Classics", "classics_6"), ("Romance", "romance_8"), ("Science", "science_22"), ("Fantasy", "fantasy_19")]
WIKI = [("Lua (programming language)", r"1993"), ("Vim (text editor)", r"1991"), ("PostgreSQL", r"1996"),
        ("Erlang (programming language)", r"1986")]
RECOVERED = ("{bad} does not exist (HTTP error): opened the home page {home} instead. Use its search box or links to reach "
             "the goal.")


class Recorder2(Recorder):
    def episode(self, goal, start, program, history0=()):
        """As Recorder.episode, with history the browser already has (an error page it was moved away from)."""
        b = self.b
        history, rows = list(history0), []
        try:
            b.goto(start)
            for n, expert in enumerate(program, start=len(history0)):
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
                label = f" '{el['text'][:40]}'" if el else ""  # the same line the live browser writes
                history.append(f"{n + 1}. {action['action']}{label} -> now at {url}")
            self.rows += rows
            print(f"ok   {goal[:70]} ({len(rows)} steps)", flush=True)
        except Exception as e:  # noqa: BLE001
            self.bad += 1
            print(f"skip {goal[:70]}: {str(e)[:120]}", flush=True)


def first_quotes(n):
    def ev(t):
        qs = [ln.strip() for ln in t.split("\n") if ln.strip().startswith("“")][:n]
        return " ... ".join(qs) if len(qs) == n else None
    return ev


def first_titles(n):
    def ev(t):
        lines = [ln.strip() for ln in t.split("\n") if ln.strip()]
        out = [lines[i - 1] for i, ln in enumerate(lines) if re.fullmatch(r"£\d+\.\d\d", ln) and i > 0][:n]
        return " ... ".join(out) if len(out) == n else None
    return ev


def first_book(t):
    """The first book's title line and its price line, joined with " ... "."""
    title = first_titles(1)(t)
    p = ev_lines(t, r"^£\d+\.\d\d$", 1)
    return f"{title} ... {p}" if title and p else None


def first_line(pattern):
    def ev(t):
        return next((ln.strip()[:160] for ln in t.split("\n")
                     if re.search(pattern, ln) and re.search(r"appear|release|first|initial", ln, re.I)), None)
    return ev


def main():
    r = Recorder2()
    price = lambda t: ev_lines(t, r"^£\d+\.\d\d$", 2)  # noqa: E731
    home = "https://books.toscrape.com/"
    for book in BOOKS:  # error page -> the home page -> the book's link
        slug = re.sub(r"[^a-z0-9]+", "-", book.lower()).strip("-")
        bad = f"https://books.toscrape.com/books/{slug}.html"
        r.episode(f"Find the price of the book '{book}' on books.toscrape.com", home,
                  [click(re.escape(book[:12]), r"catalogue/"), done(lambda t, ev, b=book: f"'{b}' costs {ev.split(chr(10))[0]}", price)],
                  history0=[f"0. {RECOVERED.format(bad=bad, home=home)}"])
    for tag in LIST_TAGS:  # several items, joined with " ... "
        r.episode(f"List the first three quotes tagged '{tag}' on quotes.toscrape.com", "https://quotes.toscrape.com/",
                  [click(f"^{re.escape(tag)}$", r"/tag/"),
                   done(lambda t, ev: "The first three: " + ev.replace(" ... ", " | "), first_quotes(3))])
    for cat in LIST_CATS:
        r.episode(f"List the titles of the first three books in the {cat} category on books.toscrape.com", home,
                  [click(f"^{re.escape(cat)}$"), done(lambda t, ev: "First three: " + ev.replace(" ... ", "; "), first_titles(3))])
    for cat, slug in START_CATS:  # work from the page an earlier step reached
        r.episode(f"On this {cat} page, tell me the title and price of the first book listed",
                  f"https://books.toscrape.com/catalogue/category/books/{slug}/index.html",
                  [done(lambda t, ev: ev.replace(" ... ", " costs "), first_book)])
    for tag in ("truth", "books", "reading"):  # "without logging in": ordinary links are fine
        r.episode(f"Without logging in, find quotes tagged '{tag}' and tell me who said the first one",
                  "https://quotes.toscrape.com/",
                  [click(f"^{re.escape(tag)}$", r"/tag/"),
                   done(lambda t, ev: ev.replace("\n", " "), lambda t: ev_lines(t, r"^“", 2))])
    for topic, pat in WIKI:  # a site's search box
        r.episode(f"Search Wikipedia for '{topic}' and tell me when it first appeared", "https://en.wikipedia.org/wiki/Main_Page",
                  [type_search(topic), done(lambda t, ev: ev, first_line(pat))])
    r.b.close()
    out = ROOT / "training" / "data" / "browser_skills.jsonl"
    with open(out, "w") as f:
        for row in r.rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"browser skills: {len(r.rows)} steps, {r.bad} episodes skipped -> {out}")


if __name__ == "__main__":
    main()

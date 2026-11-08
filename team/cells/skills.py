"""The micro-skills, one per cell, each with exact ground truth.

Every skill says which part of the hive it serves, how its input looks, and how to build labelled examples.
Labels come from how each example is built, so scores are exact. Train and dev examples come from one pool of
words and frames; test examples come from a DIFFERENT pool (other objects, sites, verbs, frames), so a test score
measures whether a cell learned the skill or only memorised words.
"""
import json
import random
import re

SPLITS = ("train", "dev", "test")


def _pool(split, train, test):
    return test if split == "test" else train


def _cap(s):
    return s[0].upper() + s[1:] if s else s


# ---------------------------------------------------------------- route_step: which specialist does a plan step
_R = {
    "researcher": (
        ["Find {fact}.", "Look up {fact}.", "Search for {fact}.", "Collect sources on {fact}.", "Which source says {fact}?"],
        ["Gather evidence on {fact}.", "Research {fact}.", "Get cited facts about {fact}.", "Identify {fact}."],
        ["the license of Qwen2.5-0.5B", "the newest stable Python release", "papers on speculative decoding",
         "the population of Lisbon", "who maintains the requests library", "small text-to-speech models",
         "the CEO of Hugging Face", "benchmarks of 1B chat models", "the boiling point of ethanol", "recent Rust releases"],
        ["the release date of Llama 3", "the GDP of Kenya", "studies on sleep and memory", "the author of NumPy",
         "the best-rated CPU-friendly embedding models", "what licence Mistral 7B uses", "the tallest bridge in Europe",
         "reviews of the Framework laptop", "the history of SQLite"]),
    "browser": (
        ["Open {site} and click {thing}.", "Go to {site}, type {q} in the search box and press Enter.",
         "On {site}, scroll to {thing} and read what it shows.", "Navigate to {site} and fill in {thing}."],
        ["Visit {site}, press {thing} and copy the text that appears.", "Load {site} and select {thing} from the menu.",
         "Use the page {site}: click through to {thing}.", "Browse {site} and tick {thing}."],
        ["books.toscrape.com", "quotes.toscrape.com", "the weather page", "news.ycombinator.com"],
        ["example.org", "the shop's product page", "the city library site", "the airline site"]),
    "coder": (
        ["Write and run a script that {job}.", "Compute {job} with Python.", "Benchmark {job}.",
         "Run code to {job}.", "Parse the CSV and {job}."],
        ["Implement a program that {job} and execute it.", "Measure the time it takes to {job}.",
         "Use a Python script to {job}.", "Calculate {job} by running code."],
        ["sorts the prices", "the average rating", "two sorting functions on a million integers", "count words per file",
         "plot temperatures by month"],
        ["deduplicates the rows", "the median latency", "tokenises three files", "convert JSON to CSV",
         "simulate 10,000 dice rolls"]),
    "writer": (
        ["Write the final report from {res}.", "Summarise {res} for Arnav.", "Draft the answer using {res}.",
         "Turn {res} into a comparison table."],
        ["Compose the deliverable from {res}.", "Produce a short brief out of {res}.", "Present {res} as the final answer.",
         "Write up {res} with citations."],
        ["the verified results", "the checked facts", "the benchmark numbers", "what the team found",
         "the facts the verifier passed", "step 2 and step 3 results", "the collected prices"],
        ["the confirmed findings", "the measured timings", "the shortlisted models", "the research notes",
         "everything the jury approved", "the outputs of steps 1-4"]),
}


def gen_route_step(split, r):
    agent = r.choice(list(_R))
    ftr, fte, otr, ote = _R[agent]
    frame = r.choice(_pool(split, ftr, fte))
    objs = _pool(split, otr, ote)
    fill = {k: r.choice(objs) for k in ("fact", "job", "res", "thing", "q")}
    fill["site"] = r.choice(objs)
    if agent == "browser":
        fill["thing"] = r.choice(["the 'Next' button", "the price box", "the login link", "the first result",
                                  "the cookie banner", "the second tab"] if split != "test" else
                                 ["the 'More' link", "the size dropdown", "the checkout icon", "the top story",
                                  "the filters panel"])
        fill["q"] = r.choice(["'travel'", "'python'", "'cheap'"] if split != "test" else ["'poetry'", "'rust'"])
    return frame.format(**fill), agent


# ---------------------------------------------------------------- pick_source: which search source to use
_S = {
    "huggingface": (["{m} models", "an open {m} model", "datasets for {m}", "{m} model weights under 2B"],
                    ["checkpoints for {m}", "a small {m} model to download", "fine-tuned {m} models"],
                    ["text-generation", "speech recognition", "image classification", "embedding", "code completion", "sentiment"],
                    ["text-to-speech", "translation", "object detection", "summarisation", "reranking"]),
    "arxiv": (["papers on {t}", "a recent preprint about {t}", "research on {t}"],
              ["the latest studies of {t}", "academic work on {t}", "a survey paper on {t}"],
              ["speculative decoding", "LoRA fine-tuning", "mixture of experts", "quantisation", "protein folding", "RLHF"],
              ["sparse attention", "model merging", "retrieval augmented generation", "knowledge distillation"]),
    "pypi": (["the latest version of {p}", "a Python package for {t}", "the {p} library release notes"],
             ["which pip package does {t}", "the newest release of the {p} module", "a Python library to {t}"],
             ["requests", "numpy", "pandas", "httpx"], ["polars", "pydantic", "rich", "fastapi"]),
    "wikipedia": (["the history of {w}", "who invented {w}", "an overview of {w}", "when {w} was founded"],
                  ["background on {w}", "the biography behind {w}", "facts about {w}"],
                  ["the transistor", "Lisbon", "the printing press", "Ada Lovelace", "the Roman Empire", "photosynthesis"],
                  ["the steam engine", "Nairobi", "the telescope", "Alan Turing"]),
    "hn": (["what Hacker News thinks of {n}", "the HN discussion about {n}", "tech news about {n}"],
           ["recent comments on Hacker News about {n}", "the top HN thread on {n}", "launch posts about {n}"],
           ["a new database launch", "the latest Rust release", "a startup's outage", "a YC launch", "a new JS framework"],
           ["a new code editor", "a cloud price change", "an open-source fork"]),
    "web": (["the opening hours of {x}", "the price of {x}", "a recipe for {x}", "reviews of {x}"],
            ["where to buy {x}", "the weather forecast for {x}", "directions to {x}", "the menu of {x}"],
            ["the city museum", "a pair of running shoes", "banana bread", "the corner cafe", "a used bike", "the gym nearby"],
            ["the train station", "noise-cancelling headphones", "lentil soup", "a hotel in Porto"]),
}


def gen_pick_source(split, r):
    src = r.choice(list(_S))
    ftr, fte, otr, ote = _S[src]
    frame = r.choice(_pool(split, ftr, fte))
    o = r.choice(_pool(split, otr, ote))
    task = {"pypi": {"p": o, "t": r.choice(["parse dates", "read Excel files", "send HTTP requests"] if split != "test"
                                         else ["validate emails", "draw terminal tables", "serve an API"])}}.get(src, {})
    fill = {k: o for k in "mtwnxp"} | task
    return "Find " + frame.format(**fill) + ".", src


# ---------------------------------------------------------------- next_move: what to do after a step fails
_N = {
    "retry": (["timed out after {s}s", "HTTP 429 too many requests", "connection reset by peer", "HTTP 503 from {h}",
               "the model gave no JSON: {junk}", "program exited 1: NameError: name '{v}' is not defined",
               "program exited 1: SyntaxError: invalid syntax"],
              ["read timed out ({s} s)", "HTTP 502 bad gateway from {h}", "temporary DNS failure for {h}",
               "the reply was not valid JSON: {junk}", "program exited 1: TypeError: unsupported operand type(s)",
               "program exited 1: IndexError: list index out of range"]),
    "reroute": (["browser could not finish: the page needs a JavaScript challenge", "the evidence quoted is not on the page",
                 "no source could be read: {h} blocks automated readers", "search returned 0 results for '{q}'",
                 "browser could not finish: stuck repeating the same click", "the page shows a captcha"],
                ["browser could not finish: element not found after 12 steps", "no source could be read: {h} refused the request",
                 "the search tool found nothing about '{q}'", "browser could not finish: the site kept redirecting",
                 "listed items do not appear in any source", "the page is an image with no text"]),
    "give_up": (["not ordered: paying for {x} needs Arnav's order", "{x} does not exist on the site",
                 "needs a login on {h}, which the order does not name", "touches family matters the order did not ask for",
                 "no space left on device"],
                ["not ordered: deleting {x} needs Arnav's order", "the order says not to sign up, and {h} requires an account",
                 "{x} was removed and no copy exists", "sending as Arnav was not ordered",
                 "the task needs Arnav's password, which is not in the vault"]),
}


def gen_next_move(split, r):
    move = r.choice(list(_N))
    tmpl = r.choice(_pool(split, *_N[move]))
    fill = {"s": r.choice([30, 60, 120]), "h": r.choice(["huggingface.co", "pypi.org", "example.com"] if split != "test"
                                                        else ["arxiv.org", "shop.example", "news.site"]),
            "junk": r.choice(["Sure! Here is", "{'a': 1", "```json"]), "v": r.choice(["df", "rows", "total"]),
            "q": r.choice(["tiny tts models", "rome flights"] if split != "test" else ["cheap gpus", "oslo hotels"]),
            "x": r.choice(["the plan", "the ticket", "the old files"] if split != "test" else ["the boots", "the backup"])}
    step = r.choice(["researcher", "browser", "coder"])
    return f"Step by {step} failed (attempt {r.choice([1, 2])} of 3): " + tmpl.format(**fill), move


# ---------------------------------------------------------------- split_orders: one order -> atomic instructions
_CL_TR = ["find the three cheapest flights to Rome", "compare their baggage fees", "email me the best one",
          "list the five newest Python releases", "check which ones are still supported", "make a table of them",
          "open books.toscrape.com", "note the price of the first book", "write a script that sorts the prices",
          "summarise the results in two lines", "read the Wikipedia page on Lisbon", "tell me its population",
          "search Hugging Face for small TTS models", "keep only Apache-2.0 ones", "benchmark them on CPU"]
_CL_TE = ["look up tomorrow's weather in Oslo", "pick the warmest hour", "remind me what to wear",
          "get the top story on Hacker News", "count its comments", "explain the main argument",
          "download the CSV of sales", "remove the duplicate rows", "plot revenue by month",
          "find two papers on model merging", "quote each abstract's first sentence", "rank them by citations"]
_JOIN = [(", ", ", then "), (", ", " and "), ("; ", "; then "), (". Then ", ". Finally, ")]


def gen_split_orders(split, r):
    clauses = r.sample(_pool(split, _CL_TR, _CL_TE), r.choice([1, 2, 2, 3, 3, 4]))
    sep, last = r.choice(_JOIN[:2] if split != "test" else _JOIN)
    text = clauses[0] if len(clauses) == 1 else sep.join(clauses[:-1]) + last + clauses[-1]
    text = _cap(text) + "."
    return text, "\n".join(_cap(c) for c in clauses)


def score_lines(pred, target):
    norm = [re.sub(r"[^a-z0-9 ]", "", ln.lower()).strip() for ln in pred.strip().split("\n") if ln.strip()]
    gold = [re.sub(r"[^a-z0-9 ]", "", ln.lower()).strip() for ln in target.split("\n")]
    return float(norm == gold)


# ---------------------------------------------------------------- json_repair: broken JSON -> valid JSON
_KEYS_TR = ["agent", "task", "verdict", "reason", "items", "url", "score", "done"]
_KEYS_TE = ["action", "query", "status", "notes", "ids", "source", "count", "ok"]
_VALS = ["researcher", "PASS", "find the price", "books.toscrape.com", 3, 0.5, True, False, None, ["a", "b"], [1, 2]]


def _break(s, obj, r, split):
    ways = ["trailing", "single", "missing_close", "py_literals", "prose", "fence", "unquoted"]
    if split == "test":
        ways += ["prose_after", "two_errors"]
    w = r.choice(ways)
    if w == "trailing":
        return s[:-1] + ", }"
    if w == "single":
        return s.replace('"', "'")
    if w == "missing_close":
        return s[:-1]
    if w == "py_literals":
        return s.replace("true", "True").replace("false", "False").replace("null", "None")
    if w == "prose":
        return r.choice(["Sure! Here is the JSON:\n", "Result: ", "Answer -> "]) + s
    if w == "fence":
        return "```json\n" + s + "\n```"
    if w == "unquoted":
        return re.sub(r'"(\w+)":', r"\1:", s)
    if w == "prose_after":
        return s + r.choice([" Hope this helps!", "\nLet me know if you need more."])
    return (s[:-1] + ", }").replace('"', "'")  # two errors


def gen_json_repair(split, r):
    keys = r.sample(_pool(split, _KEYS_TR, _KEYS_TE), r.choice([1, 2, 3]))
    obj = {k: r.choice(_VALS) for k in keys}
    s = json.dumps(obj)
    return _break(s, obj, r, split), s


def score_json(pred, target):
    try:
        return float(json.loads(pred.strip()) == json.loads(target))
    except Exception:  # noqa: BLE001
        return 0.0


# ---------------------------------------------------------------- orders_<kind>: is this kind ORDERED (yes/no)
def _orders_rows(split, seed):
    from training import build_orders as bo  # one builder for the order reader and its cells: same labels
    if split == "test":
        return bo.build(bo.FRAMES_TEST, bo.OBJ_TEST, bo.DISTRACT_TEST, bo.NEG_TEST, 40, 2)
    rows = bo.build(bo.FRAMES_TRAIN, bo.OBJ_TRAIN, bo.DISTRACT_TRAIN, bo.NEG_TRAIN, 160, 1)
    if split == "dev":
        return rows[150:]
    more = bo.build(bo.FRAMES_TRAIN, bo.OBJ_TRAIN, bo.DISTRACT_TRAIN, bo.NEG_TRAIN, 500, 11)  # more combinations,
    dev = {t for t, _ in rows[150:]}  # same training-only words
    return rows[:150] + [r for r in more if r[0] not in dev]


def _orders_gen(kind):
    def gen(split, r, _cache={}):  # noqa: B006 - per-process cache of the fixed builder output
        if split not in _cache:
            _cache[split] = _orders_rows(split, 0)
        text, kinds = r.choice(_cache[split])
        return text, "yes" if kind in kinds else "no"
    return gen


def gen_orders_any(split, r, _cache={}):  # noqa: B006
    """New skill made by the factory: does the sentence ORDER any risky action at all? (a sibling of the order cells)"""
    if split not in _cache:
        _cache[split] = _orders_rows(split, 0)
    text, kinds = r.choice(_cache[split])
    return text, "yes" if kinds else "no"


# ---------------------------------------------------------------- family_topic: does a step touch family matters
_FAM_TR = ["Plan a birthday dinner for Mom", "Find a gift for my sister", "Write a note to my wife", "Book a table for our anniversary",
           "Help me reply to my ex", "Find a nursery for the baby", "Check flights to visit Grandma", "Draft a message to Dad",
           "Find relationship advice", "Pick a wedding venue"]
_FAM_TE = ["Order flowers for my husband", "Choose a school for our son", "Remind me to call my aunt", "Find a dating app",
           "Summarise the divorce paperwork", "Get Valentine's ideas for my girlfriend", "Plan a trip with the kids",
           "Ask my cousin about the visit"]
_NOF_TR = ["List files in the parent directory", "Kill the child process", "Print to the Brother printer", "Pick a font family",
           "Sort by the date column", "Explain carbon dating", "Find the relationship between price and rating",
           "Compare motherboards under $200", "Call the partner API", "Find the sister city of Lisbon"]
_NOF_TE = ["Check the parent commit", "Reap zombie child threads", "Read the Family Guy wiki trivia", "Set the date format",
           "Plot the relationship between speed and memory", "Read about the mother tongue of Basque", "Find brother-in-arms quotes",
           "Model the kids' section layout of the bookstore site"]
_TAIL = ["", " and send me the link", " before Friday", " and summarise it", ", then make a short list"]


def gen_family_topic(split, r):
    fam = r.random() < 0.5
    base = r.choice(_pool(split, _FAM_TR, _FAM_TE) if fam else _pool(split, _NOF_TR, _NOF_TE))
    return base + r.choice(_TAIL) + ".", "yes" if fam else "no"


# ---------------------------------------------------------------- claim_support: does the quote support the claim
_ENT_TR = [("Qwen2.5-0.5B", "license", "apache-2.0", "mit"), ("SmolLM2-135M", "parameters", "135M", "360M"),
           ("Lisbon", "population", "545,000", "455,000"), ("requests", "latest version", "2.32.3", "2.31.0"),
           ("the hiking boots", "price", "$89", "$98"), ("Llama-3.2-1B", "gated", "yes", "no"),
           ("books.toscrape.com", "number of books", "1000", "100")]
_ENT_TE = [("Phi-3-mini", "license", "mit", "apache-2.0"), ("Gemma-2-2B", "parameters", "2.6B", "2.0B"),
           ("Nairobi", "population", "4.4 million", "3.4 million"), ("numpy", "latest version", "2.1.0", "2.0.1"),
           ("the 3pm train", "price", "€42", "€24"), ("Mistral-7B", "gated", "no", "yes"), ("the forum", "members", "12,400", "1,240")]
_SUP = ["{e} {a}: {v}", "The {a} of {e} is {v}.", "{e} — {a} {v} (as listed)", "As of today, {e} has {a} {v}."]


_ATTR_TR = ["license", "price", "population", "latest version", "release year", "rating", "file size", "parameter count"]
_ATTR_TE = ["capacity", "weight", "opening year", "top speed", "membership fee", "download count", "context length"]
_QF_TR = ["{e} {a}: {v}", "The {a} of {e} is {v}.", "{e} — {a} {v} (as listed)", "As of today, {e} has {a} {v}."]
_QF_TE = ["{e}'s {a} stands at {v}.", "{a} ({e}): {v}", "Listed {a} for {e}: {v}"]
_SYL = ["ka", "lo", "mi", "ren", "tor", "va", "zu", "pel", "dan", "qui", "sor", "bex", "nai", "ul", "fen"]


def _ename(r):
    n = "".join(r.choice(_SYL) for _ in range(r.choice([2, 3]))).capitalize()
    return n + r.choice(["", "", f"-{r.randint(1, 9)}B", " Hotel", " Pro", f" {r.randint(2, 9)}"])


def _val(r):
    k = r.randrange(5)
    if k == 0:
        return f"{r.randint(1, 999):,}", "num"
    if k == 1:
        return f"{r.randint(10, 999) * 10:,}", "num"
    if k == 2:
        return f"{r.choice(['$', '€', '£'])}{r.randint(5, 500)}", "num"
    if k == 3:
        return f"{r.randint(0, 9)}.{r.randint(0, 20)}.{r.randint(0, 9)}", "num"
    return r.choice(["apache-2.0", "mit", "gpl-3.0", "cc-by-4.0", "bsd-3-clause", "4.5 stars", "3.9 stars"]), "word"


def _near(v, r):
    """A value that looks almost the same: one digit off, or another word of the same kind."""
    digits = [i for i, c in enumerate(v) if c.isdigit()]
    if digits:
        i = r.choice(digits)
        return v[:i] + str((int(v[i]) + r.randint(1, 8)) % 10) + v[i + 1:]
    return r.choice([w for w in ["apache-2.0", "mit", "gpl-3.0", "cc-by-4.0", "bsd-3-clause", "4.5 stars", "3.9 stars"] if w != v])


def gen_claim_support(split, r):
    """Made-up entities and values, so the only way to answer is to compare the claim with the quote."""
    e, a = _ename(r), r.choice(_pool(split, _ATTR_TR, _ATTR_TE))
    v, _ = _val(r)
    claim = r.choice([f"The {a} of {e} is {v}.", f"{e} has {a} {v}.", f"{e}'s {a} is {v}."])
    q = r.choice(_pool(split, _QF_TR, _QF_TE))
    if r.random() < 0.5:
        return f"CLAIM: {claim}\nQUOTE: {q.format(e=e, a=a, v=v)}", "SUPPORTED"
    kind = r.choice(["num", "num", "ent", "attr", "neg"])
    if kind == "num":
        quote = q.format(e=e, a=a, v=_near(v, r))
    elif kind == "ent":
        quote = q.format(e=_ename(r), a=a, v=v)
    elif kind == "attr":
        quote = q.format(e=e, a=r.choice([x for x in _pool(split, _ATTR_TR, _ATTR_TE) if x != a]), v=v)
    else:
        quote = f"The {a} of {e} is not {v}."
    return f"CLAIM: {claim}\nQUOTE: {quote}", "UNSUPPORTED"


# ---------------------------------------------------------------- quote_pick: which sentence supports the claim
_FILL_TR = ["The site was updated last week.", "Prices include tax.", "Shipping takes 3-5 days.", "The page has 20 items.",
            "Reviews are moderated.", "The model card was edited in May.", "Downloads are counted monthly."]
_FILL_TE = ["The menu changes every season.", "Opening hours vary on holidays.", "The archive goes back to 2009.",
            "Comments are closed.", "The data is refreshed hourly.", "Support replies within a day."]


def gen_quote_pick(split, r):
    e, a, v, wrong = r.choice(_pool(split, _ENT_TR, _ENT_TE))
    claim = f"The {a} of {e} is {v}."
    n = r.choice([3, 4, 5])
    sents = r.sample(_pool(split, _FILL_TR, _FILL_TE), n - 1)
    has = r.random() < 0.75
    trap = f"The {a} of {e} is {wrong}." if r.random() < 0.5 else f"The {a} of {e} was discussed."
    sents.insert(r.randrange(n), f"{e} lists its {a} as {v}." if has else trap)
    if has and r.random() < 0.5:  # a near-miss distractor too
        sents.insert(r.randrange(len(sents) + 1), trap)
    gold = next((str(i + 1) for i, s in enumerate(sents) if v in s and wrong not in s and "discussed" not in s), "none")
    body = "\n".join(f"{i + 1}. {s}" for i, s in enumerate(sents))
    return f"CLAIM: {claim}\nSENTENCES:\n{body}", gold


# ---------------------------------------------------------------- pick_element: which page element to act on
_UI_TR = ["Next", "Previous", "Login", "Search", "Add to basket", "Checkout", "Poetry", "Travel", "Load more", "Contact",
          "About us", "Pricing", "Download", "Settings", "Help", "Home", "Blog", "Careers", "Cart", "Reviews",
          "Show comments", "Sort by price", "Filters", "Apply", "Subscribe", "Docs", "FAQ", "Profile", "Orders",
          "Gift cards", "Sale", "New arrivals", "Mystery", "History", "Science"]
_UI_TE = ["Older posts", "Newer posts", "Sign in", "Find", "Buy now", "Pay", "Fiction", "Romance", "See all", "Support",
          "Our team", "Plans", "Export", "Preferences", "Guide", "Start", "News", "Jobs", "Basket", "Ratings",
          "Expand replies", "Cheapest first", "Refine", "Confirm", "Follow"]
_GOAL_TR = ["click {t}", "open the {t} page", "go to {t}", "press the {t} button", "select {t}", "show me {t}"]
_GOAL_TE = ["tap {t}", "navigate to {t}", "choose the {t} option", "I need the {t} section", "hit {t}"]
_SYN_TR = [("go to the next page", "Next"), ("go back a page", "Previous"), ("sign in", "Login"), ("buy it", "Add to basket"),
           ("see more results", "Load more"), ("find out what it costs", "Pricing")]
_SYN_TE = [("log in", "Sign in"), ("purchase it", "Buy now"), ("view every item", "See all"), ("see older articles", "Older posts")]
_KIND = ['link', 'button', 'a', 'span']


def gen_pick_element(split, r):
    """Find the element the goal means and answer with its id: match the words (or a common synonym), then copy."""
    labels = _pool(split, _UI_TR, _UI_TE)
    if r.random() < 0.25:
        goal, target = r.choice(_pool(split, _SYN_TR, _SYN_TE))
    else:
        target = r.choice(labels)
        goal = r.choice(_pool(split, _GOAL_TR, _GOAL_TE)).format(t=r.choice([target, target.lower()]))
    others = r.sample([t for t in labels if t != target], r.choice([4, 6, 8]))
    els = others + [target]
    r.shuffle(els)
    ids = r.sample(range(1, 80), len(els))
    lines = [f"[{i}] {r.choice(_KIND)} \"{t}\"" for i, t in zip(ids, els)]
    if r.random() < 0.3:  # inputs and plain text the browser also lists
        lines.insert(r.randrange(len(lines) + 1), f"[{r.choice([x for x in range(80, 99)])}] input[text] \"\"")
    return f"GOAL: {goal}\nELEMENTS:\n" + "\n".join(lines), str(ids[els.index(target)])


def gen_element_match(split, r):
    """The smaller skill inside pick_element: does THIS one element reach the goal? yes or no.
    The pick_element organizer asks it once per element and acts on the most likely yes."""
    labels = _pool(split, _UI_TR, _UI_TE)
    if r.random() < 0.25:
        goal, target = r.choice(_pool(split, _SYN_TR, _SYN_TE))
    else:
        target = r.choice(labels)
        goal = r.choice(_pool(split, _GOAL_TR, _GOAL_TE)).format(t=r.choice([target, target.lower()]))
    yes = r.random() < 0.5
    label = target if yes else r.choice([t for t in labels if t != target] + [""])
    kind = "input[text]" if label == "" else r.choice(_KIND)
    return f'GOAL: {goal}\nELEMENT: {kind} "{label}"', "yes" if yes else "no"


# ---------------------------------------------------------------- licence_open: new skill made by the factory
_LIC_TR = [("apache-2.0", "yes"), ("mit", "yes"), ("bsd-3-clause", "yes"), ("cc-by-nc-4.0", "no"), ("llama3.2", "no"),
           ("gemma", "no"), ("openrail", "no"), ("other", "no"), ("cc-by-4.0", "yes"), ("gpl-3.0", "no")]
_LIC_TE = [("Apache 2.0", "yes"), ("MIT License", "yes"), ("bsd-2-clause", "yes"), ("cc-by-nc-sa-4.0", "no"),
           ("llama2", "no"), ("research-only", "no"), ("creativeml-openrail-m", "no"), ("unknown", "no"), ("isc", "yes")]


_LIC_FMT_TR = ["{m} | license {l}", "{m} | {l} | downloads {d}", "License: {l} ({m})"]
_LIC_FMT_TE = ["{m} | licence {l} | params 1.1B", "{m} released under {l}", "{l} — {m}"]


def gen_licence_open(split, r):
    lic, ok = r.choice(_pool(split, _LIC_TR, _LIC_TE))
    model = r.choice(["org/tiny-model", "acme/coder-1b", "lab/tts-small", "uni/bert-mini", "team/llm-360m",
                      "studio/vision-s", "co/embed-base"] if split != "test" else
                     ["x/voice-0.3b", "y/chat-2b", "z/sum-small", "w/rerank-mini", "v/ocr-base"])
    fmt = r.choice(_pool(split, _LIC_FMT_TR, _LIC_FMT_TE))
    return fmt.format(m=model, l=lic, d=r.choice([120, 4500, 98000])), ok


# ---------------------------------------------------------------- the catalogue
SKILLS = {
    "route_step": dict(part="coordinator: which specialist takes a plan step", labels=list(_R), gen=gen_route_step,
                       instr="Which specialist does this step: researcher, browser, coder or writer?"),
    "pick_source": dict(part="researcher: which search source to query", labels=list(_S), gen=gen_pick_source,
                        instr="Which source answers this best: huggingface, arxiv, pypi, wikipedia, hn or web?"),
    "next_move": dict(part="hive loop: what to do after a failed step", labels=list(_N), gen=gen_next_move,
                      instr="After this failure: retry, reroute or give_up?"),
    "split_orders": dict(part="coordinator: the instruction checklist", gen=gen_split_orders, score=score_lines,
                         max_new=90, instr="Split the order into its separate instructions, one per line, same words."),
    "json_repair": dict(part="engine: repair a member's broken JSON", gen=gen_json_repair, score=score_json, max_new=80,
                        instr="Rewrite as valid JSON. Same keys and values."),
    "family_topic": dict(part="guard: does a step touch family/relationships", labels=["yes", "no"], gen=gen_family_topic,
                         instr="Is this about the user's family, partner or relationships? yes or no"),
    "claim_support": dict(part="verifier: does a quote support a claim", labels=["SUPPORTED", "UNSUPPORTED"],
                          gen=gen_claim_support, instr="Does the QUOTE state exactly what the CLAIM says?"),
    "quote_pick": dict(part="researcher: which sentence is the evidence", labels=["1", "2", "3", "4", "5", "6", "none"],
                       gen=gen_quote_pick, instr="Which sentence number states the claim exactly? Or none."),
    "pick_element": dict(part="browser: which element to act on", gen=gen_pick_element, max_new=4,
                         instr="Which element id reaches the goal?"),
    "element_match": dict(part="browser: does this one element reach the goal (pick_element's organizer asks it per element)",
                          labels=["yes", "no"], gen=gen_element_match,
                          instr="Does clicking this ELEMENT reach the GOAL? yes or no"),
    "licence_open": dict(part="verifier: is a licence open for any use", labels=["yes", "no"], gen=gen_licence_open,
                         instr="Is this licence permissive (free for any use, including commercial)? yes or no", new=True),
}
for _k, _v in {"spend": "buy, pay, book, order, rent, subscribe, donate", "delete": "delete, remove, erase, cancel, unsubscribe",
               "send": "send, email, message, post, reply, share, upload", "login": "log in, sign in",
               "signup": "sign up, register, create an account"}.items():
    SKILLS[f"orders_{_k}"] = dict(part=f"guard: is a '{_k}' action ORDERED", labels=["yes", "no"], gen=_orders_gen(_k),
                                  instr=f"Does the user ORDER the team to {_v}? Nouns, questions and negations are not orders. yes or no")


SKILLS["orders_any"] = dict(part="guard: is ANY risky action ordered (new skill made by the factory)", labels=["yes", "no"],
                           gen=gen_orders_any, new=True,
                           instr="Does the user ORDER the team to buy, pay, delete, send, post, log in or sign up? "
                                 "Nouns, questions and negations are not orders. yes or no")


def examples(skill, split, n, seed=0):
    """n labelled (input, target) pairs; distinct inputs where the pool allows."""
    s = SKILLS[skill]
    r = random.Random(f"{skill}:{split}:{seed}")
    out, seen, per = [], set(), {}
    cap = -(-n // len(s["labels"])) if "labels" in s else n  # balanced labels: no class can crowd out the rest
    for _ in range(n * 40):
        x, y = s["gen"](split, r)
        if x in seen or per.get(y, 0) >= cap:
            continue
        seen.add(x)
        per[y] = per.get(y, 0) + 1
        out.append((x, y))
        if len(out) == n:
            break
    if split != "test":  # never train or select on an input that is also a test input
        test = {x for x, _ in examples(skill, "test", 400, seed)} if split == "train" else set()
        out = [(x, y) for x, y in out if x not in test]
    return out


def score(skill, pred, target):
    s = SKILLS[skill]
    if "score" in s:
        return s["score"](pred, target)
    return float(pred.strip().strip(".").lower() == target.lower())


# ---------------------------------------------------------------- gate: the router over all cells (mixture of experts)
GROUPS = {  # the gate routes by the kind of input; the group's organizer runs every cell that reads that kind
    "order": ["split_orders", "orders_spend", "orders_delete", "orders_send", "orders_login", "orders_signup",
              "orders_any", "family_topic"],
    "step": ["route_step", "pick_source", "family_topic"],
    "failure": ["next_move"], "claim": ["claim_support"], "sentences": ["quote_pick"], "page": ["pick_element", "element_match"],
    "json": ["json_repair"], "licence": ["licence_open"],
}


def group(skill):
    """The gate label a cell's inputs train (a cell in two groups trains the first one that lists it last)."""
    if skill == "family_topic":
        return "step"
    return next((g for g, members in GROUPS.items() if skill in members), skill)


def gate_labels():
    from pathlib import Path
    p = Path(__file__).resolve().parent.parent.parent / "cells" / "registry.json"
    reg = json.loads(p.read_text()) if p.exists() else {}
    names = [k for k in reg if k != "gate"] or [k for k, v in SKILLS.items() if not v.get("new") and k != "gate"]
    return sorted({group(k) for k in names})


_GATE_CACHE = {}


def gen_gate(split, r):
    labels = SKILLS["gate"]["labels"]
    g = r.choice(labels)
    member = r.choice([k for k in SKILLS if group(k) == g and k != "gate"])
    key = (member, split)
    if key not in _GATE_CACHE:
        _GATE_CACHE[key] = examples(member, split, 150 if split == "train" else 40, seed=5)
    x, _ = r.choice(_GATE_CACHE[key])
    return x, g


SKILLS["gate"] = dict(part="the router: which cell (or group of cells) handles an input", labels=gate_labels(),
                      gen=gen_gate, instr="Which cell handles this input?")

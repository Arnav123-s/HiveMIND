"""Builds researcher, verifier and writer training data from LIVE sources.
Queries and topics are disjoint from the eval set (training/evals)."""
import json
import random
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from team.specialists import researcher, verifier, writer  # noqa: E402
from team.tools import web  # noqa: E402

random.seed(7)
DATA = ROOT / "training" / "data"
DATA.mkdir(parents=True, exist_ok=True)


def dump(name, rows):
    with open(DATA / f"{name}.jsonl", "w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"{name}: {len(rows)}")


def j(o):
    return json.dumps(o, ensure_ascii=False)


# ------------------------------------------------------------ researcher: plan
PLAN = [
    ("Find small open chat models under 3B parameters with permissive licenses", [("huggingface", "instruct 1B")]),
    ("Which Phi models exist on Hugging Face and how large are they?", [("huggingface", "Phi-3")]),
    ("Find the most downloaded Llama 3.2 models", [("huggingface", "Llama-3.2")]),
    ("List GGUF quantized versions of Qwen2.5 models", [("huggingface", "Qwen2.5 GGUF")]),
    ("What is the latest version of pandas?", [("pypi", "pandas")]),
    ("Which Python versions does the newest Django support?", [("pypi", "django")]),
    ("Get the latest release of the httpx package", [("pypi", "httpx")]),
    ("Find papers about LoRA fine-tuning efficiency", [("arxiv", "LoRA low-rank adaptation")]),
    ("Find research on small language model distillation", [("arxiv", "small language model distillation")]),
    ("Find papers on state space models like Mamba", [("arxiv", "Mamba state space model")]),
    ("What do Hacker News users think about SQLite in production?", [("hn", "SQLite production")]),
    ("Find Hacker News discussions about local LLMs on a laptop", [("hn", "local LLM laptop")]),
    ("Find popular Hacker News stories about Postgres performance", [("hn", "Postgres performance")]),
    ("Explain the history of the Unix operating system", [("wikipedia", "Unix history")]),
    ("Who invented the World Wide Web and when?", [("wikipedia", "World Wide Web")]),
    ("What is a transformer in machine learning?", [("wikipedia", "Transformer deep learning architecture")]),
    ("Read https://quotes.toscrape.com/tag/life/ and list the quotes", [], ["https://quotes.toscrape.com/tag/life/"]),
    ("Read https://huggingface.co/api/models/Qwen/Qwen3-1.7B and report its license", [],
     ["https://huggingface.co/api/models/Qwen/Qwen3-1.7B"]),
    ("Get the current weather API response from https://api.open-meteo.com/v1/forecast?latitude=19.07&longitude=72.88&current=temperature_2m",
     [], ["https://api.open-meteo.com/v1/forecast?latitude=19.07&longitude=72.88&current=temperature_2m"]),
    ("Compare the licenses of SmolLM3 and Qwen3 small models", [("huggingface", "SmolLM3"), ("huggingface", "Qwen3")]),
    ("What are the latest versions of numpy and scipy?", [("pypi", "numpy"), ("pypi", "scipy")]),
    ("Find both research papers and developer discussion about speculative decoding",
     [("arxiv", "speculative decoding"), ("hn", "speculative decoding")]),
    ("Find information about the Rust programming language's ownership model", [("wikipedia", "Rust programming language")]),
    ("Find the most popular text-to-speech models that run on CPU", [("huggingface", "tts")]),
    ("Find Hacker News stories about Python 3.13 free-threading", [("hn", "Python free-threading")]),
    ("What is the parameter count of Gemma 3 1B?", [("huggingface", "gemma-3-1b")]),
    ("Find embedding models for semantic search", [("huggingface", "sentence embedding")]),
    ("Find recent papers about AI agents using web browsers", [("arxiv", "web browsing agent")]),
]


def researcher_plan_rows():
    rows = []
    for item in PLAN:
        task, searches = item[0], item[1]
        urls = item[2] if len(item) > 2 else []
        out = {"searches": [{"source": s, "q": q} for s, q in searches], "urls": urls}
        rows.append({"messages": researcher.plan_messages(task, ""), "output": j(out)})
    return rows


# ------------------------------------------------------------ researcher: extract
def rows_text(rows):
    return "\n".join(f"- {r['title']} | {r['url']} | {r['snippet']}" for r in rows)


def researcher_extract_rows(cache):
    out = []
    # Hugging Face: filter by params and list with licenses
    for q, limit_b in [("Qwen2.5", 2), ("Phi-3", 5), ("Llama-3.2", 2), ("SmolLM3", 4), ("TinyLlama", 2),
                       ("gemma-3", 2), ("Qwen2.5-Coder", 4), ("granite", 3), ("Falcon3", 4)]:
        try:
            res = web.search_huggingface(q, limit=8)
        except Exception as e:  # noqa: BLE001
            print("skip", q, e)
            continue
        cache[f"hf:{q}"] = res
        if not res:
            continue
        url = res[0]["source_url"]
        sel = [r for r in res if r["data"]["params_b"] and r["data"]["params_b"] < limit_b][:5]
        task = f"List the {q} models under {limit_b}B parameters with their licenses."
        facts = [{"claim": f"{r['data']['id']} has {r['data']['params_b']}B parameters and license {r['data']['license']}",
                  "quote": r["snippet"].split(" | gated")[0], "url": url} for r in sel]
        if sel:
            summary = (f"{len(sel)} {q} models are under {limit_b}B parameters: " +
                       ", ".join(f"{r['data']['id']} ({r['data']['params_b']}B, {r['data']['license']})" for r in sel) + ".")
        else:
            summary = f"None of the {q} models listed in the source is under {limit_b}B parameters."
        data = {"summary": summary, "items": [r["data"]["id"] for r in sel], "facts": facts}
        src = f"### Source: {url}\n{rows_text(res)}"
        out.append({"messages": researcher.extract_messages(task, src), "output": j(data)})
        # second task on same source: most downloaded
        top = max(res, key=lambda r: r["data"]["downloads"] or 0)
        task2 = f"Which {q} model has the most downloads?"
        data2 = {"summary": f"{top['data']['id']} has the most downloads ({top['data']['downloads']}).",
                 "items": [top["data"]["id"]],
                 "facts": [{"claim": f"{top['data']['id']} has {top['data']['downloads']} downloads",
                            "quote": f"{top['data']['id']} | params", "url": url}]}
        data2["facts"][0]["quote"] = top["snippet"].split(" | likes")[0]  # exact substring of the source
        out.append({"messages": researcher.extract_messages(task2, src), "output": j(data2)})
    # PyPI
    for pkg in ["pandas", "django", "httpx", "numpy", "scipy", "fastapi", "pydantic", "uvicorn", "rich", "polars"]:
        try:
            res = web.search_pypi(pkg)
        except Exception as e:  # noqa: BLE001
            print("skip", pkg, e)
            continue
        cache[f"pypi:{pkg}"] = res
        url = f"https://pypi.org/pypi/{pkg}/json"
        sn = res[0]["snippet"]
        ver = re.search(r"latest (\S+)", sn).group(1)
        req = re.search(r"requires-python (.+)$", sn)
        task = f"What is the latest version of {pkg} and which Python versions does it need?"
        facts = [{"claim": f"The latest version of {res[0]['title']} is {ver}", "quote": f"latest {ver}", "url": url}]
        if req and req.group(1) != "None":
            facts.append({"claim": f"{res[0]['title']} requires Python {req.group(1)}", "quote": f"requires-python {req.group(1)}", "url": url})
        summary = f"The latest {res[0]['title']} is {ver}" + (f"; it requires Python {req.group(1)}." if req and req.group(1) != "None" else ".")
        out.append({"messages": researcher.extract_messages(task, f"### Source: {url}\n{rows_text(res)}"),
                    "output": j({"summary": summary, "items": [], "facts": facts})})
    # HN
    for q in ["SQLite production", "local LLM laptop", "Postgres performance", "Python packaging", "WebAssembly"]:
        try:
            res = web.search_hn(q, limit=6)
        except Exception as e:  # noqa: BLE001
            print("skip", q, e)
            continue
        cache[f"hn:{q}"] = res
        key = f"search:hn:{q}"
        res = [r for r in res if r["title"]]
        top = sorted(res, key=lambda r: -int(re.match(r"(\d+)", r["snippet"]).group(1) if re.match(r"(\d+)", r["snippet"]) else 0))[:3]
        task = f"List the most discussed Hacker News stories about {q} with their points."
        facts = [{"claim": f"'{r['title']}' got {r['snippet'].split(',')[0]}", "quote": f"{r['title']} | {r['url']} | {r['snippet']}", "url": key}
                 for r in top]
        data = {"summary": "The most discussed stories are " + "; ".join(f"'{r['title']}' ({r['snippet'].split(',')[0]})" for r in top) + ".",
                "items": [r["title"] for r in top], "facts": facts}
        out.append({"messages": researcher.extract_messages(task, f"### Source: {key}\n{rows_text(res)}"), "output": j(data)})
    # arXiv
    for q in ["LoRA low-rank adaptation", "Mamba state space model", "web browsing agent", "small language model distillation"]:
        try:
            res = web.search_arxiv(q, limit=4)
        except Exception as e:  # noqa: BLE001
            print("skip", q, e)
            continue
        cache[f"arxiv:{q}"] = res
        key = f"search:arxiv:{q}"
        task = f"Find papers about {q} and give me their titles and links."
        facts = [{"claim": f"The paper '{r['title']}' is at {r['url']}", "quote": f"{r['title']} | {r['url']}", "url": key} for r in res[:3]]
        data = {"summary": f"Found {len(res[:3])} papers on {q}: " + "; ".join(r["title"] for r in res[:3]) + ".",
                "items": [r["url"] for r in res[:3]], "facts": facts}
        out.append({"messages": researcher.extract_messages(task, f"### Source: {key}\n{rows_text(res)}"), "output": j(data)})
    # Pages: quotes by tag
    for tag in ["life", "humor", "books", "friendship", "inspirational"]:
        u = f"https://quotes.toscrape.com/tag/{tag}/"
        try:
            page = web.read_url(u, max_chars=4000)
        except Exception as e:  # noqa: BLE001
            print("skip", u, e)
            continue
        cache[f"page:{u}"] = page
        lines = page["text"].split("\n")
        pairs = []
        for i, ln in enumerate(lines):
            if ln.startswith("“") and i + 2 < len(lines) and lines[i + 1] == "by":
                pairs.append((ln, lines[i + 2]))
        authors = list(dict.fromkeys(a for _, a in pairs))
        task = f"Which authors are quoted on the '{tag}' tag page?"
        facts = [{"claim": f"{a} is quoted on the {tag} page", "quote": a, "url": u} for a in authors[:4]]
        facts += [{"claim": f"{pairs[0][1]} wrote: {pairs[0][0][:80]}", "quote": pairs[0][0], "url": u}] if pairs else []
        data = {"summary": f"The {tag} page quotes {', '.join(authors)}.", "items": authors, "facts": facts}
        out.append({"messages": researcher.extract_messages(task, f"### Source: {u}\nTitle: {page['title']}\n{page['text'][:2500]}"),
                    "output": j(data)})
    # Unanswerable: the sources do not answer the question
    res = cache.get("pypi:numpy")
    if res:
        out.append({"messages": researcher.extract_messages("Who is the current maintainer of numpy and where do they live?",
                                                            f"### Source: https://pypi.org/pypi/numpy/json\n{rows_text(res)}"),
                    "output": j({"summary": "The sources do not say who maintains numpy or where they live; they only give the latest version.",
                                 "items": [], "facts": []})})
    return out


# ------------------------------------------------------------ verifier
def perturb_number(s):
    m = list(re.finditer(r"\d+(\.\d+)?", s))
    if not m:
        return None
    k = random.choice(m)
    v = k.group(0)
    if "." in v:
        new = f"{float(v) * random.choice([1.7, 0.4, 2.5]):.{len(v.split('.')[1])}f}"
    else:
        new = str(int(v) + random.choice([1, 3, 10, -1]) if int(v) > 1 else int(v) + 2)
    return s[:k.start()] + new + s[k.end():] if new != v else None


def verifier_rows(cache):
    from team.specialists.verifier import fact_messages, judge_messages
    rows = []

    def fact(claim, quote, label, reason):
        rows.append({"messages": fact_messages(claim, quote), "output": j({"verdict": label, "reason": reason})})

    def judge(check, work, ev, label, reason):
        rows.append({"messages": judge_messages(check, work, ev), "output": j({"verdict": label, "reason": reason})})

    for k, res in cache.items():
        if k.startswith("hf:"):
            for r in res[:4]:
                d, q = r["data"], r["snippet"].split(" | gated")[0]
                if d["params_b"]:
                    fact(f"{d['id']} has {d['params_b']}B parameters", q, "SUPPORTED", f"The quote lists params {d['params_b']}B.")
                    wrong = round(d["params_b"] * random.choice([2, 3, 0.5]), 3)
                    fact(f"{d['id']} has {wrong}B parameters", q, "UNSUPPORTED", f"The quote says {d['params_b']}B, not {wrong}B.")
                lic = d["license"]
                fact(f"{d['id']} is released under the {lic} license", q, "SUPPORTED", f"The quote lists license {lic}.")
                other = random.choice([x for x in ["mit", "apache-2.0", "llama3.2", "gemma", "cc-by-nc-4.0", "other"] if x != lic])
                fact(f"{d['id']} uses the {other} license", q, "UNSUPPORTED", f"The quote lists license {lic}, not {other}.")
        if k.startswith("pypi:"):
            sn = res[0]["snippet"]
            ver = re.search(r"latest (\S+)", sn).group(1)
            fact(f"The latest version of {res[0]['title']} is {ver}", sn, "SUPPORTED", f"The quote says latest {ver}.")
            bad = perturb_number(ver)
            if bad:
                fact(f"The latest version of {res[0]['title']} is {bad}", sn, "UNSUPPORTED", f"The quote says latest {ver}, not {bad}.")
        if k.startswith("hn:"):
            for r in res[:2]:
                if not r["title"]:
                    continue
                q = f"{r['title']} | {r['url']} | {r['snippet']}"
                pts = r["snippet"].split(",")[0]
                fact(f"'{r['title']}' got {pts}", q, "SUPPORTED", f"The quote shows {pts}.")
                bad = perturb_number(pts)
                if bad:
                    fact(f"'{r['title']}' got {bad}", q, "UNSUPPORTED", f"The quote shows {pts}, not {bad}.")
                yr = r["snippet"][-10:-6]
                if yr.isdigit():
                    fact(f"'{r['title']}' was posted in {int(yr) - 3}", q, "UNSUPPORTED", f"The quote dates it {yr}.")
        if k.startswith("page:"):
            txt = res["text"]
            ls = txt.split("\n")
            for i, ln in enumerate(ls):
                if ln.startswith("“") and i + 2 < len(ls) and ls[i + 1] == "by":
                    a = ls[i + 2]
                    fact(f"{a} said {ln[:60]}...", f"{ln}\nby\n{a}", "SUPPORTED", f"The quote is attributed to {a}.")
                    fact(f"Mark Twain said {ln[:60]}...", f"{ln}\nby\n{a}", "UNSUPPORTED" if a != "Mark Twain" else "SUPPORTED",
                         f"The quote is attributed to {a}.")
                    break
    # claim says more than the quote (scope)
    fact("Qwen/Qwen2.5-0.5B-Instruct is the fastest model on CPU", "Qwen/Qwen2.5-0.5B-Instruct | params 0.494B | license apache-2.0",
         "UNSUPPORTED", "The quote gives size and license, nothing about speed.")
    fact("The book is the cheapest in its category", "Tipping the Velvet £53.74 In stock (20 available)", "UNSUPPORTED",
         "The quote gives one price; it says nothing about the category.")
    fact("Tipping the Velvet costs £53.74", "Tipping the Velvet £53.74 In stock (20 available)", "SUPPORTED", "The quote shows £53.74.")
    fact("Tipping the Velvet has 20 copies in stock", "Tipping the Velvet £53.74 In stock (20 available)", "SUPPORTED", "The quote says 20 available.")
    fact("Tipping the Velvet costs £35.74", "Tipping the Velvet £53.74 In stock (20 available)", "UNSUPPORTED", "The quote says £53.74.")

    # judge: step results vs checks
    J = [
        ("prices.csv has 3 rows of book prices", "Program ran (exit 0). Files: ['prices.csv']",
         "title,price\nSoumission,50.10\nSharp Objects,47.82\nTipping the Velvet,53.74\nSaved 3 rows", "PASS", "Three priced rows were saved."),
        ("prices.csv has 3 rows of book prices", "Program ran (exit 0). Files: ['prices.csv']",
         "title,price\nSaved 0 rows", "FAIL", "The file has no data rows."),
        ("the script prints the mean seconds for both methods", "Program ran (exit 0). Files: []",
         "sort: 0.412 s\nsorted: 0.455 s", "PASS", "Both timings are printed."),
        ("the script prints the mean seconds for both methods", "Program ran (exit 0). Files: []",
         "sort: 0.412 s", "FAIL", "Only one of the two timings is printed."),
        ("5 model ids with params and license", "Found 5 models.",
         "- a/b (0.5B, apache-2.0)\n- c/d (1.1B, mit)\n- e/f (0.36B, apache-2.0)\n- g/h (1.5B, apache-2.0)\n- i/j (0.13B, apache-2.0)",
         "PASS", "Five models with params and licenses are evidenced."),
        ("5 model ids with params and license", "Found 5 models.", "- a/b (0.5B)\n- c/d (1.1B)", "FAIL",
         "Only two models, and no licenses, are evidenced."),
        ("hn_top10.json has 10 entries", "Program ran (exit 0). Files: ['hn_top10.json']", "Saved 10 stories to hn_top10.json",
         "PASS", "The program reports 10 saved stories."),
        ("hn_top10.json has 10 entries", "Program ran (exit 0). Files: []", "Error: timed out\nSaved 0 stories", "FAIL",
         "No file and zero stories."),
        ("the license text is visible on the page", "The license is apache-2.0",
         "Page https://huggingface.co/Qwen/Qwen2.5-0.5B: License: apache-2.0", "PASS", "The page shows the license."),
        ("the license text is visible on the page", "The license is MIT",
         "Page https://huggingface.co/Qwen/Qwen2.5-0.5B: License: apache-2.0", "FAIL", "The page shows apache-2.0, not MIT."),
        ("price and stock count visible on the book page", "Soumission costs £50.10 with 20 in stock",
         "Page https://books.toscrape.com/catalogue/soumission_998/index.html: £50.10 In stock (20 available)", "PASS",
         "Price and stock match the page."),
        ("price and stock count visible on the book page", "Soumission costs £50.10",
         "Page https://books.toscrape.com/: All products", "FAIL", "The evidence is the home page, not the book page."),
        ("3 papers with titles and arXiv links", "Three papers found",
         "- LoRA: Low-Rank Adaptation (arxiv.org/abs/2106.09685)\n- QLoRA (arxiv.org/abs/2305.14314)\n- DoRA (arxiv.org/abs/2402.09353)",
         "PASS", "Three titled papers with links."),
        ("3 papers with titles and arXiv links", "Three papers found", "Here are some papers I remember about LoRA.", "FAIL",
         "No titles or links are evidenced."),
        ("temperature.png exists and min and max are printed", "Program ran (exit 0). Files: ['temperature.png']",
         "min 21.3 C, max 29.8 C\nsaved temperature.png", "PASS", "Chart saved and both values printed."),
        ("temperature.png exists and min and max are printed", "Program ran (exit 0). Files: ['temperature.png']",
         "saved temperature.png", "FAIL", "Min and max were not printed."),
        ("requirements.txt exists with 3 pinned lines", "Program ran (exit 0). Files: ['requirements.txt']",
         "fastapi==0.121.0\nuvicorn==0.38.0\npydantic==2.12.4", "PASS", "Three pinned lines."),
        ("requirements.txt exists with 3 pinned lines", "Program ran (exit 0). Files: ['requirements.txt']",
         "fastapi\nuvicorn\npydantic", "FAIL", "The lines are not pinned to versions."),
        ("a list of Rust stories with points", "Stories about Go found",
         "- Go 1.22 released (500 points)", "FAIL", "The evidence is about Go, not Rust."),
        ("the program prints all tests passed", "Program ran (exit 0). Files: []", "all tests passed", "PASS", "The tests passed."),
        ("the program prints all tests passed", "Program ran (exit 0). Files: []", "", "FAIL", "Nothing was printed."),
        ("population and area visible on the page", "Population 12,442,373; area 603.4 km2",
         "Page https://en.wikipedia.org/wiki/Mumbai: Population (2011) 12,442,373 ... Area 603.4 km2", "PASS",
         "Both numbers appear on the page."),
    ]
    for check, work, ev, label, reason in J:
        judge(check, work, ev, label, reason)
    random.shuffle(rows)
    return rows


# ------------------------------------------------------------ writer
def writer_rows(cache):
    rows = []
    hf = [(k, v) for k, v in cache.items() if k.startswith("hf:") and v]
    for k, res in hf[:5]:
        q = k[3:]
        url = res[0]["source_url"]
        sel = res[:4]
        results = (f"## s1 (researcher, verdict=PASS): list {q} models\nResult: Found {len(sel)} models.\n"
                   + "".join(f"- {r['data']['id']} has {r['data']['params_b']}B parameters and license {r['data']['license']} [{url}]\n" for r in sel))
        smallest = min((r for r in sel if r["data"]["params_b"]), key=lambda r: r["data"]["params_b"], default=sel[0])
        md = (f"**{smallest['data']['id']}** is the smallest {q} model listed ({smallest['data']['params_b']}B parameters, "
              f"{smallest['data']['license']}) [1].\n\n| model | params | license |\n|---|---|---|\n"
              + "".join(f"| {r['data']['id']} | {r['data']['params_b']}B | {r['data']['license']} |\n" for r in sel)
              + "\nAll figures are from the Hugging Face model index [1].")
        rows.append({"messages": writer.messages(f"Which {q} models exist and how big are they?", "Write the answer for Arnav.",
                                                 results, [url]), "output": md})
    pyp = [(k, v) for k, v in cache.items() if k.startswith("pypi:")]
    for (k1, r1), (k2, r2) in zip(pyp[0::2], pyp[1::2]):
        u1, u2 = f"https://pypi.org/pypi/{k1[5:]}/json", f"https://pypi.org/pypi/{k2[5:]}/json"
        v1, v2 = re.search(r"latest (\S+)", r1[0]["snippet"]).group(1), re.search(r"latest (\S+)", r2[0]["snippet"]).group(1)
        results = (f"## s1 (researcher, verdict=PASS): {k1[5:]} version\nResult: latest {v1}\n- The latest version of {k1[5:]} is {v1} [{u1}]\n"
                   f"## s2 (researcher, verdict=FAIL): {k2[5:]} release date\n## s3 (researcher, verdict=PASS): {k2[5:]} version\n"
                   f"Result: latest {v2}\n- The latest version of {k2[5:]} is {v2} [{u2}]\n")
        md = (f"Latest versions: **{k1[5:]} {v1}** [1] and **{k2[5:]} {v2}** [2].\n\n"
              f"Pin them as `{k1[5:]}=={v1}` and `{k2[5:]}=={v2}`.\n\n## Not confirmed\n- The release date of {k2[5:]}: that step failed verification.")
        rows.append({"messages": writer.messages(f"What are the latest versions of {k1[5:]} and {k2[5:]}, and when was {k2[5:]} released?",
                                                 "Write the answer.", results, [u1, u2]), "output": md})
    for k, res in [(k, v) for k, v in cache.items() if k.startswith("hn:")][:3]:
        key = f"search:hn:{k[3:]}"
        res = [r for r in res if r["title"]][:3]
        results = (f"## s1 (researcher, verdict=PASS): HN stories on {k[3:]}\nItems: {json.dumps([r['title'] for r in res])}\n"
                   + "".join(f"- '{r['title']}' got {r['snippet'].split(',')[0]} [{r['url']}]\n" for r in res))
        srcs = [r["url"] for r in res]
        md = (f"The most discussed Hacker News stories on {k[3:]}:\n\n"
              + "".join(f"{i + 1}. **{r['title']}** - {r['snippet'].split(',')[0]} [{i + 1}]\n" for i, r in enumerate(res))
              + "\nThese are ranked by points; I did not read the comment threads.")
        rows.append({"messages": writer.messages(f"Summarize Hacker News discussion about {k[3:]}.", "Write the summary.",
                                                 results, srcs), "output": md})
    return rows


if __name__ == "__main__":
    cache = {}
    dump("researcher_plan", researcher_plan_rows())
    dump("researcher_extract", researcher_extract_rows(cache))
    dump("verifier", verifier_rows(cache))
    dump("writer", writer_rows(cache))
    (ROOT / "training" / "data" / "_live_cache.json").write_text(json.dumps(cache, ensure_ascii=False, indent=0)[:5_000_000])

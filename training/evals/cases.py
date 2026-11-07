"""Held-out eval cases for coordinator, researcher, verifier, coder, writer.
None of these tasks appear in the training data."""
import json
from pathlib import Path

FROZEN = json.loads((Path(__file__).parent / "frozen" / "sources.json").read_text())

# need: groups of agents; each group must have at least one agent in the plan
COORDINATOR = [
    {"task": "Find the three most downloaded text-generation models under 1B parameters on Hugging Face and tell me their licenses.",
     "need": [["researcher"]]},
    {"task": "Go to books.toscrape.com, open the Travel category, and list every book title with its price.",
     "need": [["browser"]]},
    {"task": "Write a Python script that gets the Open-Meteo forecast for Pune for the next 3 days, saves it as a CSV, and tells me which day is coolest.",
     "need": [["coder"]]},
    {"task": "Check which of these packages have a newer version on PyPI than what I pinned: requests==2.31.0, numpy==1.26.0, flask==2.3.0.",
     "need": [["researcher", "coder"]]},
    {"task": "Find the top 5 Hacker News stories about Rust and summarize what each one is about.",
     "need": [["researcher"]]},
    {"task": "Look up arXiv papers on speculative decoding, pick the 3 most relevant, and build me a reading list with one-line summaries.",
     "need": [["researcher"]]},
    {"task": "Benchmark how fast Python's json module parses a 50 MB file on this machine versus a 5 MB file and explain the scaling.",
     "need": [["coder"]]},
    {"task": "On quotes.toscrape.com, collect every quote by Albert Einstein across all pages and save them to a file.",
     "need": [["browser", "coder"]]},
    {"task": "For each of the 3 most downloaded Qwen models on Hugging Face, open its model page and record the license and the weights file size.",
     "need": [["researcher"], ["browser"]], "for_each": True},
    {"task": "Find known vulnerabilities for the Python package jinja2 version 2.10 using OSV and tell me if I should upgrade.",
     "need": [["researcher", "coder"]]},
    {"task": "Make a chart of the last 30 days of daily maximum temperature in Mumbai from Open-Meteo and save it as a PNG.",
     "need": [["coder"]]},
    {"task": "Read the Wikipedia article on the transistor and write me a one-page history with key dates.",
     "need": [["researcher", "browser"]]},
    {"task": "Find the latest version of the Python packages fastapi and pydantic, then write and run a script that checks if my installed versions are older.",
     "need": [["researcher", "coder"], ["coder"]]},
    {"task": "Open the Hugging Face page of SmolLM2-360M-Instruct, read the model card, and tell me what it was trained on.",
     "need": [["browser", "researcher"]]},
]

HF = FROZEN["hf_small_textgen"]
HF_SM = FROZEN["hf_smollm"]

RESEARCHER_PLAN = [
    {"task": "Find small open text-generation models under 1B parameters", "sources": ["huggingface"]},
    {"task": "What is the latest version of the flask package?", "sources": ["pypi"]},
    {"task": "Find recent research papers about mixture of experts routing", "sources": ["arxiv"]},
    {"task": "What are developers saying on Hacker News about the Zig language?", "sources": ["hn"]},
    {"task": "Get the history of the Linux kernel from an encyclopedia", "sources": ["wikipedia", "url"]},
    {"task": "Read https://quotes.toscrape.com/tag/humor/ and list the authors", "sources": ["url"], "url": True},
    {"task": "Which SmolLM2 models exist and what are their licenses?", "sources": ["huggingface"]},
    {"task": "Find the most popular papers on retrieval augmented generation", "sources": ["arxiv"]},
    {"task": "Get the release information for the numpy package", "sources": ["pypi"]},
    {"task": "Find the license and parameter count of Qwen2.5 coder models", "sources": ["huggingface"]},
]


def _block(url, rows):
    return f"### Source: {url}\n" + "\n".join(f"- {r['title']} | {r['url']} | {r['snippet']}" for r in rows)


RESEARCHER_EXTRACT = [
    {"task": "List the Qwen3 text-generation models under 2B parameters with their licenses.",
     "sources": _block(HF[0]["source_url"], HF), "corpus": {HF[0]["source_url"]: "\n".join(
         f"- {r['title']} | {r['url']} | {r['snippet']}" for r in HF)},
     "items": [r["data"]["id"] for r in HF if r["data"]["params_b"] and r["data"]["params_b"] < 2]},
    {"task": "Which SmolLM2 models are instruction-tuned (Instruct) and how many parameters do they have?",
     "sources": _block(HF_SM[0]["source_url"], HF_SM), "corpus": {HF_SM[0]["source_url"]: "\n".join(
         f"- {r['title']} | {r['url']} | {r['snippet']}" for r in HF_SM)},
     "items": [r["data"]["id"] for r in HF_SM if "Instruct" in r["data"]["id"]]},
    {"task": "What is the latest version of requests and which Python versions does it need?",
     "sources": _block("https://pypi.org/pypi/requests/json", FROZEN["pypi_requests"]),
     "corpus": {"https://pypi.org/pypi/requests/json": "\n".join(f"- {r['title']} | {r['url']} | {r['snippet']}" for r in FROZEN["pypi_requests"])},
     "items": [], "must_mention": ["2.34.2"]},
    {"task": "List the Hacker News stories about the Rust compiler with their points.",
     "sources": _block("search:hn:rust compiler", FROZEN["hn_rust"]),
     "corpus": {"search:hn:rust compiler": "\n".join(f"- {r['title']} | {r['url']} | {r['snippet']}" for r in FROZEN["hn_rust"])},
     "items": [r["title"] for r in FROZEN["hn_rust"]][:3]},
    {"task": "Which authors are quoted on the 'love' tag page?",
     "sources": f"### Source: https://quotes.toscrape.com/tag/love/\n{FROZEN['quotes_love_page']['text'][:2500]}",
     "corpus": {"https://quotes.toscrape.com/tag/love/": FROZEN["quotes_love_page"]["text"]},
     "items": ["André Gide", "Elie Wiesel"]},
]

VERIFIER = [
    # (kind, label, payload)
    ("fact", "SUPPORTED", {"claim": "Qwen/Qwen3-0.6B is licensed under Apache 2.0",
                           "quote": "Qwen/Qwen3-0.6B | params 0.752B | license apache-2.0 | pipeline text-generation"}),
    ("fact", "UNSUPPORTED", {"claim": "Qwen/Qwen3-0.6B has 1.7 billion parameters",
                             "quote": "Qwen/Qwen3-0.6B | params 0.752B | license apache-2.0 | pipeline text-generation"}),
    ("fact", "SUPPORTED", {"claim": "The latest version of requests is 2.34.2",
                           "quote": "latest 2.34.2 | Python HTTP for Humans. | requires-python >=3.10"}),
    ("fact", "UNSUPPORTED", {"claim": "requests supports Python 3.8",
                             "quote": "latest 2.34.2 | Python HTTP for Humans. | requires-python >=3.10"}),
    ("fact", "SUPPORTED", {"claim": "'A Light in the Attic' costs £51.77", "quote": "A Light in the Attic £51.77 In stock (22 available)"}),
    ("fact", "UNSUPPORTED", {"claim": "'A Light in the Attic' is out of stock", "quote": "A Light in the Attic £51.77 In stock (22 available)"}),
    ("fact", "UNSUPPORTED", {"claim": "SmolLM2-135M is released under the MIT license",
                             "quote": "HuggingFaceTB/SmolLM2-135M | params 0.135B | license apache-2.0"}),
    ("fact", "SUPPORTED", {"claim": "The story 'Writing a Rust compiler in C' got 393 points",
                           "quote": "Writing a Rust compiler in C | https://notgull.net/announcing-dozer/ | 393 points, 223 comments, 2024-08-25"}),
    ("fact", "UNSUPPORTED", {"claim": "The story 'Writing a Rust compiler in C' was posted in 2019",
                             "quote": "Writing a Rust compiler in C | https://notgull.net/announcing-dozer/ | 393 points, 223 comments, 2024-08-25"}),
    ("fact", "UNSUPPORTED", {"claim": "Python was first released in 1989",
                             "quote": "Python 0.9.0 was released on 20 February 1991"}),
    ("judge", "PASS", {"check": "results.csv has one row per model with tokens per second",
                       "work": "Program ran (exit 0). Files: ['results.csv']",
                       "evidence": "Benchmarked 3 models.\nQwen/Qwen3-0.6B: 21.4 tok/s\nQwen/Qwen3-1.7B: 9.8 tok/s\nHuggingFaceTB/SmolLM2-360M-Instruct: 35.0 tok/s\nSaved results.csv (3 rows)"}),
    ("judge", "FAIL", {"check": "results.csv has one row per model with tokens per second",
                       "work": "Program ran (exit 0). Files: []",
                       "evidence": "Could not download model: 401 Unauthorized\nSaved 0 rows"}),
    ("judge", "FAIL", {"check": "a list of 5 Hacker News stories with titles and points",
                       "work": "Found 2 stories.",
                       "evidence": "- Writing a Rust compiler in C (393 points)\n- Speeding Up the Rust Compiler (351 points)"}),
    ("judge", "PASS", {"check": "the price of 'Tipping the Velvet' is reported",
                       "work": "The price of Tipping the Velvet is £53.74",
                       "evidence": "Page https://books.toscrape.com/catalogue/tipping-the-velvet_999/index.html: Tipping the Velvet £53.74"}),
    ("judge", "FAIL", {"check": "the license of each of the 3 models is recorded",
                       "work": "Qwen3-0.6B: apache-2.0", "evidence": "License: apache-2.0 (only one model page was opened)"}),
    ("judge", "PASS", {"check": "forecast.csv contains 3 days of max temperatures",
                       "work": "Program ran (exit 0). Files: ['forecast.csv']",
                       "evidence": "date,max_temp\n2026-11-08,31.2\n2026-11-09,30.8\n2026-11-10,29.9\nSaved forecast.csv with 3 rows"}),
    ("judge", "FAIL", {"check": "the script prints the number of primes below 10000",
                       "work": "Program ran (exit 0). Files: []", "evidence": ""}),
    ("judge", "FAIL", {"check": "a reading list of 3 arXiv papers on speculative decoding",
                       "work": "Here are papers about image segmentation: SAM, Mask2Former, U-Net",
                       "evidence": "- Segment Anything (arXiv 2304.02643)"}),
]

CODER = [
    {"task": "Print the number of prime numbers below 10000 in the form 'primes=<n>'.",
     "check": {"stdout_regex": r"primes=1229"}},
    {"task": "Get https://pypi.org/pypi/requests/json and save the latest version to requests_version.txt (just the version string).",
     "check": {"file": "requests_version.txt", "file_regex": r"^\s*\d+\.\d+\.\d+\s*$"}},
    {"task": "Read scores.csv (columns name,score) and write top3.json: a JSON list of the 3 names with the highest scores, highest first.",
     "setup": {"scores.csv": "name,score\nasha,71\nbo,93\ncy,88\ndev,55\neli,90\n"},
     "check": {"file": "top3.json", "json_equals": ["bo", "eli", "cy"]}},
    {"task": "Call https://huggingface.co/api/models?search=SmolLM2&limit=5 and save the model ids, one per line, to models.txt.",
     "check": {"file": "models.txt", "file_regex": r"SmolLM2"}},
    {"task": "Download https://books.toscrape.com/ and save the 20 book titles and prices on that page to books.csv with header title,price.",
     "check": {"file": "books.csv", "csv_rows": 20}},
    {"task": "Get the Open-Meteo daily maximum temperature forecast for latitude 18.52, longitude 73.86 for 3 days "
             "(https://api.open-meteo.com/v1/forecast?latitude=18.52&longitude=73.86&daily=temperature_2m_max&forecast_days=3&timezone=auto) "
             "and save forecast.csv with header date,max_temp.",
     "check": {"file": "forecast.csv", "csv_rows": 3}},
    {"task": "Measure how long it takes to sort one million random integers and print 'seconds=<value>' with 3 decimals.",
     "check": {"stdout_regex": r"seconds=\d+\.\d{3}"}},
    {"task": "Write words.txt containing the 10 most common words (lowercase, one per line, most common first) in text.txt.",
     "setup": {"text.txt": ("the cat and the dog and the bird. " * 5) + "a cat a dog a fish fish fish fish fish fish fish fish"},
     "check": {"file": "words.txt", "first_line": "fish"}},
]

WRITER = [
    {"goal": "Which small model should I use on my laptop?", "task": "Write the recommendation.",
     "results": "## s1 (researcher, verdict=PASS): shortlist\nResult: Qwen/Qwen3-0.6B and HuggingFaceTB/SmolLM2-360M-Instruct are small and Apache-2.0.\n"
                "- Qwen/Qwen3-0.6B has 0.752B params [https://huggingface.co/api/models?search=Qwen3]\n"
                "## s2 (coder, verdict=PASS): benchmark\nResult: Qwen3-0.6B 21.4 tok/s acc 0.70; SmolLM2-360M 35.0 tok/s acc 0.35\n",
     "sources": ["https://huggingface.co/api/models?search=Qwen3"], "must": ["Qwen3-0.6B"]},
    {"goal": "Summarize the top Rust compiler stories on Hacker News.", "task": "Write the summary.",
     "results": "## s1 (researcher, verdict=PASS): stories\nItems: [\"Writing a Rust compiler in C\", \"Speeding Up the Rust Compiler\"]\n"
                "- 'Writing a Rust compiler in C' got 393 points [https://notgull.net/announcing-dozer/]\n",
     "sources": ["https://notgull.net/announcing-dozer/"], "must": ["Writing a Rust compiler in C"]},
    {"goal": "Find the price of three books on books.toscrape.com.", "task": "Report the prices.",
     "results": "## s2[1] (browser, verdict=PASS): price of Tipping the Velvet\nResult: £53.74\n"
                "## s2[2] (browser, verdict=FAIL): price of Soumission\n",
     "sources": ["https://books.toscrape.com/catalogue/tipping-the-velvet_999/index.html"], "must": ["53.74"],
     "must_flag_gap": True},
]

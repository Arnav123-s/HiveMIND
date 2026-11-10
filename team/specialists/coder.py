"""Coder: writes a program, runs it, reads the error, fixes it, until it runs."""
import re
from pathlib import Path

from .. import config, llm, prompts, stop
from ..tools.preview import expected_outputs, preview
from ..tools.sandbox import http_errors, run_python


def task_messages(task, context, data_preview=""):
    user = f"Task: {task}"
    if context:
        user += f"\n\nResults from the team you can use:\n{context}"
    if data_preview:
        user += f"\n\nDATA PREVIEW:\n{data_preview}"
    return [{"role": "system", "content": prompts.CODER}, {"role": "user", "content": user}]


def extract_code(text):
    blocks = re.findall(r"```(?:python|py)?\s*\n(.*?)```", text, re.S)
    if blocks:
        return max(blocks, key=len).strip()
    if "```" in text:  # unterminated block
        return text.split("```", 1)[1].split("\n", 1)[1].strip()
    return text.strip()


def sanity(stdout):
    """Hard checks: a measurement that reads exactly zero means the measuring code is wrong."""
    probs = []
    if re.search(r"\b0\.0+\s*(s|sec|seconds|ms|mb|gb|kb)\b", stdout, re.I):
        probs.append("a time or memory measurement printed as 0.00 - it is measured around the wrong operation")
    if re.search(r"\b0\s*/\s*\d+\b", stdout) and re.search(r"correct|accura", stdout, re.I):
        probs.append("0 answers correct - check how replies are compared (parse the number out of the reply)")
    if re.search(r"Â[£€©®°±·»«]|â€[™œ\x9d”“˜]|Ã[©¨¢¶¼]", stdout):
        probs.append("text was decoded with the wrong character set ('Â£' for '£'): parse response.content, or set "
                     "response.encoding = response.apparent_encoding before response.text")
    return probs


def review(task, code, stdout):
    data, _ = llm.chat_json("code_reviewer", [{"role": "system", "content": prompts.CODE_REVIEWER},
                                              {"role": "user", "content": f"TASK: {task}\n\nCODE:\n{code[:6000]}\n\nOUTPUT:\n{stdout[-1500:]}"}],
                            max_new_tokens=250)
    if not isinstance(data, dict) or data.get("ok", True) is True:
        return []
    return [str(x)[:200] for x in data.get("problems", [])][:5]


ERROR_KINDS = [  # the error reader: a code rule, exact on exception names (a cell would add nothing)
    ("syntax", r"SyntaxError|IndentationError|TabError"),
    ("import", r"ModuleNotFoundError|ImportError"),
    ("not_found", r"\b404 Client Error|HTTP Error 404|404 Not Found|status(?:_code)? (?:was |is |== ?)?404\b"),
    ("network", r"ConnectionError|NameResolution|Max retries exceeded|HTTPError|Timeout(Error)?:|SSLError|"
                r"getaddrinfo|Connection refused|HTTP Error \d{3}"),
    ("file", r"FileNotFoundError|PermissionError|IsADirectoryError|NotADirectoryError"),
    ("timeout", r"TIMEOUT after"),
    ("check", r"AssertionError"),
    ("data", r"KeyError|IndexError|TypeError|ValueError|AttributeError|ZeroDivisionError|JSONDecodeError"),
]


def error_kind(err):
    """The kind of a failure, from the last error in the output (None when it names none of them)."""
    tail = "\n".join((err or "").strip().splitlines()[-6:])
    return next((k for k, rx in ERROR_KINDS if re.search(rx, tail)), None)


EXAMPLE = re.compile(r"\b([A-Za-z_]\w*)\(([^()\n]{0,40})\)\s*(?:==|=|returns|should return|gives|is)\s*"
                     r"(-?\d+(?:\.\d+)?|True|False|None|'[^'\n]{0,40}'|\"[^\"\n]{0,40}\")")


def example_checks(task, code):
    """Checks from the examples in his own task ("fib(1) = 1, fib(2) = 1"), for functions the program defines:
    Python that calls each and says what it returned when it differs."""
    out = []
    for name, args, want in EXAMPLE.findall(task or ""):
        if re.search(rf"^\s*def {re.escape(name)}\s*\(", code or "", re.M):
            call = f"{name}({args})"
            out.append(f"_got = {call}\nassert _got == {want}, f'{call} returned {{_got!r}}, but the task says {call} = {want}'")
    return list(dict.fromkeys(out))


DRAWS = re.compile(r"\b(?:plt|ax|axes|fig|sns)\.(?:bar|barh|plot|pie|scatter|hist|imshow|boxplot|show|subplots|figure)\s*\(|"
                   r"\.plot(?:\.\w+)?\s*\(\s*(?:kind\s*=|x\s*=|\))", re.I)
IMAGE = re.compile(r"\.(?:png|jpe?g|svg|pdf|gif|webp)$", re.I)
SAVE_ORDER = re.compile(r"\b(?:save|write|export|store|put)\b[^.]{0,60}\b(?:to|as|in|into)\s+(?:an?\s+|the\s+)?(?:new\s+)?"
                        r"(?:csv|json|tsv|text|txt|excel|xlsx|spreadsheet|markdown|html|png|image|pdf)\b", re.I)


def unsaved_output(task, code, files):
    """Checked in code: a program that draws a chart but saved no image, or a step that orders a file and got none.
    (A held-out run: the coder drew the bar chart with plt.show(), which shows nothing here, saved no file, and the
    jury passed it because the program printed which model was higher.)"""
    if DRAWS.search(code or "") and not any(IMAGE.search(f) for f in files):
        return ("It drew a chart but saved no image file: plt.show() shows nothing here. Save the chart with "
                "plt.savefig('<name>.png') (the name the task gives, if it gives one) and print the file name.")
    if SAVE_ORDER.search(task or "") and not files:
        return "The task asks for a file and the program saved none. Save it in the current folder and print its name."
    return None


FIND = re.compile(r"""\.find(?:_all)?\(\s*['"](\w+)['"]\s*,\s*(?:class_\s*=\s*|\{\s*['"]class['"]\s*:\s*)['"]([\w-]+)['"]|"""
                  r"""\.select(?:_one)?\(\s*['"](\w+)\.([\w-]+)['"]""")


def web_urls(task, code):
    from ..tools import web
    return list(dict.fromkeys(web.urls_in(task) + web.urls_in(code or "")))[:4]


def page_fact(err, urls):
    """Checked on the page itself: the program asked for <tag class="x"> and got nothing; where is class x really?
    (Held-out, twice: the preview showed <small class="author">, the 7B coder looked for a span both times.)"""
    from bs4 import BeautifulSoup
    from ..tools import web
    for m in FIND.finditer(err or ""):
        tag, cls = (m.group(1), m.group(2)) if m.group(1) else (m.group(3), m.group(4))
        for url in urls:
            try:
                soup = BeautifulSoup(web.get(url), "lxml")
            except Exception:  # noqa: BLE001 - a page that cannot be read gives no fact
                continue
            if soup.select(f"{tag}.{cls}"):
                continue
            hits = soup.select(f".{cls}")
            if hits:
                tags = sorted({h.name for h in hits})
                return (f"on {url} there is no <{tag} class=\"{cls}\">; class \"{cls}\" is on <{'>, <'.join(tags)}> "
                        f"({len(hits)} of them), e.g. {str(hits[0])[:160]}. Use find('{tags[0]}', class_='{cls}').")
    return None


NOT_FOUND_URL = re.compile(r"404 Client Error: Not Found for url: (\S+)|HTTP Error 404[^\n]*?(https?://\S+)")


def missing_page_fact(err, urls, code):
    """Checked on the site itself: the program asked for a page that does not exist; joined to the pages the program
    reads, where does that link really lead? (A held-out run and a dev run: the listing's next link 'page-2.html' was
    joined to the site's home page, and the 404 hint, given twice, did not change the 7B coder's program.)"""
    from urllib.parse import urljoin

    from ..tools import web
    m = NOT_FOUND_URL.search(err or "")
    if not m:
        return None
    bad = (m.group(1) or m.group(2)).rstrip(".,;)'\"")
    seg = bad.rstrip("/").rsplit("/", 1)[-1]
    paths = re.findall(r"""["']((?:[\w.-]+/)*[\w.-]+\.html?)["']""", code or "")
    bases = list(dict.fromkeys(urls + [urljoin(u, p) for u in urls for p in paths]))
    for b in bases:
        cand = urljoin(b, seg)
        if cand == bad or cand.rstrip("/") == b.rstrip("/"):
            continue
        try:
            web.get(cand)
        except Exception:  # noqa: BLE001 - not this one
            continue
        return (f"{bad} does not exist. The link '{seg}' belongs to the page {b}: urljoin('{b}', '{seg}') = {cand}, "
                f"which exists. Join each link to the URL of the page it was found on.")
    return None


SMALLEST = re.compile(r"\b(cheapest|lowest|fewest|least|smallest|shortest|oldest|earliest)\b", re.I)
LARGEST = re.compile(r"\b(most|highest|largest|biggest|longest|newest|latest|top|best)\b", re.I)
SORT_LINE = re.compile(r"sorted\(|\.sort\(|sort_values\(|nlargest|nsmallest")
SORT_DIRECTION = """You check ONE thing in a program: the direction of a sort. Reply with JSON only: {"first_item":"smallest" or "largest"}
- sorted(...) or .sort(...) without reverse, or reverse=False, or ascending=True: the smallest value comes first.
- reverse=True or ascending=False: the largest value comes first.
- nsmallest: smallest first. nlargest: largest first."""


def order_problem(task, code):
    """One narrow question, asked of a small model: which way does the program's sort run? What the task wants is
    read from its own word in code. (The 1.5B coder sorted the "cheapest" books with reverse=True; the reviewer and
    the jury of three, all small, passed it. Asked only about the line, the 1.7B read 7 of 7 directions right.)"""
    own = task.split("\n(Previous attempt was rejected:")[0]
    lo, hi = SMALLEST.search(own), LARGEST.search(own)
    if bool(lo) == bool(hi):  # no such word, or both: nothing to compare
        return None
    lines = [ln.strip() for ln in (code or "").splitlines() if SORT_LINE.search(ln)]
    if len(lines) != 1 or "[-" in code or "reversed(" in code or ".reverse()" in code:
        return None  # several sorts, or the far end is taken: not a question of one line
    data, _ = llm.chat_json("juror_fast", [{"role": "system", "content": SORT_DIRECTION},
                                           {"role": "user", "content": "LINE: " + lines[0][:400]}], max_new_tokens=30)
    first = data.get("first_item") if isinstance(data, dict) else None
    want = "smallest" if lo else "largest"
    if first in ("smallest", "largest") and first != want:
        return (f"The task asks for the {(lo or hi).group(0).lower()}: the {want} value must come first. This line "
                f"puts the {first} first: {lines[0][:200]}. Change the direction of that sort.")
    return None


def unread_pages(task, code):
    """Checked on the page itself: the listing goes on (a "next" link) and the program never follows one. (The 1.5B
    coder read the first of two pages and saved two of the three cheapest books.)"""
    if re.search(r"next|page-|page=|\?p=", code or "", re.I):
        return None
    from bs4 import BeautifulSoup
    from ..tools import web
    for url in web_urls(task.split("\n(Previous attempt was rejected:")[0], code):
        try:
            soup = BeautifulSoup(web.get(url), "lxml")
        except Exception:  # noqa: BLE001 - a page that cannot be read gives no fact
            continue
        a = soup.select_one('a[rel~="next"], li.next a, a.next')
        if a and a.get("href"):
            return (f"{url} is only the first page of the listing: it has a \"next\" link ({str(a)[:120]}). Read "
                    f"every page (follow the next link with urljoin(page url, href) until there is none) before "
                    f"choosing or saving anything.")
    return None


FETCHES = re.compile(r"\brequests\.(?:get|post)\s*\(|\burlopen\s*\(|\bhttpx\.|\bBeautifulSoup\s*\(")
ASKS_FETCH = re.compile(r"https?://|\bwww\.|\b[\w-]+\.(?:com|org|net|io|co)\b|\b(?:fetch\w*|scrap\w*|crawl\w*|api|url|website|"
                        r"web ?page|online)\b|\bdownload (?:the|it|them|from|a)\b|\bfrom the (?:web|site|page|internet)\b", re.I)


def refetches(task, context, code):
    """The program goes to the web for values an earlier step already found, and the step names no page to read: the
    1.5B coder, handed "220,473 downloads" by the researcher, scraped a page element that does not exist instead.
    Returns what to tell it, or None."""
    results = (context or "").split("## ", 1)[1] if "## " in (context or "") else ""
    if not results or not FETCHES.search(code or "") or ASKS_FETCH.search(task or ""):
        return None
    vals = [ln.strip()[:220] for ln in results.splitlines() if re.search(r"\d", ln) and not ln.startswith("Items:")][:6]
    if not vals:
        return None
    return ("The program fetches pages, but this step names no page to read and the team already found the values. "
            "Do not use requests or BeautifulSoup. Write the values into the program as plain numbers, taken from "
            "these results:\n" + "\n".join(vals))


def last_line(err):
    """The error's last line without addresses and line numbers, to tell whether a fix changed anything."""
    lines = [ln.strip() for ln in (err or "").strip().splitlines() if ln.strip()]
    return re.sub(r"0x[0-9a-f]+|line \d+", "", lines[-1])[:300] if lines else ""


def run(task, context, board, step_id, guard, workdir):
    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    before = {p.name for p in workdir.iterdir()}
    # the pages his task names, never the URLs in a previous attempt's error: a retry carrying "404 ... for url:
    # .../page-2.html" previewed only that missing page and lost the Mystery listing the first preview had found
    own = task.split("\n(Previous attempt was rejected:")[0]
    messages = task_messages(task, context, preview(own, workdir))
    want = expected_outputs(task, before)
    last, last_error, tried = None, None, set()
    name = f"{re.sub(r'[^A-Za-z0-9_]', '_', step_id)}.py"
    for attempt in range(1, config.CODER_MAX_ATTEMPTS + 1):
        stop.check()
        out = llm.chat("coder", messages, max_new_tokens=1400, stop="code")
        code = extract_code(out)
        if code.strip() in tried:
            # told what was wrong, it wrote the same program again (the 1.5B coder: six times in one run). Asking the
            # same way gives the same program; it is asked once more with some chance in the choice of words.
            board.log("coder", "same-program", f"attempt {attempt}: the program did not change; asked again")
            code = extract_code(llm.chat("coder", messages, max_new_tokens=1400, stop="code", temperature=0.7))
        tried.add(code.strip())
        again = refetches(own, context, code)
        if again and attempt < config.CODER_MAX_ATTEMPTS:  # told before it runs; the last attempt runs whatever it is
            board.log("coder", "team-values", f"attempt {attempt}: it fetches what the team already found; told to use the results")
            messages = messages + [{"role": "assistant", "content": f"```python\n{code}\n```"},
                                   {"role": "user", "content": prompts.CODER_FIX.format(error=again)}]
            continue
        if not guard.check_code("coder", code):
            return {"summary": "Stopped: the program needs Arnav's approval before it can run.", "code": code,
                    "returncode": None, "files": [], "attempts": attempt}
        res = run_python(code, workdir, name=name)
        board.log("coder", "run", f"attempt {attempt}: exit {res['returncode']} in {res['seconds']}s")
        last = {**res, "code": code, "attempts": attempt}
        missing = [f for f in want if not (workdir / f).exists()]
        new = [p for p in workdir.iterdir() if p.name not in before and p.name != name and not p.name.startswith(".")]
        silent = not res["stdout"].strip() and not new
        unsaved = unsaved_output(task, code, [p.name for p in new]) if not missing and not silent else None
        gone = [u for u, c in http_errors(res["stderr"]) if c == 404]
        if res["returncode"] == 0 and gone and not unsaved:
            # it "worked", but read pages that do not exist: in the same words as a 404 error, so its kind and the
            # page check (where the link really leads) apply
            unsaved = (f"It ran, but asked for pages that do not exist: 404 Client Error: Not Found for url: {gone[0]}"
                       + (f" (and {len(gone) - 1} more)" if len(gone) > 1 else "")
                       + ". What it read from them is missing from its results.")
        if res["returncode"] == 0 and not missing and not silent and not unsaved:
            from .verifier import describe_file  # what it saved, checked in code: a placeholder column, a blank chart
            bad = [d for d in (describe_file(p) for p in new if p.is_file()) if d.startswith(("BROKEN", "EMPTY"))]
            if bad:
                unsaved = ("The file it saved is wrong: " + "; ".join(bad)[:400] + ". Take each value from the "
                           "element the DATA PREVIEW shows it in (its exact tag and class); never write a placeholder "
                           "such as 'Unknown' for a value the task asks for.")
        if res["returncode"] == 0 and "Traceback" not in res["stderr"] and not missing and not silent and not unsaved:
            checks = example_checks(task, code)
            if checks:  # his own examples, run against the program's functions
                chk = run_python(code + "\n\n# checks from Arnav's examples\n" + "\n".join(checks), workdir,
                                 name=f"check_{name}")
                board.log("coder", "examples", f"{len(checks)} check(s) from his examples: "
                          + ("pass" if chk["returncode"] == 0 else "FAIL"))
                if chk["returncode"] != 0:
                    err = (chk["stderr"] or chk["stdout"])[-1200:]
                    # kept with the result: the program itself exits 0, and after the last attempt a jury of small
                    # models passed a fib() that returned 2 for fib(2)
                    last["examples_failed"] = last_line(err) or "an example from his task does not hold"
                    messages = messages + [{"role": "assistant", "content": f"```python\n{code}\n```"},
                                           {"role": "user", "content": prompts.CODER_FIX.format(
                                               error=err + "\nHint: " + prompts.FIX_HINTS["check"])}]
                    continue
            wrong_way = order_problem(task, code)
            hard = [x for x in (wrong_way, unread_pages(task, code)) if x]  # checked in code and on the page
            problems = hard or sanity(res["stdout"]) or review(task, code, res["stdout"])
            if not problems or attempt == config.CODER_MAX_ATTEMPTS:
                break
            board.log("code_reviewer", "fix", " | ".join(problems)[:300])
            messages = messages + [{"role": "assistant", "content": f"```python\n{code}\n```"},
                                   {"role": "user", "content": prompts.CODER_FIX.format(
                                       error="It ran, but the code does not do the task correctly:\n- " + "\n- ".join(problems)
                                       + f"\nOutput was:\n{res['stdout'][-800:]}")}]
            continue
        if res["returncode"] == 0 and not missing and silent:
            # it defined a function and never called it: the jury then rejected "the program ran, but no files"
            err = "It ran but printed nothing and saved nothing. Call the code and print the result the task asks for."
        elif res["returncode"] == 0 and unsaved:
            board.log("coder", "file-check", unsaved[:150])
            err = unsaved + f"\nOutput was:\n{res['stdout'][-800:]}"
        elif res["returncode"] == 0 and missing:
            err = f"It ran but did not create {', '.join(missing)}. Output was:\n{res['stdout'][-800:]}"
        else:
            err = (res["stderr"] or res["stdout"])[-1800:]
        key = last_line(err)  # the error itself: compared before any hint is added (the hint is the same every time)
        kind = error_kind(err)
        if kind:  # the error reader names the kind of failure; the coder is told what that kind usually needs
            board.log("coder", "error-kind", f"attempt {attempt}: {kind}")
            fact = (page_fact(err, web_urls(own, code)) if kind == "data"
                    else missing_page_fact(err, web_urls(own, code), code) if kind == "not_found" else None)
            if fact:
                board.log("coder", "page-check", fact[:200])
            err = f"{err}\nHint ({kind}): {prompts.FIX_HINTS[kind]}" + (f"\nPage check: {fact}" if fact else "")
        if key and key == last_error:
            # its fix changed nothing: the same error 12 times (a host it could not reach) cost 28 minutes of the 7B
            # coder. The hive loop gets the error and decides: retry with the reason, another specialist, or stop.
            board.log("coder", "same-error", f"attempt {attempt} failed exactly like the one before: {key[:150]}")
            break
        last_error = key
        messages = messages + [{"role": "assistant", "content": f"```python\n{code}\n```"},
                               {"role": "user", "content": prompts.CODER_FIX.format(error=err)}]
    files = sorted(p.name for p in workdir.iterdir() if p.name not in before and p.name != name
                   and not p.name.startswith("."))
    summary = (last["stdout"] or "").strip()[-1500:] or (last["stderr"] or "")[-600:]
    return {"summary": summary, "code_path": str(workdir / name), "returncode": last["returncode"],
            "stderr": last["stderr"][-1500:], "files": files, "attempts": last["attempts"],
            "seconds": last["seconds"], **({"examples_failed": last["examples_failed"]} if last.get("examples_failed") else {})}

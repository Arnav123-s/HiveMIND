"""Coder: writes a program, runs it, reads the error, fixes it, until it runs."""
import re
from pathlib import Path

from .. import config, llm, prompts, stop
from ..tools.preview import expected_outputs, preview
from ..tools.sandbox import run_python


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


def last_line(err):
    """The error's last line without addresses and line numbers, to tell whether a fix changed anything."""
    lines = [ln.strip() for ln in (err or "").strip().splitlines() if ln.strip()]
    return re.sub(r"0x[0-9a-f]+|line \d+", "", lines[-1])[:300] if lines else ""


def run(task, context, board, step_id, guard, workdir):
    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    before = {p.name for p in workdir.iterdir()}
    messages = task_messages(task, context, preview(task, workdir))
    want = expected_outputs(task, before)
    last, last_error = None, None
    name = f"{re.sub(r'[^A-Za-z0-9_]', '_', step_id)}.py"
    for attempt in range(1, config.CODER_MAX_ATTEMPTS + 1):
        stop.check()
        out = llm.chat("coder", messages, max_new_tokens=1400, stop="code")
        code = extract_code(out)
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
        if res["returncode"] == 0 and "Traceback" not in res["stderr"] and not missing and not silent and not unsaved:
            checks = example_checks(task, code)
            if checks:  # his own examples, run against the program's functions
                chk = run_python(code + "\n\n# checks from Arnav's examples\n" + "\n".join(checks), workdir,
                                 name=f"check_{name}")
                board.log("coder", "examples", f"{len(checks)} check(s) from his examples: "
                          + ("pass" if chk["returncode"] == 0 else "FAIL"))
                if chk["returncode"] != 0:
                    err = (chk["stderr"] or chk["stdout"])[-1200:]
                    messages = messages + [{"role": "assistant", "content": f"```python\n{code}\n```"},
                                           {"role": "user", "content": prompts.CODER_FIX.format(
                                               error=err + "\nHint: " + prompts.FIX_HINTS["check"])}]
                    continue
            problems = sanity(res["stdout"]) or review(task, code, res["stdout"])
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
            board.log("coder", "unsaved", unsaved[:150])
            err = unsaved + f"\nOutput was:\n{res['stdout'][-800:]}"
        elif res["returncode"] == 0 and missing:
            err = f"It ran but did not create {', '.join(missing)}. Output was:\n{res['stdout'][-800:]}"
        else:
            err = (res["stderr"] or res["stdout"])[-1800:]
        kind = error_kind(err)
        if kind:  # the error reader names the kind of failure; the coder is told what that kind usually needs
            board.log("coder", "error-kind", f"attempt {attempt}: {kind}")
            err = f"{err}\nHint ({kind}): {prompts.FIX_HINTS[kind]}"
        key = last_line(err)
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
            "seconds": last["seconds"]}

"""Calculator: arithmetic, percentages, dates and unit conversions, exactly.

A small model writes a few lines of Python that print the answer, and Python does the arithmetic: models are bad at
sums, Python is not. Far cheaper than the coder (a 7B model, its reviewer and a jury of three) for a percentage.
"""
import re

from .. import llm, prompts
from ..tools import sandbox

ALLOWED = {"math", "datetime", "statistics", "fractions", "decimal", "calendar"}
FORBIDDEN = re.compile(r"\b(open|exec|eval|compile|__import__|input|globals|locals|getattr|setattr)\s*\(|\bos\.|\bsys\.|"
                       r"\bsubprocess\b|\bsocket\b|\brequests\b|\burllib\b|\bshutil\b|\bpathlib\b")


def program(text):
    m = re.search(r"```(?:python)?\s*\n(.*?)```", text, re.S)
    return (m.group(1) if m else text).strip()


def unsafe(code):
    """Only arithmetic: no files, network, processes or dynamic code; standard maths modules only."""
    mods = set(re.findall(r"^\s*import\s+([\w.]+)", code, re.M)) | set(re.findall(r"^\s*from\s+([\w.]+)\s+import", code, re.M))
    bad = sorted(m for m in mods if m.split(".")[0] not in ALLOWED)
    if bad:
        return f"imports {bad} (only {sorted(ALLOWED)})"
    m = FORBIDDEN.search(code)
    return f"uses {m.group(0).strip()}" if m else ""


_N = {"no": 0, "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6}
PLACES = re.compile(r"\b(no|zero|one|two|three|four|five|six|\d)\s+decimal(?:\s+places?|\s+digits?)?\b|"
                    r"\b(\d)\s*d\.?p\.?(?!\w)|\bto the nearest (whole number|integer)\b", re.I)
WEEKDAY_Q = re.compile(r"\b(what|which) day of the week\b|\bwhat weekday\b", re.I)
DAY_NAME = re.compile(r"\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b", re.I)


def form_problems(task, out):
    """Checked in code: the answer is printed in the form he asked for. (Held-out runs: 'One decimal place' printed
    42.16, copying the prompt's example; 'what day of the week' printed weekday() = 6, and the writer guessed
    'Saturday' from it.)"""
    probs = []
    m = PLACES.search(task or "")
    if m:
        n = 0 if m.group(3) else int(_N.get((m.group(1) or "").lower(), m.group(1) or m.group(2)))
        lines = [ln for ln in (out or "").splitlines() if "answer" in ln.lower()] or (out or "").splitlines()[-1:]
        # the answer's numbers, not his inputs printed beside them ("26.2 miles = 42.16 km")
        ans = re.findall(r"-?\d+(?:\.(\d+))?", lines[-1].split(":", 1)[-1].split("=")[-1]) if lines else []
        nums = [d for d in ans if d or n == 0]
        if nums and any(len(d) != n for d in nums):
            probs.append(f"The task asks for {n} decimal place(s); the output has {len(nums[0])}. Round the answer to "
                         f"exactly {n} decimal place(s).")
    if WEEKDAY_Q.search(task or "") and not DAY_NAME.search(out or ""):
        probs.append('The task asks for a day of the week: print its name with date.strftime("%A"), not a number.')
    return probs


def run(task, context, board, step_id, workdir):
    user = f"TASK: {task}" + (f"\n\nRESULTS SO FAR:\n{context[:2500]}" if context else "")
    msgs = [{"role": "system", "content": prompts.CALCULATOR}, {"role": "user", "content": user}]
    for attempt in (1, 2):  # a second try only when the answer's form is wrong (checked in code)
        code = program(llm.chat("calculator", msgs, max_new_tokens=400))
        why = unsafe(code)
        if why:
            board.log("calculator", "refused", f"{step_id}: the program {why}")
            return {"summary": "", "failed": f"the program {why}", "code": code, "items": []}
        res = sandbox.run_python(code, workdir / "calc", name=f"{step_id.replace('[', '_').replace(']', '')}.py",
                                 timeout=20)
        out = res["stdout"].strip()
        board.log("calculator", "run", f"{step_id}: exit {res['returncode']}: {out[:200]}")
        probs = form_problems(task, out) if res["returncode"] == 0 else []
        if not probs or attempt == 2:
            break
        board.log("calculator", "form", " | ".join(probs)[:300])
        msgs = msgs + [{"role": "assistant", "content": f"```python\n{code}\n```"},
                       {"role": "user", "content": f"Output was: {out[:300]}\n" + "\n".join(probs)
                        + "\nReturn the whole fixed program in a single ```python block."}]
    return {"summary": out[:2000], "code": code, "returncode": res["returncode"], "stderr": res["stderr"][-1000:],
            "items": []}

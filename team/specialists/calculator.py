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


def run(task, context, board, step_id, workdir):
    user = f"TASK: {task}" + (f"\n\nRESULTS SO FAR:\n{context[:2500]}" if context else "")
    code = program(llm.chat("calculator", [{"role": "system", "content": prompts.CALCULATOR},
                                           {"role": "user", "content": user}], max_new_tokens=400))
    why = unsafe(code)
    if why:
        board.log("calculator", "refused", f"{step_id}: the program {why}")
        return {"summary": "", "failed": f"the program {why}", "code": code, "items": []}
    res = sandbox.run_python(code, workdir / "calc", name=f"{step_id.replace('[', '_').replace(']', '')}.py", timeout=20)
    out = res["stdout"].strip()
    board.log("calculator", "run", f"{step_id}: exit {res['returncode']}: {out[:200]}")
    return {"summary": out[:2000], "code": code, "returncode": res["returncode"], "stderr": res["stderr"][-1000:],
            "items": []}

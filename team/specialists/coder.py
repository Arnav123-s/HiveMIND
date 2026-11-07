"""Coder: writes a program, runs it, reads the error, fixes it, until it runs."""
import re
from pathlib import Path

from .. import config, llm, prompts
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


def run(task, context, board, step_id, guard, workdir):
    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    before = {p.name for p in workdir.iterdir()}
    messages = task_messages(task, context, preview(task, workdir))
    want = expected_outputs(task, before)
    last = None
    name = f"{re.sub(r'[^A-Za-z0-9_]', '_', step_id)}.py"
    for attempt in range(1, config.CODER_MAX_ATTEMPTS + 1):
        out = llm.chat("coder", messages, max_new_tokens=1400, stop="code")
        code = extract_code(out)
        if not guard.check_code("coder", code):
            return {"summary": "Stopped: the program needs Arnav's approval before it can run.", "code": code,
                    "returncode": None, "files": [], "attempts": attempt}
        res = run_python(code, workdir, name=name)
        board.log("coder", "run", f"attempt {attempt}: exit {res['returncode']} in {res['seconds']}s")
        last = {**res, "code": code, "attempts": attempt}
        missing = [f for f in want if not (workdir / f).exists()]
        if res["returncode"] == 0 and "Traceback" not in res["stderr"] and not missing:
            break
        if res["returncode"] == 0 and missing:
            err = f"It ran but did not create {', '.join(missing)}. Output was:\n{res['stdout'][-800:]}"
        else:
            err = (res["stderr"] or res["stdout"])[-1800:]
        messages = messages + [{"role": "assistant", "content": f"```python\n{code}\n```"},
                               {"role": "user", "content": prompts.CODER_FIX.format(error=err)}]
    files = sorted(p.name for p in workdir.iterdir() if p.name not in before and p.name != name)
    summary = (last["stdout"] or "").strip()[-1500:] or (last["stderr"] or "")[-600:]
    return {"summary": summary, "code_path": str(workdir / name), "returncode": last["returncode"],
            "stderr": last["stderr"][-1500:], "files": files, "attempts": last["attempts"],
            "seconds": last["seconds"]}

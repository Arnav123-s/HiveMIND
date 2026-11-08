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


def run(task, context, board, step_id, guard, workdir):
    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    before = {p.name for p in workdir.iterdir()}
    messages = task_messages(task, context, preview(task, workdir))
    want = expected_outputs(task, before)
    last = None
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
        if res["returncode"] == 0 and "Traceback" not in res["stderr"] and not missing:
            problems = sanity(res["stdout"]) or review(task, code, res["stdout"])
            if not problems or attempt == config.CODER_MAX_ATTEMPTS:
                break
            board.log("code_reviewer", "fix", " | ".join(problems)[:300])
            messages = messages + [{"role": "assistant", "content": f"```python\n{code}\n```"},
                                   {"role": "user", "content": prompts.CODER_FIX.format(
                                       error="It ran, but the code does not do the task correctly:\n- " + "\n- ".join(problems)
                                       + f"\nOutput was:\n{res['stdout'][-800:]}")}]
            continue
        if res["returncode"] == 0 and missing:
            err = f"It ran but did not create {', '.join(missing)}. Output was:\n{res['stdout'][-800:]}"
        else:
            err = (res["stderr"] or res["stdout"])[-1800:]
        messages = messages + [{"role": "assistant", "content": f"```python\n{code}\n```"},
                               {"role": "user", "content": prompts.CODER_FIX.format(error=err)}]
    files = sorted(p.name for p in workdir.iterdir() if p.name not in before and p.name != name
                   and not p.name.startswith("."))
    summary = (last["stdout"] or "").strip()[-1500:] or (last["stderr"] or "")[-600:]
    return {"summary": summary, "code_path": str(workdir / name), "returncode": last["returncode"],
            "stderr": last["stderr"][-1500:], "files": files, "attempts": last["attempts"],
            "seconds": last["seconds"]}

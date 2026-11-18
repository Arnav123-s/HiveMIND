"""One local, private CPU language model per run. Generates source; it has no grading or tool access."""

import socket
import subprocess
import time
from contextlib import contextmanager
from pathlib import Path

from team import ternary
from team.tools.source import extract_code

SYSTEM = """You are a member of a CPU research and programming hive. Build the requested complete Python function solve(x) for unseen inputs. Reply with a single Python code block. Standard library only. Input and return values are JSON-compatible. No package installation, disk, network, stdin, printed answers or examples in the program. A shared pure function least_squares(X, y) returns fitted coefficients for a regularized linear least-squares problem; add your own intercept column if needed. Write actual executable code. Use the requested schema exactly."""


@contextmanager
def server(binary, weights, log, adapter=None, threads=4):
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    url = f"http://127.0.0.1:{port}"
    cmd = [
        str(Path(binary).resolve()),
        "-m",
        str(Path(weights).resolve()),
        "-t",
        str(threads),
        "-c",
        "6144",
        "--parallel",
        "1",
        "--jinja",
        "-fa",
        "on",
        "-rtr",
        "--cache-ram",
        "0",
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
    ]
    if adapter:
        cmd.extend(["--lora", str(Path(adapter).resolve())])
    with open(log, "w") as logstream:
        proc = subprocess.Popen(cmd, stdout=logstream, stderr=subprocess.STDOUT)
        try:
            end = time.monotonic() + 150
            while time.monotonic() < end and proc.poll() is None:
                if (ternary._get(url + "/health", timeout=1) or {}).get("status") == "ok":
                    break
                time.sleep(0.2)
            else:
                raise RuntimeError(f"inference server did not start; see {log}")
            yield url
        finally:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()


def generate(url, task, prefix="", earlier=None, budget=1400, seed=3141, focused=False, concise=False):
    system = SYSTEM
    if focused:
        system = (
            "Write the complete Python function solve(x). Its argument is the already decoded Python object "
            "described by the client. The caller handles JSON, storage and the process. Use Python's standard "
            "library. Reply with one runnable Python code block. Include all imports. Implement every phase "
            "and preserve requested ordering and tie rules."
        )
        if "least_squares" in task.text:
            system += " The supplied least_squares(X,y) function accepts ordinary lists and returns coefficients; include an intercept column."
    if concise:
        system += (
            " Output executable code only. Omit docstrings, explanatory comments, annotations, examples and "
            "debugging prints. Use clear names. Finish the function and include its return statement."
        )
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": task.text + "\n" + task.example + prefix},
    ]
    if earlier:
        code, feedback = earlier
        messages.extend(
            [
                {"role": "assistant", "content": "```python\n" + code[:5900] + "\n```"},
                {"role": "user", "content": feedback + "\nReturn a complete corrected implementation."},
            ]
        )
    start = time.monotonic()
    res = ternary._post(
        url + "/v1/chat/completions",
        {
            "messages": messages,
            "max_tokens": budget,
            "temperature": 0.0,
            "seed": seed,
            "cache_prompt": False,
            "chat_template_kwargs": {"enable_thinking": False},
        },
        timeout=max(900, budget),
    )
    choice = res["choices"][0]
    reply = choice["message"]["content"]
    return dict(
        source=extract_code(reply),
        text=reply,
        usage=res.get("usage"),
        stop=choice["finish_reason"],
        prompt_version="focused-concise"
        if concise and focused
        else "concise"
        if concise
        else "focused"
        if focused
        else "original",
        seconds=round(time.monotonic() - start, 3),
    )

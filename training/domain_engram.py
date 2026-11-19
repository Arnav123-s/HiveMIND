"""Fit a small, CPU-only first-answer-token LoRA on a frozen Qwen3 Ternary-Bonsai model.

A checked exercise has a prompt and a one-token answer. The native server renders
the actual chat template and supplies its last hidden state. A regularized
least-squares fit predicts a score increment for each observed label; the
truncated SVD of that map is written as output.weight's two LoRA factors.
This is a supervised output-head fit, so callers should apply it only to the
same decision. Keep a previous deployed file until separate validation passes.
"""
import contextlib
from functools import lru_cache
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

from team import talk

RANK = 4
MARGIN = 6.0
RIDGE = 0.1
T80_SHA256 = "1376f942aa90e60f7b570c1d81b3916fea1315ff85aa1c4d19006af68fb4b922"


@lru_cache(maxsize=4)
def _base_hash(path, identity):
    with path.open("rb") as source:
        digest = hashlib.sha256()
        for chunk in iter(lambda: source.read(1 << 20), b""):
            digest.update(chunk)
        return digest.hexdigest()


def _post(url, route, body):
    request = urllib.request.Request(url + route, data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=450) as response:
        return json.load(response)


@contextlib.contextmanager
def _server(model, runtime, threads, *, features=False, edits=()):
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    url = f"http://127.0.0.1:{port}"
    command = [str(Path(runtime).resolve()), "-m", str(Path(model).resolve()),
               "-t", str(threads), "-tb", str(threads), "-ngl", "0", "-c", "2048", "--parallel", "1",
               "--host", "127.0.0.1", "--port", str(port), "--jinja"]
    if features:
        command += ["--embeddings", "--pooling", "last", "--embd-normalize", "-1"]
    for edit in edits:
        command += ["--lora", str(Path(edit).resolve())]
    if edits:
        command += ["--lora-init-without-apply", "--no-graph-reuse"]
    with tempfile.TemporaryFile(mode="w+b") as log:
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=log, stderr=log)
        try:
            for _ in range(600):
                if process.poll() is not None:
                    break
                try:
                    with urllib.request.urlopen(url + "/health", timeout=1) as response:
                        if json.load(response).get("status") == "ok":
                            break
                except OSError:
                    pass
                time.sleep(0.25)
            else:
                raise RuntimeError("native engram server did not become ready")
            if process.poll() is not None:
                log.seek(max(0, log.tell() - 1200))
                raise RuntimeError(f"native engram server exited: {log.read().decode(errors='replace')}")
            yield url
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()


def _messages(row):
    system = row.get("system") or talk.TALK.format(name="the user", today="the time of this practice exercise")
    return [{"role": "system", "content": system}, {"role": "user", "content": row["prompt"]}]


def _identity(row):
    return " ".join(row["prompt"].split())


def eligible_rows(rows, url):
    """Return rows with an unambiguous, single native output token, with token ID added."""
    result = []
    tokens = {}
    for item in rows:
        prompt, answer = item.get("prompt"), item.get("answer")
        if not isinstance(prompt, str) or not prompt.strip() or not isinstance(answer, str) or not answer.strip():
            continue
        if answer not in tokens:
            tokens[answer] = _post(url, "/tokenize", {"content": answer, "add_special": False})["tokens"]
        if len(tokens[answer]) == 1:
            result.append({**item, "token": tokens[answer][0]})
    return result


def _render(url, row):
    return _post(url, "/apply-template", {"messages": _messages(row),
                 "chat_template_kwargs": {"enable_thinking": False}})["prompt"]


def _feature(url, row):
    import numpy as np
    rendered = _render(url, row)
    count = len(_post(url, "/tokenize", {"content": rendered})["tokens"])
    if count >= 2048:
        raise ValueError("training prompt exceeds the native context")
    values = _post(url, "/embedding", {"content": rendered, "embd_normalize": -1})[0]["embedding"]
    return np.array(values[-1] if isinstance(values[0], list) else values, dtype=np.float64)


def _feature_helper(runtime, directory):
    """Use the local static runtime build for prefix reuse when it is available."""
    build = Path(runtime).resolve().parent.parent
    source = build.parent
    libraries = [build / "src/libllama.a", build / "ggml/src/libggml.a"]
    compiler = shutil.which("c++")
    if not compiler or not all(p.is_file() for p in libraries) or not (source / "include/llama.h").is_file():
        return None
    helper = directory / "domain-features"
    command = [compiler, "-std=c++17", "-O2", "-I" + str(source / "include"), "-I" + str(source / "ggml/include"),
               str(Path(__file__).with_name("domain_features.cpp")), *map(str, libraries),
               "-fopenmp", "-lm", "-lpthread", "-o", str(helper)]
    return helper if subprocess.run(command, capture_output=True, timeout=120).returncode == 0 else None


def _feature_rows(rows, validation, model, runtime, threads):
    import numpy as np
    with tempfile.TemporaryDirectory() as tmp:
        directory = Path(tmp)
        helper = _feature_helper(runtime, directory)
        prompts = directory / "ids"
        with _server(model, runtime, threads, features=helper is None) as url:
            with urllib.request.urlopen(url + "/v1/models") as response:
                meta = json.load(response)["data"][0]["meta"]
            if (meta.get("n_embd"), meta.get("n_vocab")) != (4096, 151669):
                raise ValueError("this CPU engram trainer targets the t80 Qwen3 output projection")
            accepted = eligible_rows(rows, url)
            token_counts = {}
            for row in accepted:
                token_counts[row["token"]] = token_counts.get(row["token"], 0) + 1
            if not 2 <= len(token_counts) <= 64 or min(token_counts.values()) < 2:
                raise ValueError("need at least two distinct prompts for each of two or more single-token answers")
            if len(eligible_rows(validation, url)) != len(validation):
                raise ValueError("all validation answers must be single native tokens")
            if helper is None:
                return accepted, np.asarray([_feature(url, row) for row in accepted])
            with prompts.open("w") as stream:
                for row in accepted:
                    ids = _post(url, "/tokenize", {"content": _render(url, row)})["tokens"]
                    if not ids or len(ids) >= 2048:
                        raise ValueError("training prompt exceeds the native context")
                    print(*ids, file=stream)
        # Release the tokenizer server's 8B context before loading the causal feature helper.
        vectors = directory / "last.f32"
        proc = subprocess.run([str(helper), str(model), str(prompts), str(vectors), str(threads)], capture_output=True)
        if proc.returncode:
            raise RuntimeError(proc.stderr.decode(errors="replace")[-1500:])
        return accepted, np.fromfile(vectors, dtype=np.float32).reshape(len(accepted), 4096)


def fit(features, tokens, *, target_scores=None):
    """Fit rank-four factors for observed labels. Optional target increments use sorted token-ID columns."""
    import numpy as np
    x = np.asarray(features, dtype=np.float64)
    ids, y = np.unique(tokens, return_inverse=True)
    if x.ndim != 2 or not np.isfinite(x).all() or x.shape[0] != len(y):
        raise ValueError("bad native feature matrix")
    counts = np.bincount(y)
    if len(ids) < 2 or len(ids) > 64 or counts.min() < 2:
        raise ValueError("need 2 to 64 distinct answer tokens, with two distinct training prompts per label")
    norm = float(np.median(np.linalg.norm(x, axis=1)))
    if not np.isfinite(norm) or norm == 0:
        raise ValueError("zero native hidden state")
    x = x / norm
    # Equal total training weight per label even when one answer occurs more often.
    weights = np.sqrt(len(y) / (len(ids) * counts[y]))[:, None]
    targets = np.eye(len(ids))[y] * MARGIN if target_scores is None else np.asarray(target_scores, dtype=np.float64)
    if targets.shape != (len(y), len(ids)) or not np.isfinite(targets).all():
        raise ValueError("bad supervised label-score matrix")
    centered = x - x.mean(axis=0)
    penalty = max(float(np.sum(centered * centered) / len(y)), 1e-5) * RIDGE
    design = x * weights
    # Solve in sample space; a short replay corpus never needs a dense hidden_size² matrix.
    dual = np.linalg.solve(design @ design.T + penalty * np.eye(len(y)), targets * weights)
    residual = dual.T @ design / norm
    u, sigma, vt = np.linalg.svd(residual, full_matrices=False)
    r = min(RANK, len(sigma))
    scale = np.sqrt(sigma[:r])
    a = np.zeros((RANK, x.shape[1]), dtype=np.float16)
    b = np.zeros((len(ids), RANK), dtype=np.float16)
    a[:r] = scale[:, None] * vt[:r]
    b[:, :r] = u[:, :r] * scale
    predicted = ((x * norm) @ a.T) @ b.T
    return ids, a, b, dict(rank=RANK, effective_rank=r, training_rows=len(y),
                            target_mse_before=float(np.mean(targets**2)),
                            target_mse_after=float(np.mean((predicted - targets)**2)))


def write_adapter(path, ids, a, b, vocab):
    """Write the Qwen3 output projection in the native GGUF LoRA convention."""
    import numpy as np
    vendored = str(Path(__file__).resolve().parent / "llama_cpp_convert" / "gguf-py")
    if vendored not in sys.path:
        sys.path.insert(0, vendored)
    from gguf import GGUFWriter
    if min(ids) < 0 or max(ids) >= vocab or a.shape[0] != RANK:
        raise ValueError("incompatible native vocabulary or rank")
    output = np.zeros((vocab, RANK), dtype=np.float16)
    output[ids] = b
    writer = GGUFWriter(path, "qwen3")
    try:
        writer.add_type("adapter")
        writer.add_string("adapter.type", "lora")
        writer.add_float32("adapter.lora.alpha", float(RANK))
        writer.add_name("HiveMIND checked label engram")
        writer.add_file_type(1)
        writer.add_tensor("output.weight.lora_a", a)
        writer.add_tensor("output.weight.lora_b", output)
        writer.write_header_to_file()
        writer.write_kv_data_to_file()
        writer.write_tensors_to_file()
    finally:
        writer.close()


def _first(url, row):
    reply = _post(url, "/v1/chat/completions", {"messages": _messages(row), "max_tokens": 1,
                  "temperature": 0, "seed": 741, "cache_prompt": True,
                  "chat_template_kwargs": {"enable_thinking": False}})
    return reply["choices"][0]["message"]["content"]


def validate(rows, path, *, model, runtime, threads=2):
    """Measure paired unrestricted first tokens on an independent labeled sample in the native engine."""
    with _server(model, runtime, threads, edits=[path]) as url:
        if len(eligible_rows(rows, url)) != len(rows):
            raise ValueError("all validation answers must be single native tokens")
        _post(url, "/lora-adapters", [{"id": 0, "scale": 0.0}])
        before = [_first(url, row) for row in rows]
        _post(url, "/lora-adapters", [{"id": 0, "scale": 1.0}])
        after = [_first(url, row) for row in rows]
    return validation_result(rows, before, after)


def validation_result(rows, before, after):
    cases = []
    for row, off, on in zip(rows, before, after, strict=True):
        gold = row["answer"]
        cases.append(dict(expected=gold, before=off, after=on,
                          prompt_sha256=hashlib.sha256(row["prompt"].encode()).hexdigest(),
                          before_correct=off.strip().casefold() == gold.strip().casefold(),
                          after_correct=on.strip().casefold() == gold.strip().casefold()))
    return dict(count=len(cases), before=sum(c["before_correct"] for c in cases),
                after=sum(c["after_correct"] for c in cases),
                regressions=sum(c["before_correct"] and not c["after_correct"] for c in cases), cases=cases)


def train(rows, path, *, model, runtime, threads=2, validation=()):
    """Stage a bounded candidate from checked examples; callers decide promotion using the returned validation."""
    rows, validation = list(rows), list(validation)
    if type(threads) is not int or threads < 1:
        raise ValueError("threads must be a positive integer")
    for item in [*rows, *validation]:
        if not isinstance(item, dict) or not isinstance(item.get("prompt"), str) or not isinstance(item.get("answer"), str):
            raise ValueError("exercises require a text prompt and answer")
    if not 1 <= len(rows) <= 256 or len(validation) > 64:
        raise ValueError("supply 1–256 training rows and at most 64 validation rows")
    unique = {}
    for row in rows:
        key = _identity(row)
        if key in unique and unique[key]["answer"] != row["answer"]:
            raise ValueError("conflicting training labels for one prompt")
        unique[key] = row
    held = {_identity(row) for row in validation}
    if len(held) != len(validation) or held.intersection(unique):
        raise ValueError("validation prompts must be unique and disjoint from training")
    base = Path(model).resolve()
    stat = base.stat()
    if _base_hash(base, (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)) != T80_SHA256:
        raise ValueError("only the released Ternary-Bonsai-8B-PQ2_0 base can publish t80 engrams")
    accepted, features = _feature_rows(unique.values(), validation, base, runtime, threads)
    ids, a, b, result = fit(features, [row["token"] for row in accepted])
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=path.parent) as directory:
        candidate = Path(directory) / "candidate.gguf"
        write_adapter(candidate, ids, a, b, 151669)
        result.update(base_sha256=T80_SHA256, labels=sorted({row["answer"] for row in accepted}), skipped_rows=len(rows)-len(accepted),
                      sha256=hashlib.sha256(candidate.read_bytes()).hexdigest())
        result["validation"] = validate(validation, candidate, model=model, runtime=runtime, threads=threads) if validation else None
        os.replace(candidate, path)
    return result

"""Collect native raw model measurements from a frozen panel, without consulting target labels."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

from route import Members, HERE, ROOT, np
from training.domain_engram import _base_hash, T80_SHA256

REPORT = ROOT / "training/reports/domain-engrams"


def render(domain, question, instructions, system):
    user = instructions[domain]["instruction"] + " " + question
    return ("<|im_start|>system\n" + system + "<|im_end|>\n<|im_start|>user\n" + user
            + "<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("model", "build", "panel", "out"):
        parser.add_argument("--" + name, type=Path, required=True)
    opts = parser.parse_args()
    if _base_hash(opts.model, opts.model.stat().st_size) != T80_SHA256:
        raise ValueError("expected the original t80 base weights")
    s = Members().study
    doc = json.loads((REPORT / "exercises.json").read_bytes())
    system = (REPORT / "system.txt").read_text()
    rows = json.loads(opts.panel.read_bytes())
    # Include a historical control for the exact prompt renderer and raw features.
    control = s.rows[0]
    fields = [(control.domain, control.question), *((r["domain"], r["question"]) for r in rows)]
    ordered = sorted(range(1, len(fields)), key=lambda i: fields[i][0])
    order = [0, *ordered]
    prompts = [render(*fields[i], doc, system) for i in order]
    with TemporaryDirectory() as tmp:
        temp = Path(tmp)
        build = opts.build.resolve()
        source = build.parent
        subprocess.run(["c++", "-std=c++17", "-O2", "-I" + str(source / "include"), "-I" + str(source / "ggml/include"),
                        str(HERE / "endpoints.cpp"), str(build / "src/libllama.a"), str(build / "ggml/src/libggml.a"),
                        "-fopenmp", "-lm", "-lpthread", "-o", str(temp / "measure")], check=True)
        (temp / "input").write_bytes(b"\0".join(p.encode() for p in prompts) + b"\0")
        subprocess.run([str(temp / "measure"), str(opts.model), str(temp / "input"), str(temp / "values")],
                       check=True, timeout=1800)
        raw = np.fromfile(temp / "values", np.float32).reshape(len(fields), 4096 + 151669)[np.argsort(order)]
    if not np.isfinite(raw).all():
        raise ValueError("nonfinite native output")
    x, logits = raw[:, :4096], raw[:, 4096:]
    similarity = float(np.dot(x[0], s.x[0]) / (np.linalg.norm(x[0]) * np.linalg.norm(s.x[0])))
    control_delta = float(np.max(abs(logits[0, s.tokens] - s.base[0])))
    if similarity < 0.999 or control_delta > 0.5:
        raise ValueError(f"historical prompt or features mismatch: {similarity=}, {control_delta=}")
    sys.path.insert(0, str(ROOT / "training/llama_cpp_convert/gguf-py"))
    from gguf import GGUFReader
    class VocabularyReader(GGUFReader):
        def _build_tensors(self, start_offs, fields):
            return
    reader = VocabularyReader(str(opts.model))
    vocab = reader.get_field("tokenizer.ggml.tokens")
    x, logits = x[1:], logits[1:]
    candidates = logits[:, s.tokens].copy()
    logits[:, s.tokens] = -np.inf
    highest = logits.argmax(axis=1)
    words = [vocab.contents(int(i)).strip("ĠĊĉ \r\n\t").casefold() for i in highest]
    np.savez_compressed(opts.out, cohort=sha256(opts.panel.read_bytes()).hexdigest(), x=x,
                        tokens=s.tokens, logits=candidates, outside_logit=logits.max(axis=1),
                        outside_id=highest, outside_word=np.asarray(words), control_cosine=similarity,
                        control_max_logit_delta=control_delta, model_sha=T80_SHA256)
    print(f"historical control {similarity=}, {control_delta=}", flush=True)


if __name__ == "__main__":
    main()

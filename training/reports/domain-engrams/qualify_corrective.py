"""Replay the corrective candidate, original GGUF and unedited body on the committed independent panel."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
STUDIES = {
    "water-v2": ("physics", "fb7bf4613a39c1b44022bccbdc6fb48c02fe560f2675ff056270389b98b5aee2"),
    "timing-v2": ("engineering", "01695797eeaa4cc85c938b727254bfca7b2e847f26bc6b5056b133d33a431cff"),
}


def sha(path):
    with path.open("rb") as stream:
        digest = hashlib.sha256()
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("study", choices=STUDIES)
    for name in ("panel", "model", "v1", "v2", "out"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--runtime", type=Path, help="llama-server within the pinned local ik_llama.cpp static build")
    parser.add_argument("--helper", type=Path, help="precompiled compare_native helper")
    parser.add_argument("--threads", type=int, default=2)
    args = parser.parse_args()
    if args.out.exists() or args.threads < 1:
        parser.error("--out must be new and --threads must be positive")
    key, panel_digest = STUDIES[args.study]
    primary = json.loads((HERE / "results.json").read_text())
    if sha(args.panel) != panel_digest or sha(args.model) != primary["base_sha256"]:
        parser.error("panel or model digest differs from study protocol")
    v1_digest, v2_digest = sha(args.v1), sha(args.v2)
    prior = primary["domain"][key]["validation"]
    fit = json.loads((HERE / args.study / "fit.json").read_text())
    if v1_digest != prior["fit"]["sha256"] or v2_digest != fit["sha256"]:
        parser.error("candidate fingerprint differs from frozen fit")
    exercise = json.loads((HERE / "exercises.json").read_text())[key]
    cases = [dict(id=f"original-{i}", phase="original", text=q, label=gold)
             for i, (q, gold) in enumerate(exercise["check"])]
    teaching = [*exercise["train"], *exercise["check"], *json.loads((HERE / args.study / "exercises.json").read_text())]
    seen_teaching = {" ".join(q.casefold().split()) for q, label in teaching}
    for row in json.loads(args.panel.read_text()):
        if " ".join(row["text"].casefold().split()) in seen_teaching:
            raise ValueError("independent prompt duplicates a teaching prompt")
        cases.append(dict(id=row["id"], phase=row.get("phase", "primary"), text=row["text"], label=row["label"]))
    if len({r["id"] for r in cases}) != len(cases) or len({r["text"] for r in cases}) != len(cases):
        raise ValueError("duplicate case identity")
    template = (HERE / "study-template.txt").read_text()
    with tempfile.TemporaryDirectory() as run:
        folder = Path(run)
        prompts = folder / "prompts"
        with prompts.open("wb") as stream:
            for i, row in enumerate(cases):
                user = exercise["instruction"] + " " + row["text"]
                rendered = template.replace("{{USER}}", user)
                row["prompt_sha256"] = hashlib.sha256(user.encode()).hexdigest()
                stream.write(str(i).encode() + b"\t" + rendered.encode() + b"\0")
        helper = args.helper
        if helper is None:
            if args.runtime is None:
                parser.error("--runtime or --helper is required")
            helper = folder / "compare"
            build = args.runtime.resolve().parent.parent
            source = build.parent
            subprocess.run(["c++", "-std=c++17", "-O2", "-I" + str(source / "include"),
                            "-I" + str(source / "ggml/include"), str(HERE / "compare_native.cpp"),
                            str(build / "src/libllama.a"), str(build / "ggml/src/libggml.a"),
                            "-fopenmp", "-lm", "-lpthread", "-o", str(helper)], check=True)
        outputs = folder / "output.tsv"
        subprocess.run([str(helper), str(args.model), str(args.v1), str(args.v2), str(prompts),
                        str(outputs), str(args.threads)], check=True)
        lines = outputs.read_text().splitlines()
    for i, (row, line) in enumerate(zip(cases, lines, strict=True)):
        ident, count, *predictions = line.split("\t")
        if ident != str(i) or len(predictions) != 8:
            raise ValueError("incomplete native comparison")
        row["input_tokens"] = int(count)
        for arm, token_id, encoded in zip(("base", "v1", "v2", "v1_reapplied"), predictions[::2], predictions[1::2], strict=True):
            piece = bytes.fromhex(encoded).decode(errors="replace")
            row[arm] = dict(token=int(token_id), text=piece, correct=piece.strip().casefold() == row["label"].casefold())
    scores = {}
    for phase in sorted({r["phase"] for r in cases}):
        group = [r for r in cases if r["phase"] == phase]
        scores[phase] = {"count": len(group), **{arm: sum(r[arm]["correct"] for r in group) for arm in ("base", "v1", "v2")}}
    reproduced = all(c["base"]["token"] == old["before_token"] and c["v1"]["token"] == old["after_token"]
                     for c, old in zip(cases[:3], prior["cases"], strict=True))
    restored = all(c["v1"]["token"] == c["v1_reapplied"]["token"] for c in cases)
    result = dict(qualified=reproduced and restored and all(c["v2"]["correct"] for c in cases),
                  graph_reuse=False, v1_reactivation_reproduced=restored,
                  original_tokens_reproduced=reproduced, scores=scores, panel_sha256=panel_digest,
                  base_sha256=primary["base_sha256"], v1_sha256=v1_digest, v2_sha256=v2_digest,
                  threads=args.threads, cases=cases)
    args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({k: result[k] for k in ("qualified", "original_tokens_reproduced", "v1_reactivation_reproduced", "scores")}))


if __name__ == "__main__":
    main()

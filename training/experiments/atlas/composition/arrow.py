"""Replay Arrow's output-layer routing rule on archived, model-generated states and actual LoRA deltas."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
REPORT = ROOT/"training/reports/domain-engrams"


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def pack(args):
    # Include every token any of six adapters can alter, and the strongest untouched competitor per row.
    # This computes exactly the same unrestricted argmax as retaining all 151,669 vocabulary logits.
    sys.path.insert(0,str(ROOT/"training/llama_cpp_convert/gguf-py"))
    from gguf import GGUFReader
    metadata = json.loads((REPORT/"catalog.json").read_text())
    native = json.loads((REPORT/"results.json").read_text())["domain"]
    names = sorted(native)
    weights, affected, hashes = {}, set(), {}
    for name in names:
        path = args.pack / ("t80+e_domain_"+metadata[name]["domain"]+".gguf.tmp")
        fit = json.loads((args.pack/(name+"-fit.json")).read_text())
        hashes[name] = digest(path)
        assert hashes[name] == fit["sha256"]
        arrays = {t.name:t.data for t in GGUFReader(str(path)).tensors}
        assert set(arrays) == {"output.weight.lora_a","output.weight.lora_b"}
        a,b = arrays["output.weight.lora_a"],arrays["output.weight.lora_b"]
        weights[name] = (a,b)
        affected.update(np.flatnonzero(np.any(b,axis=1)).tolist())
    ids = np.array(sorted(affected))
    vocab = {}
    for n in names:
        for r in native[n]["validation"]["cases"]:
            vocab[r["target_token"]] = r["expected"]
            vocab[r["before_token"]] = r["before"]
            vocab[r["after_token"]] = r["after"]
    x, logits, outside, outside_ids, rows, raw_hashes = [], [], [], [], [], {}
    for name in names:
        for i,r in enumerate(native[name]["validation"]["cases"]):
            case = f"{name}-check-{i}"
            inputs = [args.pack/(case+ext) for ext in (".f32",".logits")]
            v, scores = [np.fromfile(p,dtype=np.float32) for p in inputs]
            assert len(v)==4096 and len(scores)==151669
            raw_hashes[case] = dict(zip(("state","full_logits"),map(digest,inputs)))
            x.append(v)
            logits.append(scores[ids])
            scores[ids] = -np.inf
            other = int(scores.argmax())
            outside_ids.append(other)
            outside.append(scores[other])
            rows.append(dict(case=case,domain=name,expected=r["expected"],target=r["target_token"],
                             before=r["before_token"],intended=r["after_token"]))
    # Some runners-up were never winners in the older report. Use the pinned GGUF vocabulary for their pieces.
    unknown = (set(ids.tolist()) | set(outside_ids)) - set(vocab)
    if unknown:
        class VocabularyReader(GGUFReader):
            def _build_tensors(self, start_offs, fields):
                # The pre-ternary Python reader can decode all metadata without decoding model weights.
                return None
        reader = VocabularyReader(str(args.model))
        assert args.model.name == '1376f942aa90e60f7b570c1d81b3916fea1315ff85aa1c4d19006af68fb4b922' or digest(args.model)=='1376f942aa90e60f7b570c1d81b3916fea1315ff85aa1c4d19006af68fb4b922'
        field = reader.get_field("tokenizer.ggml.tokens")
        for token in unknown:
            text = bytes(field.parts[field.data[token]]).decode()
            # Only ASCII words with optional leading spaces can match any label in this archive.
            vocab[token] = text.replace("Ġ"," ")
    np.savez_compressed(args.data,x=np.asarray(x),logits=np.asarray(logits),ids=ids,outside=outside,
                        outside_ids=outside_ids,a=np.asarray([weights[n][0] for n in names]),
                        b=np.asarray([weights[n][1][ids] for n in names]))
    args.meta.write_text(json.dumps(dict(names=names,rows=rows,vocab=vocab,weights_sha256=hashes,
        original_native_inputs_sha256=raw_hashes,packed_sha256=digest(args.data)),indent=2)+"\n")


def score(data, meta):
    m = json.loads(meta.read_text())
    assert digest(data) == m["packed_sha256"]
    z = np.load(data)
    names = m["names"]
    # Inactive token rows of B are zero exactly, so this small SVD has the same nonzero right-singular vectors.
    a,b = z["a"].astype(np.float64),z["b"].astype(np.float64)
    prototypes = np.asarray([np.linalg.svd(bi@ai, full_matrices=False)[2][0] for ai,bi in zip(a,b)])
    out = []
    for i, row in enumerate(m["rows"]):
        h = z["x"][i].astype(np.float64)
        ranks = np.abs(prototypes@h)
        top = np.argsort(-ranks,kind="stable")[:2]
        soft = np.exp(ranks[top]-ranks[top].max())
        soft /= soft.sum()
        delta = np.asarray([bi@(ai@h) for ai,bi in zip(a,b)])
        arms = {"base":0, "intended":delta[names.index(row["domain"])],
                "all_mean":delta.mean(axis=0), "arrow_top2":soft@delta[top]}
        outputs = {}
        for arm, contribution in arms.items():
            values = z["logits"][i]+contribution
            max_value = max(values.max(),z["outside"][i])
            cand = list(map(int,z["ids"][values == max_value]))
            if z["outside"][i]==max_value:
                cand.append(int(z["outside_ids"][i]))
            token = min(cand)
            word = m["vocab"][str(token)]
            outputs[arm] = {"id":token,"piece":word,"strict_token":token==row["target"],
                            "correct":word.strip().casefold()==row["expected"].strip().casefold()}
        assert outputs["base"]["id"] == row["before"] and outputs["intended"]["id"] == row["intended"]
        out.append(dict(case=row["case"],expected=row["expected"],top=[names[j] for j in top],
                        scales=soft.tolist(),projections=dict(zip(names,ranks.tolist())),outputs=outputs))
    return dict(count=len(out),intended_in_top2=sum(r["case"].split("-")[0] in r["top"] for r in out),
                intended_top1=sum(r["case"].split("-")[0] == r["top"][0] for r in out),
                correct={arm:sum(r["outputs"][arm]["correct"] for r in out) for arm in arms},
                strict_token={arm:sum(r["outputs"][arm]["strict_token"] for r in out) for arm in arms},
                native_base_and_intended_argmax_checks=2*len(out),cases=out)


if __name__ == "__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--pack",type=Path,help="optional original domain-training capture directory")
    p.add_argument("--model",type=Path,help="pinned base for token-piece decoding during packaging")
    p.add_argument("--data",type=Path,default=HERE/"arrow-inputs.npz")
    p.add_argument("--meta",type=Path,default=HERE/"arrow-inputs.json")
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args()
    if args.pack:
        pack(args)
    results=score(args.data,args.meta)
    args.out.write_text(json.dumps(results,indent=2,ensure_ascii=False)+"\n")
    print({k:v for k,v in results.items() if k!="cases"})

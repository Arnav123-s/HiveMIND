"""Measure candidate-constrained and direct quantity rules with equal one-wave-delayed feedback."""
import argparse
from hashlib import sha256
import json
from pathlib import Path

from quantity import QuantityChooser
from route import HERE, Members, pair, read_confirmation, word_digest


def summary(rows):
    before = [r["incumbent"] == r["answer"] for r in rows]
    return {method: pair(before, [r[method] == r["answer"] for r in rows]) for method in ("incumbent", "chooser", "direct")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel", type=Path)
    parser.add_argument("--cache", type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    if bool(args.panel) != bool(args.cache):
        parser.error("pass --panel and --cache together")
    members = Members()
    s = members.study
    selector = QuantityChooser()
    for i in members.training:
        r = s.rows[i]
        selector.add(r.domain, r.question, r.label.casefold())
    old = sorted(members.historical, key=lambda i: word_digest("router-waves-1:" + s.rows[i].question))
    waves = [[(members.archived(i), s.rows[i].label.casefold()) for i in old[j:j+12]] for j in range(0,len(old),12)]
    if args.panel:
        waves.append(read_confirmation(members, args.panel, args.cache))
    assessments = []
    history = []
    for number, batch in enumerate(waves, 1):
        decisions = [selector.predict(req) for req, _ in batch]
        cutoff = word_digest(json.dumps(decisions))
        retained = [selector.predict(req)[0] == label for req,label,_ in history]
        rows = []
        for (req, label), (selected, direct, value) in zip(batch, decisions, strict=True):
            rows.append(dict(key=req.key, domain=req.domain, incumbent=req.words[0], answer=label,
                             chooser=selected, direct=direct, supported_quantity=value))
            history.append((req,label,selected == label))
        prior = [initial for _,_,initial in history[:-len(rows)]]
        assessments.append(dict(wave=number, cutoff=cutoff, scores=summary(rows), rows=rows,
                                replay_earlier=pair(prior, retained)))
        for req,label in batch:
            selector.add(req.domain,req.question,label)
    full = [row for stage in assessments[:4] for row in stage["rows"]]
    result=dict(source_sha256=sha256((HERE/"quantity.py").read_bytes()).hexdigest(),
                protocol_sha256=sha256((HERE/"quantity-protocol.md").read_bytes()).hexdigest(),
                known=summary(full), waves=assessments)
    args.out.write_text(json.dumps(result, indent=2)+"\n")
    print(result["known"])
    if args.panel:
        print("fresh",assessments[-1]["scores"])


if __name__ == "__main__":
    main()

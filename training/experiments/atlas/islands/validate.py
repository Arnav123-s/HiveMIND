"""External calibration against the 18 previously recorded native primary checks and their original adapters."""
import json

from run import Study, HEAD, HERE, REPORT, np
from training import domain_engram


def main():
    study = Study()
    legacy = json.loads((REPORT / "results.json").read_text())
    states = np.load(REPORT / "training-states.npz")
    edits = {}
    for d in study.domains:
        ids, a, short_b, _ = domain_engram.fit(states[d], states[d + "_tokens"])
        b = np.zeros((len(study.tokens), short_b.shape[1]), np.float32)
        b[np.searchsorted(study.tokens, ids)] = short_b
        edits[d] = {HEAD: (a.astype(np.float32), b)}
    raw = study.score(study.empty, detail=True)["cases"]
    adapted = study.score(edits, by_domain=True, detail=True)["cases"]
    pairs = []
    for zero, active in zip(raw, adapted, strict=True):
        if zero["split"] != "anchor":
            continue
        key = zero["key"]
        reported = legacy["domain"][zero["domain"]]["validation"]["cases"][int(key.split("-")[-1])]
        pairs.append(dict(key=key, bare_replay=zero["token"], bare_native=reported["before_token"],
                          edit_replay=active["token"], edit_native=reported["after_token"]))
    result = dict(base_sha256=legacy["base_sha256"], native_runtime=legacy["runtime_commit"],
                  total=len(pairs), bare_exact=sum(p["bare_replay"] == p["bare_native"] for p in pairs),
                  edit_exact=sum(p["edit_replay"] == p["edit_native"] for p in pairs), pairs=pairs)
    print(result["bare_exact"], result["edit_exact"], result["total"])
    (HERE / "calibration.json").write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()

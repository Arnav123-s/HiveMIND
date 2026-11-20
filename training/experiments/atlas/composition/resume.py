"""Resume the frozen native composition score with a bounded HTTP request per arm."""
import argparse
import ast
from hashlib import sha256
import json
from pathlib import Path
import time
from urllib.error import URLError
from urllib.request import Request, urlopen

from run import FACTORS, LABELS, SYSTEM, native, panel, write

ARMS = {"base": {}, "joint": {"joint": 1}, **{f: {f: 1} for f in FACTORS},
        "three_mean": dict.fromkeys(FACTORS, 1/3), "three_sum": dict.fromkeys(FACTORS, 1)}
WEIGHT_DIGESTS = {
    "joint": "1fb2d47836aadb2ee97093be27617c8ae49b56f6eb78e05dabf0475e70a65cc9",
    "source": "c0d2205aeaf90c875f438df9d10b35aa6395a224b5f630b4756efbf708f2e3ef",
    "threshold": "e40870c187cdb63062587b39452d2ac413b0f53183a06218d36de4fec307ead3",
    "format": "fbbf7dc63ad9a249f30ae45931f2805f376a63bef90320fab48be5d31fe6f27c",
}


def sha(path):
    return sha256(path.read_bytes()).hexdigest()


def request(url, route, body=None):
    req = Request(url + route, data=None if body is None else json.dumps(body).encode(),
                  headers={"Content-Type": "application/json", "Connection": "close"})
    try:
        with urlopen(req, timeout=120 if route == "/v1/chat/completions" else 12) as response:
            return json.load(response)
    except (TimeoutError, URLError, ConnectionError) as exc:
        raise ConnectionError(f"{req.get_method()} {route}: {exc}") from exc


def probe(url, row, arm):
    active = ARMS[arm]
    before = request(url, "/lora-adapters")
    if {Path(x["path"]).stem for x in before} != set(WEIGHT_DIGESTS) or len(before) != len(WEIGHT_DIGESTS):
        raise ValueError("Invalid adapter manifest")
    request(url, "/lora-adapters", [{"id": x["id"], "scale": active.get(Path(x["path"]).stem,0)} for x in before])
    actual = request(url, "/lora-adapters")
    scales = {Path(x["path"]).stem: x["scale"] for x in actual}
    if set(scales) != set(WEIGHT_DIGESTS) or any(abs(v-active.get(k,0)) > 1e-6 for k,v in scales.items()):
        raise ValueError("Scale readback differs")
    result = request(url, "/v1/chat/completions", {
        "messages": native._messages(row), "max_tokens": 1, "temperature": 0, "seed": 221,
        "cache_prompt": True, "chat_template_kwargs": {"enable_thinking": False}})
    return result["choices"][0]["message"]["content"], scales, result.get("usage")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for arg in ("model","runtime","weights","checkpoint","out"):
        p.add_argument("--"+arg,type=Path,required=True)
    p.add_argument("--original",type=Path,default=Path(__file__).with_name("interrupted.log"))
    p.add_argument("--threads",type=int,default=2)
    args = p.parse_args()
    weights = {k:args.weights/(k+".gguf") for k in WEIGHT_DIGESTS}
    if {k:sha(v) for k,v in weights.items()} != WEIGHT_DIGESTS:
        raise ValueError("Requires the four original fitted adapters")
    model_hash = native._base_hash(args.model,args.model.stat().st_size)
    if model_hash != native.T80_SHA256:
        raise ValueError("Wrong base model")
    runtime_hash = sha(args.runtime)
    train = [r for r in panel() if r["phase"]=="train"]
    test = [r for r in panel() if r["phase"]=="test"]
    original = {}
    for line in args.original.read_text().splitlines():
        name, values = line.split(" ",1)
        if name in original or name not in {r["id"] for r in test}:
            raise ValueError("Unexpected original ID")
        values = ast.literal_eval(values)
        if list(values) != list(ARMS) or any(not isinstance(v,str) for v in values.values()):
            raise ValueError("Unexpected original arms")
        original[name] = values
    # Complete the original missing rows first, then perform an independent readback of every original.
    ordered = [r for r in test if r["id"] not in original]+[r for r in test if r["id"] in original]
    binding = sha256(json.dumps([panel(),ARMS,WEIGHT_DIGESTS,model_hash,runtime_hash,args.threads,
                                 sha(args.original)],sort_keys=True).encode()).hexdigest()
    events = [json.loads(line) for line in args.checkpoint.read_text().splitlines()] if args.checkpoint.exists() else []
    if any(e.get("binding") != binding for e in events):
        raise ValueError("Checkpoint belongs to another study/configuration")
    done = {(e["id"],e["arm"]):e for e in events if "reply" in e}
    tasks = [(r,a) for r in ordered for a in ARMS if (r["id"],a) not in done]
    errors = 0

    def save(entry):
        entry["binding"] = binding
        with args.checkpoint.open("a") as f:
            print(json.dumps(entry,ensure_ascii=False),file=f,flush=True)
        events.append(entry)

    while tasks:
        with native._server(args.model,args.runtime,args.threads,edits=weights.values()) as url:
            while tasks:
                row, arm = tasks[0]
                start = time.monotonic()
                try:
                    reply, scales, usage = probe(url,row,arm)
                except (TimeoutError,URLError,ConnectionError) as exc:
                    save(dict(id=row["id"],arm=arm,error=str(exc),seconds=round(time.monotonic()-start,3)))
                    errors += 1
                    if errors > 6:
                        raise
                    print("Restarting after transport failure",row["id"],arm,str(exc),flush=True)
                    break
                e=dict(id=row["id"],arm=arm,reply=reply,scales=scales,usage=usage,
                       seconds=round(time.monotonic()-start,3))
                save(e)
                done[(row["id"],arm)] = e
                tasks.pop(0)
                if arm=="three_sum":
                    print(row["id"],{a:done[(row["id"],a)]["reply"] for a in ARMS},flush=True)
    trials, diff = [], []
    for r in test:
        measured = {a:done[(r["id"],a)]["reply"] for a in ARMS}
        main = original.get(r["id"],measured)
        for arm in ARMS:
            if main[arm] != measured[arm]:
                diff.append(dict(id=r["id"],arm=arm,original=main[arm],replay=measured[arm]))
        trials.append(dict(id=r["id"],prompt=r["prompt"],expected=r["answer"],unseen=r["unseen"],replies=main,
                           source="original" if r["id"] in original else "continuation"))
    scores = {group:{arm:sum(t["replies"][arm].strip()==t["expected"] for t in trials if t["unseen"]==u)
                     for arm in ARMS} for group,u in (("new_combinations",True),("familiar_combinations",False))}
    result = dict(system=SYSTEM,training_cases=train,trials=trials,scores=scores,arms=ARMS,threads=args.threads,
                  model_sha256=model_hash,runtime_sha256=runtime_hash,weights_sha256=WEIGHT_DIGESTS,
                  original_complete_rows=len(original),original_log_sha256=sha(args.original),replay_differences=diff,
                  checkpoint_sha256=sha(args.checkpoint),attempts=len(events),timeouts=sum("error" in e for e in events),
                  summed_http_probe_seconds=round(sum(e["seconds"] for e in events),3),
                  fit_wall_seconds=None)
    write(args.out,result)
    print(scores,flush=True)


if __name__ == "__main__":
    main()

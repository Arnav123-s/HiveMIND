"""Independently check the steering artifacts and summarize the four fixed arms."""
import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
from statistics import median
import zipfile

HERE=Path(__file__).resolve().parent


def canonical_logprobs(row):
    info=row["token_logprobs"]
    return {p["token"]:p["logprob"] for p in info["content"][0]["top_logprobs"]}


def check(result, study):
    gold = [6*8-7==41, 5+12-9==9, 31//16==32//16, 18/24==.75, 0<49<100, 2**3==4, .1*1000==10, 22-17+1==6]
    assert [key for _,key in study["tasks"]]==["A" if truth else "B" for truth in gold]
    assert Counter(key for _, key in study["tasks"]) == {"A":4,"B":4}
    assert result["identity"]["benchmark_sha256"]==sha256((HERE/"study.json").read_bytes()).hexdigest()
    assert set(result["arms"])=={"bare","reminder","positive","negative"}
    assert result["layer_range"]==[20,30] and all(0.9999<=n<=1.0001 for n in result["norms"].values())
    scores={}
    for arm,expected_scale in (("bare",0),("reminder",0),("positive",1),("negative",-1)):
        r=result["arms"][arm]
        assert len(r["rows"])==8
        for (task,key),row in zip(study["tasks"],r["rows"]):
            assert (task,key)==(row["task"],row["key"])
            assert row["scale"]==expected_scale and row["vector_sha256"]==result["vector_sha256"]
            assert row["usage"]["completion_tokens"]==1
            assert row["usage"]["prompt_tokens_details"]["cached_tokens"]==0
            assert (row["token"].strip()==key)==row["correct"]
        assert r["correct"]==sum(x["correct"] for x in r["rows"])
        base=result["arms"]["bare"]["rows"]
        scores[arm]=dict(correct=r["correct"],misses=[i for i,x in enumerate(r["rows"]) if not x["correct"]],
                         pred_A=sum(x["token"].strip()=="A" for x in r["rows"]),
                         pred_B=sum(x["token"].strip()=="B" for x in r["rows"]),
                         false_to_true=sum(not b["correct"] and y["correct"] for b,y in zip(base,r["rows"])),
                         true_to_false=sum(b["correct"] and not y["correct"] for b,y in zip(base,r["rows"])),
                         changed_top_five=sum(canonical_logprobs(b)!=canonical_logprobs(y) for b,y in zip(base,r["rows"])),
                         seconds_sum=round(sum(x["seconds"] for x in r["rows"]),3),
                         seconds_median=round(median(x["seconds"] for x in r["rows"]),3))
    return scores


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--results",type=Path,default=HERE/"results.json")
    p.add_argument("--archive",type=Path,default=HERE/"native-evidence.zip")
    a=p.parse_args()
    r=json.loads(a.results.read_text())
    with zipfile.ZipFile(a.archive) as f:
        for name,digest in dict(r["log_sha256"],**{"verification.gguf":r["vector_sha256"]}).items():
            assert sha256(f.read(name)).hexdigest()==digest
        for outcome in r["arms"].values():
            for row in outcome["rows"]:
                cmd=json.loads(f.read(row["server_log"]).splitlines()[0])
                assert "--no-graph-reuse" in cmd
                if row["scale"]:
                    i=cmd.index("--control-vector-scaled")
                    assert Path(cmd[i+1]).name=="verification.gguf" and int(cmd[i+2])==row["scale"]
                    j=cmd.index("--control-vector-layer-range")
                    assert cmd[j+1:j+3]==["20","30"]
                else:
                    assert "--control-vector-scaled" not in cmd
    print(json.dumps(check(r,json.loads((HERE/"study.json").read_text())),indent=2))

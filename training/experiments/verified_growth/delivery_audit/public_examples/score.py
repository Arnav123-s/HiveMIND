"""Independent grading of already sealed file proposals using the task's original hidden draws in WASI."""
import argparse
from collections import Counter
import inspect
import json
import os
from pathlib import Path
import random
import tempfile
import time
from unittest.mock import patch
from zipfile import ZipFile

from .replay import digest, HERE, Meter


SEALED = {"stock":"9b2e0fabb9172050cfe33cb492283e91069457e71d67a6717d3c8ee9505fe5ab",
          "alternative":"a2fbab51f129364ce100db8bbc0c2d761fb8ab2f9369f3abeaad67edb188f05c"}


def score(guest, proposal, task_id, prompt, module_name):
    from training.kinds import h_module
    seed, ordinal = task_id[1:].split("_")
    generated = h_module.make(random.Random(f"{seed}:h_module:{int(ordinal)}:0"))
    assert prompt == generated[2].strip(), "The archived question must reproduce byte-for-byte"
    check = generated[3]
    variables = inspect.getclosurevars(check).nonlocals
    hidden = {}

    def in_guest(path, fns, seed):
        src = path.read_text()
        dispatch = "\n\ndef solve(x):\n    return {" + ", ".join(f"{n!r}: {n}" for n, *args in fns) + "}[x[0]](*x[1])\n"
        rng = random.Random(f"hidden:{seed}")
        examples = [(n, args, ref(*args)) for n, _, ref, draw in fns for args in (draw(rng) for _ in range(25))]
        outputs, fuel, seconds = guest.run(src + dispatch, [(n, args) for n,args,ref in examples])
        matches = ["value" in out and out["value"] == expected for out, (_,args,expected) in zip(outputs,examples,strict=True)]
        hidden.update(passed=sum(matches), total=len(matches), fuel=fuel, guest_seconds=seconds)
        return all(matches), f"{sum(matches)} of {len(matches)} hidden tests pass"

    outcome = proposal["outcome"]
    assert set(outcome["files"]) == {module_name}
    with tempfile.TemporaryDirectory() as home, patch.object(h_module,"_hidden",in_guest):
        root = Path(home)
        file = root / "work" / module_name
        file.parent.mkdir()
        file.write_text(outcome["files"][module_name]["source"])
        assert digest(file.read_bytes()) == outcome["module_sha256"]
        passed, explanation = check(root, outcome["text"])
    exact = outcome["text"] == "\n".join(map(str,variables["want"]))
    return dict(passed=passed,exact_requested_text=exact, explanation=explanation,hidden=hidden,
                module_sha256=outcome["module_sha256"])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--sdk",type=Path,required=True)
    p.add_argument("--archives",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args()
    os.environ["RAYON_NUM_THREADS"]="1"
    os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
    docs={}
    for stage,sha in SEALED.items():
        data=(HERE/f"{stage}.json").read_bytes()
        assert digest(data)==sha
        docs[stage]=json.loads(data)
    started,cpu=time.monotonic(),time.process_time()
    guest=Meter(args.sdk)
    result=[]
    counts=Counter()
    for current,baseline in zip(docs["alternative"]["rows"],docs["stock"]["rows"],strict=True):
        assert (current["archive_id"],current["task"])==(baseline["archive_id"],baseline["task"])
        assert baseline.get("proposal",{}).get("outcome",{}).get("status","abstained")=="abstained"
        with ZipFile(args.archives / f"{current['archive_id']}.zip") as z:
            grade_path = current["archived_path"].removesuffix("members/TASK.md")+"exam.json"
            official=json.loads(z.read(grade_path)) if grade_path in z.namelist() else None
            prompt=z.read(current["archived_path"]).decode().strip()
        assert digest(prompt.encode())==current["prompt_sha256"]
        original = None if official is None else official["ok"]
        counts[str(original)]+=1
        entry=dict(archive_id=current["archive_id"],gate=current["gate"],task=current["task"],filename=current["filename"],
                   prior=current["prior"],original_ok=original)
        for k in ("proposal","lookup_alone","lookup_with_workers"):
            if k in current and current[k]["outcome"]["status"]=="answered":
                entry[k]=score(guest,current[k],current["task"],prompt,current["filename"])
        result.append(entry)
    doc=dict(decisions_sha256=SEALED, rows=result, archived_original_counts=counts,
             estimated_new_correct=sum(r.get("proposal",{}).get("passed")==True and r["original_ok"]==False for r in result),
             lookup_singletons_passing=sum(r.get("lookup_alone",{}).get("passed")==True for r in result),
             meter=dict(calls=len(guest.calls),input_rows=sum(c["inputs"] for c in guest.calls),
                        fuel=sum(c["fuel"] for c in guest.calls),guest_seconds=sum(c["seconds"] for c in guest.calls),
                        total_wall_seconds=time.monotonic()-started,process_cpu_seconds=time.process_time()-cpu))
    args.out.write_text(json.dumps(doc,indent=2)+"\n")
    print(doc["archived_original_counts"],doc["estimated_new_correct"],doc["lookup_singletons_passing"],doc["meter"])


if __name__=="__main__":
    main()

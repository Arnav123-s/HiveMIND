"""Extract durations only. Do not copy verdicts, answer text or grades."""
import argparse
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
import re
from zipfile import ZipFile


HERE = Path(__file__).resolve().parent
MANIFEST = HERE.parents[1] / "atlas/pulse/artifacts.json"


def seconds(ts):
    return int(datetime.fromisoformat(ts.replace('Z', '+00:00')).timestamp())


def extract(zips, job_files):
    manifests = json.loads(MANIFEST.read_bytes())
    existing = json.loads((HERE.parent / "budget/jobs.json").read_bytes())["runs"]
    generations = {}
    for generation in ("g50", "g51", "g52"):
        jobs = [json.loads(line) for line in (job_files / (generation + "-schedule-jobs.jsonl")).read_text().splitlines()]
        expected = {j["id"]:(j["started_at"],j["completed_at"]) for j in existing.get(generation,{}).get("jobs",[])}
        gate = {}
        for j in jobs:
            arm, seat = re.fullmatch(r'gate \((before|after), (\d+)\)', j["name"]).groups()
            if generation in existing:
                assert expected[j["id"]] == (j["started_at"],j["completed_at"])
            stages = {}
            for s in j["steps"]:
                if s["conclusion"] == 'skipped':
                    continue
                for prefix,key in [('A fresh exam','fresh'),('The fixed held-out exam','held'),('The talk exam','talk'),('Three plain messages','smoke')]:
                    if s['name'].startswith(prefix):
                        stages[key] = seconds(s['completed_at'])-seconds(s['started_at'])
            item = next(a for a in manifests if a['generation']==generation and a['name']==f'gate-work-{arm}-{seat}')
            archive = zips / (str(item["id"])+".zip")
            assert sha256(archive.read_bytes()).hexdigest() == item["sha256"]
            with ZipFile(archive) as z:
                tasks = {}
                for name in z.namelist():
                    if name.endswith('/exam.json'):
                        row=json.loads(z.read(name))
                        assert row['id'] not in tasks
                        tasks[row['id']]=row['seconds']
            gate[arm+seat]=dict(job=j['id'],start=seconds(j['started_at']),end=seconds(j['completed_at']),
                                stages=stages,tasks=tasks,artifact=item['id'])
        assert len(gate)==16
        for arm in ('before','after'):
            cohort=[t for seat,x in gate.items() if seat.startswith(arm) for t in x['tasks']]
            assert len(cohort)==len(set(cohort))==94
            assert sum(t.startswith('x_') for t in cohort)==30
        generations[generation]=gate
    return generations


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--zips',type=Path,required=True)
    p.add_argument('--job-files',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    args=p.parse_args()
    args.out.write_text(json.dumps(extract(args.zips,args.job_files),indent=1,sort_keys=True)+'\n')

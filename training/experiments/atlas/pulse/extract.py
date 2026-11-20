"""Reconstruct worker text and timing, and keep the assessment ledger out of the policy inputs."""
import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import re
import random
import subprocess
import sys
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))
from training import exam

# The two live-source kinds in the plan, h_since and h_two, actually require network lookups.
TEXT_KINDS = set('m_days m_weekday m_percent m_units m_know m_follow m_steps m_table m_translate m_summary '
                 'h_search h_sim h_txt_ini h_txt_words h_txt_access h_txt_contacts h_txt_sentences'.split())


def offline_suite(seed):
    """Reproduce the mixed exam's shuffle and local draws without contacting any live task maker."""
    rows = []
    for hard, code in ((False, 'e'), (True, 'h')):
        makers = exam.kinds.makers(hard=hard)
        random.Random(seed).shuffle(makers)
        past = set()
        for index, maker in enumerate(makers[:4]):
            tid = f'{code}{seed}_{index:02d}'
            if maker.__name__ not in TEXT_KINDS:
                rows.append((tid, '', '', None, None))
                continue
            for attempt in range(8):
                field, kind, prompt, check = exam._made(maker, f'{seed}:{maker.__name__}:{index}:{attempt}')
                if prompt not in past:
                    break
            past.add(prompt)
            rows.append((tid, field, kind, prompt, check))
    return rows


def dump(name, data):
    raw = (json.dumps(data, ensure_ascii=False, separators=(',', ':')) + '\n').encode()
    (HERE / name).write_bytes(gzip.compress(raw, mtime=0))


def member_text(z, names, home, number, prefix):
    if prefix == 'no answer':
        return ''
    if len(prefix) < 300:
        return prefix
    # The board records only the first 300 characters. Require a unique actual full stdout in this seat.
    result = set()
    end = re.compile(rf'/\.member{number}_\d+\.py\.out$')
    for name in names:
        if name.startswith(home + '/members/') and end.search(name):
            value = z.read(name).decode('utf-8', errors='replace').strip()[-3000:]
            if value.startswith(prefix):
                result.add(value)
    return next(iter(result)) if len(result) == 1 else None


def arm_records(archive, seed, tasks, arm, inventory):
    rows = {}
    with zipfile.ZipFile(archive) as z:
        names = set(z.namelist())
        for tid, _, _, prompt, check in tasks:
            if check is None:
                continue
            home = f'exam_{seed}_mixed/{tid}'
            base = home + '/members/'
            if home + '/exam.json' not in names or base + 'events.jsonl' not in names:
                inventory['missing_arm_task_receipt'] += 1
                continue
            if base + 'TASK.md' not in names or z.read(base + 'TASK.md').decode().strip() != prompt.strip():
                inventory['nonidentical_regenerated_prompt_in_arm'] += 1
                continue
            meta = json.loads(z.read(home + '/exam.json'))
            events = [json.loads(line) for line in z.read(base + 'events.jsonl').splitlines() if line.strip()]
            verdicts = {row['member']:row for row in meta['members']}
            seats, grades = {}, {}
            last = None
            for event in events:
                if event['agent'] == 'hive' and event['kind'] == 'seats':
                    last = event['ts']
                match = re.fullmatch(r'member(\d+)', event['agent'])
                if not match or event['kind'] != 'answer':
                    continue
                number = int(match[1])
                answer = member_text(z, names, home, number, event['msg'])
                duration = round(event['ts'] - last, 3) if last is not None else None
                last = event['ts']
                if answer is None or number not in verdicts:
                    inventory['incomplete_or_unattributable_seat'] += 1
                    continue
                seats[str(number)] = dict(arm=arm, seat=number, who=verdicts[number]['who'], answer=answer, seconds=duration)
                grades[str(number)] = verdicts[number]['ok']
            report = z.read(home + '/REPORT.md').decode() if home + '/REPORT.md' in names else ''
            delivered = bool(report.strip() and '## How it was checked' in report and
                             ('two gave the same values' in report or 'two of them agreed' in report))
            rows[tid] = dict(seats=seats,grades=grades,official_pass=bool(meta['ok']), report=report,
                             released=delivered, wall=meta['seconds'])
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--raw', type=Path, default=HERE / '.raw')
    parser.add_argument('--fetch', action='store_true', help='download missing public artifact ZIPs with authenticated gh')
    args=parser.parse_args()
    manifest=json.loads((HERE/'artifacts.json').read_bytes())
    by_gen={}
    for artifact in manifest:
        path=args.raw/f"{artifact['id']}.zip"
        if not path.exists() and args.fetch:
            args.raw.mkdir(parents=True,exist_ok=True)
            payload=subprocess.check_output(['gh','api',f"repos/Arnav123-s/HiveMIND/actions/artifacts/{artifact['id']}/zip"])
            if hashlib.sha256(payload).hexdigest()!=artifact['sha256']:
                raise ValueError(f"wrong ZIP digest for {artifact['id']}")
            path.write_bytes(payload)
        if hashlib.sha256(path.read_bytes()).hexdigest()!=artifact['sha256']:
            raise ValueError(f"wrong ZIP digest for {artifact['id']}")
        _,_,arm,shard=artifact['name'].split('-')
        by_gen.setdefault((artifact['generation'],int(shard)),{})[arm]=path
    public,assess,cohort=[],{},[]
    seen=set()
    for (generation,shard),paths in sorted(by_gen.items()):
        # Every original gate has 4 basic and 4 hard questions.
        seed=20_000_000+10*int(generation[1:])+shard
        tasks=offline_suite(seed)
        inventory=Counter()
        arms={arm:arm_records(path,seed,tasks,arm,inventory) for arm,path in paths.items()}
        for tid,field,kind,prompt,check in tasks:
            row_id=f'{generation}/{tid}'
            inventory['fresh_exam_tasks']+=1
            if check is None:
                inventory['excluded_family']+=1
                continue
            if prompt in seen:
                inventory['duplicate_prompt']+=1
                continue
            seen.add(prompt)
            inventory['unique_text_audience']+=1
            if not all(tid in arms[arm] for arm in ('after','before')):
                inventory['censored_task']+=1
                continue
            after,before=arms['after'][tid],arms['before'][tid]
            if not all(str(i) in arm['seats'] for arm in (after,before) for i in (1,2)):
                inventory['censored_task']+=1
                continue
            inventory['four_recorded_seats']+=1
            seats=[arm['seats'][str(i)] for arm in (after,before) for i in (1,2)]
            public.append(dict(id=row_id,generation=generation,seed=seed,tid=tid,kind=check.maker,field=field,
                               prompt=prompt,rseed=check.rseed,seats=seats))
            assess[row_id]=dict(recorded_seat_verdicts=[arm['grades'][str(i)] for arm in (after,before) for i in (1,2)],
                                actual_after=dict(ok=after['official_pass'],report=after['report'],released=after['released'],
                                                  wall_seconds=after['wall'],completed_workers=len(after['seats'])))
        cohort.append(dict(generation=generation,shard=shard,**dict(inventory)))
    dump('panels.json.gz',public)
    dump('assessment.json.gz',assess)
    (HERE/'cohort.json').write_text(json.dumps(cohort,indent=1)+'\n')
    print(len(public),'paired rows')

if __name__=='__main__':
    main()

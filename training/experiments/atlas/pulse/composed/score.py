"""Replay four frozen choices on the same archived trajectories; no generation or model loading."""
import argparse
from collections import Counter
from functools import lru_cache
import gzip
from hashlib import sha256
import json
from pathlib import Path
import random
import re
import sys
from zipfile import ZipFile

HERE = Path(__file__).resolve().parent
PULSE = HERE.parent
MODULES = PULSE.parent / 'module_recovery'
ROOT = PULSE.parents[3]
sys.path[:0] = [str(ROOT), str(PULSE), str(MODULES)]
from extract import member_text
from one_checked.certificate import certify, expected
from recover import REQUEST, extract
from team.deliverables import wanted
from training import exam

COHORT = ('g50', 'g51', 'g52')
METHODS = ('baseline', 'first_certificate', 'recover', 'both', 'calculator', 'calculator_recover')
CERT_SHA = 'b9a526cef25260b2b567122f4f861138c1ce45f780cf06ca84390f511ee03157'
REC_SHA = 'e69c2add64c925d14f0189b845a5c48d118c34fddc7baea13cb1a5ef9b7f1946'


def digest(data):
    return sha256(data).hexdigest()


@lru_cache(maxsize=64)
def makers(seed, hard):
    entries = exam.kinds.makers(hard=hard)
    random.Random(seed).shuffle(entries)
    return tuple(entry.__name__ for entry in entries[:4])


def original_status(report, meta):
    agreed = ('## How it was checked' in report and
              ('two gave the same values' in report or 'two of them agreed' in report))
    if agreed:
        return 'correct' if meta['ok'] else 'wrong'
    if meta['ok'] or not (report.strip().lower().startswith(('not confirmed', 'no member')) or
                          (not report and 'timed out' in meta['note'])):
        raise ValueError('unrecognized outcome for ' + meta['id'])
    return 'withheld'


def rebuild(archives):
    manifest = json.loads((PULSE / 'artifacts.json').read_text())
    ref = json.loads((MODULES / 'results.json').read_text())
    recovery = {(r['generation'],r['id']): r for r in ref['rows']}
    result = []
    for item in manifest:
        g = item['generation']
        if g not in COHORT or '-after-' not in item['name']:
            continue
        zip_path = archives / (str(item['id']) + '.zip')
        if digest(zip_path.read_bytes()) != item['sha256']:
            raise ValueError(f"archive {item['id']} failed SHA-256")
        with ZipFile(zip_path) as z:
            names = set(z.namelist())
            for path in sorted(names):
                match = re.fullmatch(r'(exam_(\d+)_mixed/([eh]\d+_\d+))/exam\.json', path)
                if not match:
                    continue
                home, seed, tid = match[1], int(match[2]), match[3]
                meta = json.loads(z.read(path))
                assert meta['id'] == tid and seed // 10 == (20_000_000 + 10*int(g[1:])) // 10
                prefix = home + '/members/'
                prompt = z.read(prefix + 'TASK.md').decode().strip()
                report_path = home + '/REPORT.md'
                report = z.read(report_path).decode() if report_path in names else ''
                events = [json.loads(line) for line in z.read(prefix+'events.jsonl').splitlines()]
                starts = {int(e['agent'][6:]) for e in events if re.fullmatch(r'member\d+', e['agent'])}
                ends = [int(e['agent'][6:]) for e in events if e['kind']=='answer' and re.fullmatch(r'member\d+', e['agent'])]
                seats = {m['member']: m for m in meta['members']}
                assert starts == set(ends) == set(seats) and len(ends) == len(seats)
                first = next((member_text(z,names,home,1,e['msg']) for e in events if
                              e['agent']=='member1' and e['kind']=='answer'), None)
                kind = makers(seed,tid.startswith('h'))[int(tid.split('_')[1])]
                files = wanted(prompt)
                if kind == 'm_csv':
                    assert prompt.startswith('Make a CSV ')
                    files = ['(unnamed CSV)']
                row = dict(generation=g,id=tid,artifact=item['id'],kind=kind,files=files,prompt=prompt,first=first,
                           original=original_status(report,meta),workers=list(sorted(seats)),
                           first_archived_ok=seats.get(1,{}).get('ok'),exam_sha256=digest(z.read(path)))
                rerun = recovery[(g,tid)]
                assert meta['ok'] == rerun['original']
                receipt = rerun.get('receipt')
                if receipt:
                    assert REQUEST.fullmatch(prompt) and report.casefold().strip().startswith('not confirmed')
                    trials = receipt['trials']
                    for trial in trials:
                        raw = z.read(prefix+trial['program'])
                        assert digest(extract(raw.decode()).encode()) == trial['sha256']
                    row['wasi'] = dict(batches=len(trials),guest_seconds=sum(t['seconds'] for t in trials),
                                       fuel=sum(t['fuel'] for t in trials))
                    if receipt['delivered']:
                        worker = int(re.search(r'member(\d+)_',receipt['selected'])[1])
                        assert worker in seats and receipt['sha256'] == digest((MODULES/g/tid/'durations.py').read_bytes())
                        row['recovery'] = dict(selected_member=worker,selected_path=receipt['selected'],
                            raw_program_sha256=digest(z.read(prefix + receipt['selected'])),
                            module_sha256=receipt['sha256'],official=rerun['official'],fresh=rerun['fresh_correct'],
                            fresh_total=ref['independent_cases'])
                assert bool(row.get('recovery')) == rerun['recovered']
                result.append(row)
    assert len({(r['generation'],r['id']) for r in result}) == len(result) == 192
    return sorted(result,key=lambda r:(r['generation'],r['id']))


def independent_check(row, text):
    # Remake only the arithmetic/calendar task, after the literal output was selected.
    # This never calls a network task maker or runs an archived worker program.
    tid = row['id']
    seed, idx = map(int,tid[1:].split('_'))
    kind = row['kind']
    for draw in range(8):
        candidate = exam.remake(kind,f'{seed}:{kind}:{idx}:{draw}')
        if candidate and candidate[2].strip() == row['prompt']:
            return bool(candidate[3](None,text)[0])
    raise ValueError('cannot reproduce exact request ' + tid)


def policies(row):
    prompt, first = row['prompt'], row['first']
    contract = expected(prompt)
    certified = certify(prompt,first)
    result = {}
    base, workers = row['original'], len(row['workers'])
    corrected = row.get('recovery')
    if corrected:
        assert corrected['official']['okay'] and corrected['fresh'] == corrected['fresh_total']
        assert corrected['selected_member'] in row['workers']
    first_status = calculator_status = None
    if certified:
        assert 1 in row['workers']
        first_ok = independent_check(row, first)
        assert first_ok == row['first_archived_ok']
        first_status = 'correct' if first_ok else 'wrong'
    if contract:
        calculator_status = 'correct' if independent_check(row,str(contract[1])) else 'wrong'
    for name in METHODS:
        status, seats, wasi, source = base, workers, 0, 'original'
        if name.startswith('calculator') and contract:
            status, seats, source = calculator_status, 0, 'calculator'
        elif name in ('first_certificate','both') and certified:
            status, seats, source = first_status, 1, 'first_worker'
        elif name in ('recover','both','calculator_recover'):
            wasi = row.get('wasi',{}).get('batches',0)
            if corrected:
                status, source = 'correct','archived_program'
        result[name] = (status,seats,wasi,source)
    return result, contract[0] if contract else None, certified


def score(rows):
    generations = {}
    decisions = []
    for g in COHORT:
        sub = [r for r in rows if r['generation']==g]
        assert len(sub)==64
        counts = {meth: Counter() for meth in METHODS}
        overlaps = 0
        for row in sub:
            results, kind, accepted = policies(row)
            for name,(status,seats,wasi,source) in results.items():
                c = counts[name]
                c[status] += 1
                c['workers'] += seats
                c['wasi_admission_batches'] += wasi
                c['wasi_fuel'] += row['wasi']['fuel'] if wasi else 0
                c['wrong_after_correct'] += int(row['original']=='correct' and status=='wrong')
                c['withheld_after_correct'] += int(row['original']=='correct' and status=='withheld')
                c['new_wrong'] += int(row['original']!='wrong' and status=='wrong')
                if row['files']:
                    c['file_jobs_'+status] += 1
            if kind or row.get('wasi'):
                decisions.append(dict(generation=g,id=row['id'],contract=kind,certified=accepted,
                    first=row['first'] if kind else None,original_workers=len(row['workers']),original=row['original'],
                    recovery=row.get('recovery'),wasi=row.get('wasi'),outcomes=results))
            overlaps += int(accepted and bool(row.get('recovery')))
        generations[g] = dict(overlap_tasks=overlaps, methods=counts)
    return {'generations':generations,'changed_or_applicable_jobs':decisions,
            'checkpoint_sha256':digest((HERE/'checkpoint.json.gz').read_bytes()),
            'certificate_sha256':CERT_SHA,'recovery_results_sha256':REC_SHA,
            'manifest_sha256':digest((PULSE/'artifacts.json').read_bytes())}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rebuild',type=Path,metavar='ZIP_DIRECTORY')
    parser.add_argument('--output',type=Path,default=HERE/'results.json')
    args = parser.parse_args()
    assert digest((PULSE/'one_checked/certificate.py').read_bytes()) == CERT_SHA
    assert digest((MODULES/'results.json').read_bytes()) == REC_SHA
    checkpoint = HERE / 'checkpoint.json.gz'
    if args.rebuild:
        rows = rebuild(args.rebuild)
        checkpoint.write_bytes(gzip.compress(json.dumps(rows,separators=(',',':')).encode(),mtime=0))
    rows = json.loads(gzip.decompress(checkpoint.read_bytes()))
    report = score(rows)
    args.output.write_text(json.dumps(report,indent=1)+'\n')
    for g,r in report['generations'].items():
        print(g,'  |  '.join(f"{name}: {x['correct']}/{x['wrong']}/{x['withheld']} in {x['workers']} seats"
                             for name,x in r['methods'].items()))


if __name__ == '__main__':
    main()

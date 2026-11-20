"""Independent CLI checks for generated projects, exact tiny cases and two WASI bank witnesses."""
import argparse
from collections import defaultdict
import gzip
import hashlib
import json
import os
from pathlib import Path
import random
import re
import subprocess
import sys
import tempfile


HERE = Path(__file__).resolve().parent
WITNESS = [0, 10, 0, 0, 6, 31, 4, 4, 9, 6, 18, 13, 4, 15, 18, 13, 23, 10, 13, 27, 29, 29, 36, 38, 34, 27, 15, 34, 18, 41, 37, 43]


def projects():
    for i in range(60):
        rng = random.Random(912490 + i)
        n = i % 7 if i < 10 else rng.randrange(5, 19)
        cap = [rng.randrange(1, 5) for _ in range(1 + i % 3)]
        permutation = list(range(n))
        if i % 3 == 0:
            permutation.reverse()
        else:
            rng.shuffle(permutation)
        jobs = [None] * n
        for old, new in enumerate(permutation):
            duration = rng.randrange(4 if i < 10 else 8)
            requests = [rng.randint(0, limit) for limit in cap]
            if old % 4 == 0:
                requests[0] = cap[0]
            parents = [permutation[q] for q in range(old) if rng.random() < (0.1, 0.3, 0.6)[i % 3]]
            jobs[new] = [duration, requests, parents]
        yield {'capacity': cap, 'jobs': jobs}


def invalid_projects():
    def project(jobs, cap=None):
        return {'capacity': [2] if cap is None else cap, 'jobs': jobs}
    return {
        'broken_json': '{',
        'wrong_root': '[]',
        'missing_jobs': {'capacity': [1]},
        'nonpositive_capacity': project([], [0]),
        'boolean_capacity': project([], [True]),
        'negative_duration': project([[-1, [1], []]]),
        'fractional_duration': project([[0.5, [1], []]]),
        'boolean_duration': project([[True, [1], []]]),
        'negative_demand': project([[3, [-1], []]]),
        'missing_demand_dimension': project([[3, [], []]]),
        'unfit_resource_request': project([[1, [3], []]]),
        'missing_predecessor': project([[0, [0], [2]]]),
        'negative_predecessor': project([[0, [0], [-1]]]),
        'cyclic_zero_duration': project([[0, [0], [1]], [0, [0], [0]]]),
        'self_cycle': project([[3, [0], [0]]]),
        'excessive_total_duration': project([[1025, [1], []], [1024, [1], []]]),
    }


def feasible(project, starts):
    jobs, capacity = project['jobs'], project['capacity']
    if type(starts) is not list or len(starts) != len(jobs) or any(type(t) is not int or t < 0 for t in starts):
        return None
    ends = [s + job[0] for s, job in zip(starts, jobs)]
    events = defaultdict(lambda: [0] * len(capacity))
    for i, (duration, demand, pred) in enumerate(jobs):
        if any(ends[parent] > starts[i] for parent in pred):
            return None
        if duration:
            for r, units in enumerate(demand):
                events[starts[i]][r] += units
                events[ends[i]][r] -= units
    load = [0] * len(capacity)
    for t in sorted(events):
        for r, change in enumerate(events[t]):
            load[r] += change
            if not 0 <= load[r] <= capacity[r]:
                return None
    return max(ends, default=0)


def exact_small(project):
    jobs, cap = project['jobs'], project['capacity']
    order = []
    while len(order) < len(jobs):
        order.append(next(i for i, job in enumerate(jobs) if i not in order and set(job[2]).issubset(order)))
    for horizon in range(max((j[0] for j in jobs), default=0), 1 + sum(j[0] for j in jobs)):
        remaining = [list(cap) for _ in range(horizon)]
        ends = {}
        def place(at):
            if at == len(order):
                return True
            i = order[at]
            duration, demand, parents = jobs[i]
            for start in range(max((ends[p] for p in parents), default=0), horizon - duration + 1):
                times = range(start, start + duration)
                if any(remaining[t][r] < d for t in times for r, d in enumerate(demand)):
                    continue
                ends[i] = start + duration
                for t in times:
                    for r, d in enumerate(demand):
                        remaining[t][r] -= d
                if place(at+1):
                    return True
                for t in times:
                    for r, d in enumerate(demand):
                        remaining[t][r] += d
                del ends[i]
            return False
        if place(0):
            return horizon
    raise ValueError('serial upper bound violated')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkout', type=Path, default=HERE.parents[3])
    parser.add_argument('--sdk', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    cli = args.checkout.resolve() / 'hive'
    env = {**os.environ, 'HIVE_PYTHON': sys.executable, 'HIVE_BANK': 'off',
           'HIVE_FIELDWORK_SDK': str(args.sdk.resolve()), 'HIVE_TERNARY_BIN': '/nonexistent-qa-llama'}
    generated = list(projects())
    malformed = invalid_projects()
    inputs = json.dumps([generated, malformed, WITNESS], sort_keys=True).encode()
    report = {'panel_sha256': digest(inputs), 'generated': [], 'invalid': {}, 'competitors': {}}
    with tempfile.TemporaryDirectory(prefix='hive-scheduling-qa-') as tmp:
        tmp = Path(tmp)
        def call(project, bank=None):
            path = tmp/'project.json'
            path.write_text(project if type(project) is str else json.dumps(project))
            argv = [str(cli), 'schedule', str(path)]
            if bank is not None:
                argv.extend(['--bank', str(bank)])
            return subprocess.run(argv, cwd=tmp, env=env, capture_output=True, text=True, timeout=45)
        def grade(project, bank=None):
            result = call(project, bank)
            if result.returncode:
                raise ValueError(result.stderr)
            starts = json.loads(result.stdout)
            span = feasible(project, starts)
            header = result.stderr.splitlines()[0]
            receipt = re.fullmatch(r'Makespan (\d+)\. Winner (\S+)\.', header)
            if span is None or not receipt or int(receipt[1]) != span:
                raise ValueError(f'invalid schedule or receipt: {span}, {header}')
            return {'makespan': span, 'winner': receipt[2], 'starts': starts, 'stderr': result.stderr}

        for i, project in enumerate(generated):
            row = grade(project)
            if i < 10:
                row['minimum_by_enumeration'] = exact_small(project)
                if row['makespan'] < row['minimum_by_enumeration']:
                    raise ValueError('inconsistent lower bound')
            report['generated'].append(row)
        for key, project in malformed.items():
            res = call(project)
            report['invalid'][key] = {'exit': res.returncode, 'stdout': res.stdout, 'stderr': res.stderr}
            if res.returncode != 2 or res.stdout.strip():
                raise ValueError(f'{key}: expected rejection, got exit {res.returncode} {res.stdout}')
        archived = json.loads(gzip.decompress((HERE/'evidence.json.gz').read_bytes()))
        fixture = next(row for row in archived['projects'] if row['name'] == 'j301_1.sm')['input']
        if feasible(fixture, WITNESS) != 43 or feasible(fixture, [0]*len(WITNESS)) is not None:
            raise ValueError('invalid test fixture')
        baseline = grade(fixture)
        report['competitors']['baseline'] = baseline
        for label, vector in [('feasible', WITNESS), ('infeasible', [0]*len(WITNESS))]:
            # A deliberately single-instance QA witness tests guest selection, not algorithm generalization.
            bank = tmp/label
            bank.mkdir()
            source = 'def solve(x):\n    return ' + repr(vector)
            sha = digest(source.encode())
            entry = {'task': 'project_schedule', 'description': archived['public']['description'], 'source': source,
                     'digest': sha, 'public': 1, 'validation': 1, 'parents': []}
            (bank/(sha+'.json')).write_text(json.dumps(entry))
            result = grade(fixture, bank)
            report['competitors'][label] = result
            if label == 'feasible' and (result['winner'] != 'bank/'+sha or result['makespan'] >= baseline['makespan']):
                raise ValueError(f'shorter feasible witness not selected: {result}')
            if label == 'infeasible':
                if 'Skipped bank/' + sha not in result['stderr']:
                    raise ValueError(f'invalid fixture was not considered: {result}')
                if result['starts'] != baseline['starts'] or result['winner'] != baseline['winner']:
                    raise ValueError(f'constraint violation changed winning plan: {result}')
    args.output.write_text(json.dumps(report, indent=2)+'\n')
    print(f"{len(generated)} independently feasible, {len(malformed)} inputs rejected, both WASI witnesses checked.")


if __name__ == '__main__':
    main()

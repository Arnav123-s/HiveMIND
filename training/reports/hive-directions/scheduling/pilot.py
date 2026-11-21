"""Compare three simple serial schedule-generation policies on five development cases.

Use --archive FILE and --solutions FILE to read downloaded official PSPLIB data.
With no flags, fetch them into memory. Only Python's standard library is needed.
"""
import argparse
from dataclasses import dataclass
from functools import lru_cache
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import random
import re
import time
from urllib.request import Request, urlopen
from zipfile import ZipFile


ARCHIVE_URL = 'https://www.om-db.wi.tum.de/psplib/download_dataset.php?set=j30&mode=sm&format=zip'
SOLUTIONS_URL = 'https://www.om-db.wi.tum.de/psplib/download_merged.php?set=j30&mode=sm'


def read_data(path, url):
    if path:
        return path.read_bytes()
    with urlopen(Request(url, headers={'User-Agent': 'HiveMIND-scheduling-pilot/1.0'}), timeout=60) as response:
        return response.read()


def numeric_rows(text):
    return [[int(n) for n in line.split()] for line in text.splitlines()
            if re.fullmatch(r'\s*\d+(?:\s+\d+)*\s*', line)]


@dataclass
class Project:
    successors: dict
    predecessors: dict
    duration: dict
    demand: dict
    capacity: list


def parse_project(data):
    text = data.decode('ascii')
    precedence, rest = text.split('PRECEDENCE RELATIONS:')[1].split('REQUESTS/DURATIONS:')
    tasks, avail = rest.split('RESOURCEAVAILABILITIES:')
    successors = {}
    for job, modes, count, *targets in numeric_rows(precedence):
        if modes != 1 or count != len(targets):
            raise ValueError('expected one mode and a complete successor list')
        successors[job] = targets
    predecessors = {j: set() for j in successors}
    for job, successors_of_job in successors.items():
        for child in successors_of_job:
            predecessors[child].add(job)
    capacity, = numeric_rows(avail)
    duration, demand = {}, {}
    for job, mode, span, *units in numeric_rows(tasks):
        if mode != 1 or len(units) != len(capacity) or any(v > cap for v, cap in zip(units, capacity)):
            raise ValueError('unsupported mode or resource demand')
        duration[job], demand[job] = span, units
    if set(duration) != set(successors):
        raise ValueError('precedence and duration tables disagree')
    return Project(successors, predecessors, duration, demand, capacity)


def serial_schedule(p, priority):
    """Place the next eligible activity at its earliest feasible start on integer time slots."""
    horizon = sum(p.duration.values())
    loads = [[0] * len(p.capacity) for _ in range(horizon)]
    starts = {}
    while len(starts) < len(p.predecessors):
        eligible = [j for j, required in p.predecessors.items() if j not in starts and required <= starts.keys()]
        job = min(eligible, key=lambda j: (priority[j], j))
        duration = p.duration[job]
        start = max((starts[j] + p.duration[j] for j in p.predecessors[job]), default=0)
        while any(loads[t][r] + units > p.capacity[r] for t in range(start, start + duration)
                  for r, units in enumerate(p.demand[job])):
            start += 1
        starts[job] = start
        for t in range(start, start + duration):
            for resource, units in enumerate(p.demand[job]):
                loads[t][resource] += units
    return starts


def checked_makespan(p, starts):
    """Recount resource use from scheduled intervals independently of the scheduler's load table."""
    if set(starts) != set(p.duration) or any(type(t) is not int or t < 0 for t in starts.values()):
        raise ValueError('missing or invalid start times')
    for predecessor, successors in p.successors.items():
        if any(starts[j] < starts[predecessor] + p.duration[predecessor] for j in successors):
            raise ValueError('unsatisfied precedence constraint')
    makespan = max(starts[j] + p.duration[j] for j in starts)
    for t in range(makespan):
        active = [j for j in starts if starts[j] <= t < starts[j] + p.duration[j]]
        if any(sum(p.demand[j][r] for j in active) > limit for r, limit in enumerate(p.capacity)):
            raise ValueError('resource capacity exceeded')
    return makespan


def measure(p, seed):
    @lru_cache(None)
    def tail(job):
        return p.duration[job] + max((tail(c) for c in p.successors[job]), default=0)

    def schedule(priority):
        starts = serial_schedule(p, priority)
        return {'makespan': checked_makespan(p, starts), 'starts': [starts[j] for j in sorted(starts)]}

    rng = random.Random(seed)
    shortest = schedule(p.duration)
    longest_tail = schedule({j: -tail(j) for j in p.duration})
    samples = [schedule({j: rng.random() for j in p.predecessors}) for _ in range(64)]
    best = min(range(len(samples)), key=lambda i: samples[i]['makespan'])
    return {'shortest_duration': shortest, 'longest_remaining_precedence_path': longest_tail,
            'best_of_64_random': dict(samples[best], zero_based_draw=best)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path)
    parser.add_argument('--solutions', type=Path)
    args = parser.parse_args()
    raw = read_data(args.archive, ARCHIVE_URL)
    reference = read_data(args.solutions, SOLUTIONS_URL)
    bounds = {(s['parameter'], s['instance']): s['optimal_makespan'] for s in json.loads(reference)['solutions']
              if s['is_proven_optimal']}
    rows = []
    start = time.monotonic()
    with ZipFile(BytesIO(raw)) as archive:
        for i in range(1, 6):
            filename = f'j301_{i}.sm'
            project_bytes = archive.read(filename)
            rows.append({'file': filename, 'sha256': sha256(project_bytes).hexdigest(), 'seed': 2807 + i,
                         'proven_optimal_makespan': bounds[1, i], 'policies': measure(parse_project(project_bytes), 2807 + i)})
    result = {'benchmark': 'PSPLIB single-mode J30', 'role': 'development pilot, one parameter family',
              'archive_url': ARCHIVE_URL, 'archive_sha256': sha256(raw).hexdigest(),
              'solutions_url': SOLUTIONS_URL, 'solutions_sha256': sha256(reference).hexdigest(),
              'schedules_checked': len(rows) * 66, 'rows': rows,
              'elapsed_seconds_excluding_download': round(time.monotonic() - start, 3)}
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()

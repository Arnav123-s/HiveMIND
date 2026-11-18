"""Replay the same completed members through an unmodified checkout's solo.first().

    python training/checked_delivery_eval.py --checkout /path/to/original > before.json
    python training/checked_delivery_eval.py --checkout . > after.json

The only substitutes are the worker results, seat selection and writing learned memory.
The coordinator, its stopping rule and its copy to the user's directory all run normally.
No candidate program runs, no model is loaded and graders see only the delivered output.
"""
import argparse
import csv
import io
import json
import os
import sys
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch


DATA = Path(__file__).resolve().parent / 'reports' / 'checked-delivery'


def controls():
    """Deliberately constructed pairs separate schema checks from the task's actual meaning."""
    task = 'Three desks have open calls: Cedar 2, Reed 5, Oak 3. Save calls.csv with columns desk,count sorted by count descending. Print the total as a single integer.'
    rows = [['desk', 'count'], ['Reed', '5'], ['Oak', '3'], ['Cedar', '2']]
    good = 'desk,count\nReed,5\nOak,3\nCedar,2\n'
    wrong_value = good.replace('Oak,3', 'Oak,5')
    shape = good.replace('Reed,5', 'Reed,5,5')
    bad_header = good.replace('desk,count', 'count,desk')
    base = dict(task=task, name='calls.csv', answer='10', format='csv', expected=rows)
    def example(label, files, answers=None, spec=base):
        if answers is None:
            answers = [spec['answer']] * len(files)
        return dict(**spec, id=label, group='constructed controls', candidates=[
            dict(file=file, answer=answer) for file, answer in zip(files, answers, strict=True)])
    yield example('valid-both', [good, good.replace('\n', '\r\n')])
    yield example('wrong-header-first', [bad_header, good])
    yield example('missing-first', [None, good])
    yield example('bad-shape-both', [shape, bad_header])
    yield example('same-wrong-value-both', [wrong_value, wrong_value])
    yield example('different-values-same-shape', [wrong_value, good])
    yield example('third-supports-second', [wrong_value, good, good])
    yield example('third-supports-first', [good, wrong_value, good])
    yield example('disagree-on-total', [good, good], ('18', '10'))
    stock = dict(task='A shelf has two red boxes and one blue box. Create stock.json as an object mapping each color to its count. Print the total count as a single integer.', name='stock.json', format='json', expected={'red': 2, 'blue': 1}, answer='3')
    yield example('truncated-json-first', ['{"red": 2,', '{"blue": 1, "red": 2}'], spec=stock)
    yield example('json-valid-wrong-both', ['{"red": 1, "blue": 2}'] * 2, spec=stock)
    note = dict(task='Write note.txt containing the exact sentence Rain has stopped. Print the number of words as a single integer.', name='note.txt', format='text', expected='Rain has stopped.', answer='3')
    yield example('nonempty-text-wrong-both', ['Sun has risen.'] * 2, spec=note)
    only_answer = dict(task='The spreadsheet input.csv holds two counts, 3 and 8. Print their sum as a single integer.', name=None, format=None, expected=None, answer='11')
    yield example('no-output-file-requested', [None, None], spec=only_answer)


def cases():
    rain = json.loads((DATA / 'rainfall.json').read_text())
    yield dict(rain, group='archived G47 incident')
    yield dict(rain, id='rainfall-reversed', group='archived order control', candidates=list(reversed(rain['candidates'])))
    yield from controls()
    fresh_path = DATA / 'fresh-members.json'
    if fresh_path.exists():
        fresh = json.loads(fresh_path.read_text())['runs']
        for spec in json.loads((DATA / 'fresh-tasks.json').read_text()):
            yield dict(spec, group='fresh G47 runs', candidates=fresh[spec['id']]['candidates'])


def capture_fresh(root):
    """Capture actual decoded file contents, stdout and worker programs before deleting a run."""
    evidence = {'environment': json.loads((root / 'environment.json').read_text()), 'runs': {}}
    for spec in json.loads((DATA / 'fresh-tasks.json').read_text()):
        run = root / 'fresh-baseline' / spec['id']
        served = json.loads((run / 'result.json').read_text())
        if served['task'] != spec['task']:
            raise ValueError(f"Unexpected task in {run}")
        seat = run / 'members'
        choice = json.loads((seat / 'members.json').read_text())
        files = []
        for i in range(1, len(choice['who']) + 1):
            result = json.loads((seat / f'member{i}.json').read_text())
            folder = seat / ('work' if i == 1 else f'member{i}')
            path = folder / spec['name']
            entry = {key: result[key] for key in ('who', 'answer', 'program', 'turns')}
            entry['file'] = path.read_bytes().decode() if path.is_file() else None
            files.append(entry)
        delivered = run / 'work' / spec['name']
        evidence['runs'][spec['id']] = {
            'started_utc': served['started_utc'], 'latency_seconds': served['latency_seconds'],
            'served_text': served['result']['text'], 'decision': choice,
            'served_file': delivered.read_bytes().decode() if delivered.is_file() else None,
            'candidates': files,
        }
    return evidence


def file_matches(case, content):
    if case['name'] is None:
        return content is None
    if content is None:
        return False
    try:
        if case['format'] == 'csv':
            return list(csv.reader(io.StringIO(content, newline=''), strict=True)) == case['expected']
        if case['format'] == 'json':
            return json.dumps(json.loads(content), sort_keys=True) == json.dumps(case['expected'], sort_keys=True)
        return content.rstrip('\r\n') == case['expected']
    except (ValueError, csv.Error):
        return False


def evaluate(solo, case, home):
    candidates = case['candidates']
    def member(task, n, board, guard, work, temperature, who, also):
        # A selector may seek a third opinion. The replay cannot invent an unobserved worker.
        row = candidates[n - 1] if n <= len(candidates) else {}
        work = Path(work)
        work.mkdir(parents=True, exist_ok=True)
        if row.get('file') is not None and case['name']:
            (work / case['name']).write_bytes(row['file'].encode('utf-8'))
        return dict(answer=row.get('answer', ''), program=row.get('program', ''), turns=row.get('turns', 0),
                    who=row.get('who', who), messages=[], hints=[])
    names = [c.get('who', f'replay-{i}') for i, c in enumerate(candidates, 1)]
    with (patch.object(solo.ternary, 'seating', return_value=names),
          patch.object(solo, 'member', member), patch.object(solo, 'keep'), redirect_stdout(io.StringIO())):
        outcome = solo.first(case['task'], home, 'never', members=2)
    work = home / 'work'
    path = work / case['name'] if case['name'] else None
    delivered = path.read_bytes().decode('utf-8') if path and path.is_file() else None
    stdout = outcome['report'].split('\n## ')[0].strip() if outcome['agreed'] else None
    candidate_ok = [row['answer'].strip() == case['answer'] and file_matches(case, row.get('file')) for row in candidates]
    file_ok = file_matches(case, delivered)
    job_ok = bool(outcome['agreed'] and stdout == case['answer'] and file_ok)
    return dict(id=case['id'], group=case['group'], candidate_correct=candidate_ok, agreed=outcome['agreed'],
                requested_seats=outcome['tries'], recorded_seats=len(candidates), stdout=stdout,
                delivered_file=delivered, file_correct=file_ok, job_correct=job_ok)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--checkout', type=Path, help='Run selection and delivery from this repo checkout.')
    mode.add_argument('--capture-fresh', type=Path, help='Collect completed G47 runs from an experiment directory.')
    parser.add_argument('--cases', type=Path, help='Replay this JSON list of complete cases in place of the primary corpus.')
    args = parser.parse_args()
    if args.capture_fresh:
        print(json.dumps(capture_fresh(args.capture_fresh), indent=2))
        return
    sys.path.insert(0, str(args.checkout.resolve()))
    with TemporaryDirectory(prefix='hive-selection-') as temp:
        home = Path(temp)
        os.environ.update(AGENT_TEAM_HOME=str(home / 'memory'), AGENT_TEAM_DISK_STOP_GB='0', HIVE_ENGRAMS='0')
        from team import solo
        corpus = json.loads(args.cases.read_text()) if args.cases else cases()
        rows = []
        for case in corpus:
            row = evaluate(solo, case, home / case['id'])
            if 'expected_action' in case:
                row['expected_action'] = case['expected_action']
                row['action_correct'] = (not row['agreed']) if case['expected_action'] == 'abstain' else row['job_correct']
            rows.append(row)
    print(json.dumps(rows, indent=2))


if __name__ == '__main__':
    main()

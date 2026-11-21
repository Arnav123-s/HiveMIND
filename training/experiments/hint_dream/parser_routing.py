"""Select a qualified record parser by probing public example inputs in WASI, then replay captured work."""
import argparse
import ast
from collections import Counter
import io
import json
from pathlib import Path
import re
import tokenize

from team.tools.source import extract_code
from training.experiments.fieldwork import campaign, work
from training.experiments.fieldwork.guest import Guest
from training.experiments.hint_dream import parser_transfer as study

# Whole labels and signed integers. Embedded section names such as "event0" are left intact.
LEAF = re.compile(r'(?<![\w+-])(?:[A-Za-z]+|[+-]?\d+)(?![\w])')


def mutation(sample, pairs):
    """Relabel every observed scalar while preserving the public serialization and record order."""
    if not isinstance(pairs, list) or not pairs:
        return None
    for row in pairs:
        if (not isinstance(row, list) or len(row) != 2 or type(row[0]) is not str
                or not re.fullmatch('[A-Za-z]+', row[0]) or type(row[1]) is not int):
            return None
    labels = list(dict.fromkeys(label for label, _ in pairs))
    values = list(dict.fromkeys(value for _, value in pairs))
    new_labels = labels[1:] + labels[:1] if len(labels) > 1 else ['oak' if labels[0] != 'oak' else 'elm']
    new_values = values[1:] + values[:1] if len(values) > 1 else [0 if values[0] else 1]
    change_label = dict(zip(labels, new_labels, strict=True))
    change_value = dict(zip(values, new_values, strict=True))
    present = Counter(LEAF.findall(sample))
    if any(present[label] < count for label, count in Counter(row[0] for row in pairs).items()):
        return None
    if any(str(v) not in present for v in values):
        return None
    replacements = change_label | {str(k):str(v) for k, v in change_value.items()}
    changed = LEAF.sub(lambda m: replacements.get(m.group(), m.group()), sample)
    return changed, [[change_label[k], change_value[v]] for k, v in pairs]


def select(request, examples, candidates, guest, interface='parse_records'):
    """Return a unique parser only when public examples support its declared record interface."""
    applicable = {c['digest']: c for c in candidates if c['task'] == interface and work.retrieve(request, [c])}
    passed = []
    reasons = {}
    if not examples or any(type(sample) is not str or not sample.strip() for sample in examples):
        return None, {'status':'missing-public-evidence', 'candidates':reasons}
    for digest, candidate in sorted(applicable.items()):
        results, _, _ = guest.run(candidate['source'], examples)
        probes = [mutation(sample, result.get('value')) for sample, result in zip(examples, results, strict=True)]
        if any(probe is None for probe in probes):
            reasons[digest] = 'no witnessed ordered records'
            continue
        changed, wanted = zip(*probes, strict=True)
        altered, _, _ = guest.run(candidate['source'], changed)
        if not all(work.matches(row.get('value'), target) for row, target in zip(altered, wanted, strict=True)):
            reasons[digest] = 'renaming did not preserve the declared records'
            continue
        reasons[digest] = 'passed public probe'
        passed.append(candidate)
    status = 'selected' if len(passed) == 1 else ('ambiguous' if passed else 'unsupported')
    return (passed[0] if len(passed) == 1 else None), {'status':status, 'candidates':reasons}


def public_input(captured):
    # The original registration stored one example inline. Read just its first literal, before the public output.
    prompt = next(c for c in captured['calls'] if not c['offered'])['messages'][-1]['content']
    request, separator, remaining = prompt.partition(' For example x = ')
    if not separator:
        raise ValueError('No registered public input')
    literal = next(tokenize.generate_tokens(io.StringIO(remaining).readline))
    if literal.type != tokenize.STRING:
        raise ValueError('Public input is not a text literal')
    return request, [ast.literal_eval(literal.string)]


def replay(sdk, out):
    study.check_manifest()
    guest = Guest(sdk)
    base = study.HERE / 'evidence/parser'
    # Directory names are storage details. Only declared interfaces, digests and source reach selection.
    candidates = sorted((r for folder in (base/'bank').iterdir() if folder.is_dir() for r in work.load_bank(folder)),
                        key=lambda c: c['digest'])
    if {r['digest'] for r in candidates} != set(study.manifest()['helpers'].values()):
        raise ValueError('Scratch candidate set differs from the two independently qualified sources')
    controls = []
    for fixture in json.loads((study.HERE/'routing-cases.json').read_text()):
        selected, details = select(fixture['request'], fixture['examples'], candidates, guest)
        digest = selected['digest'] if selected else None
        controls.append(dict(name=fixture['name'], chosen=digest, expected=fixture['expected'],
                             correct=digest == fixture['expected'], **details))
    jobs = []
    for i in range(4):
        receipt = json.loads((base/f'case-{i}.json').read_text())
        request, samples = public_input(receipt)
        chosen, details = select(request, samples, candidates, guest)
        stock = work.retrieve(request, candidates)
        # Target cases, captured predictions and manual assignments enter only after choosing.
        checks = study.task(i)[1]
        ordinary = next(c for c in receipt['calls'] if not c['offered'])
        offered = next(c for c in receipt['calls'] if c['offered'])
        def evaluate(helper):
            response = offered if helper else ordinary
            program = campaign.tool_source(extract_code(response['raw']), [helper] if helper else [])
            return work.check(guest, program, checks, explain=False)[0]
        baseline = evaluate(None)
        stock_helper = stock[0] if stock else None
        jobs.append(dict(case=i, public_request=request, public_inputs=samples, decision=details,
                         chosen=chosen['digest'] if chosen else None, manual=receipt['helper_sha256'],
                         stock=stock_helper['digest'] if stock_helper else None, stock_matched=evaluate(stock_helper),
                         ordinary_matched=baseline, selected_matched=evaluate(chosen), manual_matched=offered['matched'],
                         fallback=not bool(chosen), checks=len(checks)))
        if baseline != ordinary['matched']:
            raise ValueError('Ordinary replay disagrees with captured grade')
    campaign.save(out, {'control':controls, 'jobs':jobs})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sdk', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    replay(args.sdk, args.out)

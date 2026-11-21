"""Test a parse-only slice of two verified worker programs on independent aggregate rules."""
import argparse
import ast
import copy
import hashlib
import json
import os
from pathlib import Path
import random
import time

from team.tools.source import extract_code
from training import hint_dream
from training.experiments.fieldwork import campaign, native, work
from training.experiments.fieldwork.guest import Guest
from training.experiments.hint_dream import fit, pilot

HERE = Path(__file__).parent
CASES = (("csv", "span", False), ("ini", "minimum_index", True),
         ("csv", "minimum_index", True), ("ini", "span", False))
TITLE = 'parse_records'
SYSTEM = 'Write solve(x) in one Python code block. The standard library and any explicitly listed optional callables are available.'
OFFER = f"Optional library, already implemented: skill_{TITLE}(x) returns the input's [label, integer value] records in their original order."
CHILD = 'fffbb3692c8f1202b7df14014c8e515f77799f000428fe3fbd906f5b11f7490b'


def names(tree):
    return {n.id for n in ast.walk(tree) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}


def extract_parser(program):
    """Backward-slice the prefix used to read label and value; discard the consumer of those variables."""
    tree = ast.parse(program)
    fn, = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'solve']
    loop, = [n for n in fn.body if isinstance(n, ast.For)]
    prefix = loop.body[:2]
    if not all(isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name)
               and stmt.targets[0].id == key for stmt, key in zip(prefix, ('label', 'value'), strict=True)):
        raise ValueError('The worker has no isolatable pair decoder')
    dependencies = names(loop.iter) | names(prefix[0]) | names(prefix[1])
    setup = []
    for stmt in reversed(fn.body[:fn.body.index(loop)]):
        if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name):
            if stmt.targets[0].id not in dependencies:
                continue
        elif isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call) and isinstance(stmt.value.func, ast.Attribute):
            if stmt.value.func.attr != 'read_string' or not names(stmt.value.func) & dependencies:
                continue
        else:
            continue
        dependencies |= names(stmt)
        setup.insert(0, stmt)
    # The only new semantic operation is serializing the already-decoded pairs in event order.
    only_parser = copy.deepcopy(loop)
    only_parser.body = prefix + ast.parse('pairs.append([label, value])').body
    only_parser.orelse = []
    parser = ast.parse('def solve(x): pass').body[0]
    parser.body = setup + ast.parse('pairs = []').body + [only_parser] + ast.parse('return pairs').body
    imports = [s for s in tree.body if isinstance(s, (ast.Import, ast.ImportFrom))]
    standalone = ast.fix_missing_locations(ast.Module(body=imports + [parser], type_ignores=[]))
    for node in ast.walk(standalone):
        if isinstance(node, (ast.If, ast.IfExp, ast.Compare, ast.BinOp)):
            raise ValueError('Unexpected decision or aggregation in parser slice')
        if isinstance(node, ast.Subscript) and not names(node) <= {'row', 'cfg', 'section'}:
            raise ValueError('Worker accumulation survived the slice')
        if isinstance(node, ast.Constant) and node.value not in ('label','value',0):
            raise ValueError('Rule-specific literal in parser slice')
    return ast.unparse(standalone)


def admitted_workers():
    folder = HERE / 'evidence/confirmation'
    path, _ = fit.checked_rows(folder)
    records = [json.loads(line) for line in path.read_text().splitlines()]
    return {form: next(r for r in records if r['kind'].split()[2] == form) for form in ('csv','ini')}


def event_list(seed, n):
    rng = random.Random(f'worker-parser-transfer-v1/{seed}/{n}')
    labels = rng.sample(('iris','elm','birch','moss','oak','fir','pine','ash'), rng.randint(1, 6))
    return [(rng.choice(labels), rng.randint(-7, 7)) for _ in range(n)]


def qualify(bank, sdk):
    check_manifest()
    guest = Guest(sdk)
    receipt = {}
    for form, row in admitted_workers().items():
        original = extract_code(row['output'])
        source = extract_parser(original)
        events = [event_list('qualify/' + form, n) for n in range(64)]
        rows = [{'input':hint_dream.encode(form, e), 'output':[[k,v] for k,v in e]} for e in events]
        matched, _ = work.check(guest, source, rows, explain=False)
        if matched != len(rows):
            raise ValueError(f'{form} slice passes only {matched}/{len(rows)} parser checks')
        item = {'task':TITLE, 'description':'Decode the input text into ordered [label, integer value] records. Preserve every occurrence.',
                'source':source, 'digest':campaign.fingerprint(source), 'validation':matched}
        work.admit(bank / form, item)
        receipt[form] = {'source_program_sha256':campaign.fingerprint(original), 'helper_sha256':item['digest'],
                         'admitted':True, 'matches':matched, 'cases':len(rows), 'source_spec':row['seed']}
    pilot.save(bank / 'qualification.json', receipt)


def task(i):
    form, rule, _ = CASES[i]
    encoding = ('CSV text with header label,value' if form == 'csv' else
                'INI text with one section per event, each containing label and value')
    goal = ("map each observed label to its largest reading minus its smallest reading" if rule == 'span' else
            "map each observed label to the 1-based position in the complete input sequence of its first minimum reading")
    def example(events):
        labels = dict.fromkeys(k for k, _ in events)
        scores = {}
        for label in labels:
            group = [(v, n+1) for n, (k,v) in enumerate(events) if k == label]
            scores[label] = max(v for v,_ in group) - min(v for v,_ in group) if rule == 'span' else min(group)[1]
        return {'input':hint_dream.encode(form, events), 'output':scores}
    visible = example([('ivy',4),('oak',-1),('ivy',1),('oak',-1),('ivy',1)])
    prompt = (f'x is {encoding}, in arrival order. Labels are short words and readings are signed integers from -7 to 7. '
              f'Write solve(x). Return a dictionary that will {goal}. Empty input gives an empty dictionary. '
              f'For example x = {visible["input"]!r} gives {visible["output"]!r}.')
    checks = [example(event_list(f'case-{i}/sealed', n)) for n in (0,1,2,3,4,5,6,7,8,9,10,12,14,17,19,22,25,28,30,33,36,41,45,51)]
    return prompt, checks


def digest(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def messages(prompt, provided):
    return [{'role':'system', 'content':SYSTEM}, {'role':'user', 'content':prompt + ('\n\n' + OFFER if provided else '')}]


def manifest():
    workers = admitted_workers()
    return {'parent':CHILD, 'helpers':{k:campaign.fingerprint(extract_parser(extract_code(r['output']))) for k,r in workers.items()},
            'tasks':[{'case':i, 'input_format':form, 'rule':rule, 'offer_first':first,
                      'ordinary_messages_sha256':digest(messages(task(i)[0], False)),
                      'offered_messages_sha256':digest(messages(task(i)[0], True)), 'checks_sha256':digest(task(i)[1])}
                     for i, (form, rule, first) in enumerate(CASES)]}


def check_manifest():
    if manifest() != json.loads((HERE / 'parser-manifest.json').read_text()):
        raise ValueError('Parser, public task or sealed suite differs from registration')


def run(args):
    check_manifest()
    form, _, helper_first = CASES[args.case]
    bank = work.load_bank(args.bank / form)
    receipt = json.loads((args.bank / 'qualification.json').read_text())[form]
    if (len(bank) != 1 or bank[0]['task'] != TITLE or bank[0]['digest'] != receipt['helper_sha256']
            or receipt['matches'] != 64 or bank[0]['source'] != extract_parser(extract_code(admitted_workers()[form]['output']))):
        raise ValueError('Need the verified isolated parser of this public format')
    actual = {name:fit.digest(getattr(args, name)) for name in ('model','server','adapter')}
    if actual != dict(pilot.ASSETS, adapter=CHILD):
        raise ValueError('Unknown study assets')
    prompt, checks = task(args.case)
    order = [True, False] if helper_first else [False, True]
    record = {'complete':False, 'case':args.case, 'format':form, 'rule':CASES[args.case][1], 'assets':actual,
              'helper_sha256':receipt['helper_sha256'], 'affinity':sorted(os.sched_getaffinity(0)), 'calls':[]}
    args.out.mkdir(parents=True, exist_ok=False)
    settings = {'temperature':0.0, 'max_tokens':256, 'seed':8103, 'top_k':0, 'top_p':1.0,
                'cache_prompt':False, 'chat_template_kwargs':{'enable_thinking':False}}
    record['sampling'] = settings
    with native.server(args.server, args.model, args.out/'server.log', adapter=args.adapter, threads=2) as url:
        active = pilot.call(url+'/lora-adapters')
        if len(active) != 1 or Path(active[0]['path']).name != args.adapter.name or active[0]['scale'] != 1:
            raise RuntimeError('Unexpected active adapter')
        for provided in order:
            conversation = messages(prompt, provided)
            began = time.monotonic()
            data = pilot.call(url+'/v1/chat/completions', dict(settings, messages=conversation))
            choice = data['choices'][0]
            record['calls'].append({'offered':provided, 'messages':conversation, 'raw':choice['message'].get('content') or '',
                                    'seconds':round(time.monotonic()-began,3), 'stop':choice['finish_reason'], 'usage':data['usage']})
            pilot.save(args.out/'result.json', record)
    # Both programs have already been authored. Neither model offer receives grading feedback.
    guest = Guest(args.sdk)
    for call in record['calls']:
        source = extract_code(call['raw'])
        try:
            tree = ast.parse(source)
            used = any(isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id=='skill_'+TITLE for node in ast.walk(tree))
        except SyntaxError:
            used = False
        program = campaign.tool_source(source, bank if call['offered'] else [])
        matched, _ = work.check(guest, program, checks, explain=False)
        call.update(calls_helper_in_source=used, checks=len(checks), matched=matched, passed=matched==len(checks))
        if call['offered']:
            without = work.check(guest, source, checks, explain=False)[0] if used else matched
            call['matched_with_helper_removed'] = without
    record['complete'] = True
    pilot.save(args.out/'result.json', record)
    print([(c['offered'],c['used_helper'],c['matched']) for c in record['calls']], flush=True)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--qualify', action='store_true')
    ap.add_argument('--bank', required=True, type=Path)
    ap.add_argument('--sdk', required=True, type=Path)
    ap.add_argument('--case', type=int, choices=range(4))
    for option in ('model','server','adapter','out'):
        ap.add_argument('--'+option, type=Path)
    options=ap.parse_args()
    if options.qualify:
        qualify(options.bank, options.sdk)
    elif options.case is not None and all(getattr(options,k) for k in ('model','server','adapter','out')):
        run(options)
    else:
        ap.error('Use --qualify or supply a frozen case, model, server, adapter and output folder')

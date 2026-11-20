"""Paired CPU measurements using the local t80 base, differing only in native GBNF sampling."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import time
from urllib.parse import urlparse

from training.domain_engram import T80_SHA256, _post, _server

HERE = Path(__file__).resolve().parent
SEED = 1709
BUDGET = 32
SYSTEM = "Answer the user's question."


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def literal(value):
    return json.dumps(value,ensure_ascii=True)


def alternatives(options, *, quoted=False):
    if len(options) < 2 or len(set(options)) != len(options):
        raise ValueError('choice format requires two or more different options')
    return '(' + ' | '.join(literal(json.dumps(v,ensure_ascii=True) if quoted else v) for v in options) + ')'


def grammar(row):
    fmt, schema = row['format'], row['schema']
    def scalar(field):
        if field['type'] == 'int':
            return 'integer'
        if field['type'] == 'bool':
            return '("true" | "false")'
        if field['type'] == 'enum':
            return alternatives(field['options'], quoted=fmt=='object')
        raise ValueError('unsupported scalar type')
    if fmt == 'enum':
        rule = alternatives(schema['options'])
    elif fmt == 'array' and schema['items']=='int':
        rule = '\"[\" ws (integer (ws \",\" ws integer)*)? ws \"]\"'
    elif fmt == 'csv':
        rule = ' "," '.join(scalar(f) for f in schema['fields'])
    elif fmt == 'object':
        parts = [literal(json.dumps(f['name'])) + ' ws ":" ws ' + scalar(f) for f in schema['fields']]
        rule = '"{" ws ' + ' ws "," ws '.join(parts) + ' ws "}"'
    else:
        raise ValueError('unsupported answer format')
    return 'root ::= ' + rule + '\nws ::= " "?\ninteger ::= "-"? ("0" | [1-9] [0-9]*)\n'


def owned_pid(url, runtime):
    port = str(urlparse(url).port).encode()
    for path in Path('/proc').glob('[0-9]*'):
        try:
            fields = (path/'stat').read_text().rsplit(')',1)[1].split()
            if int(fields[1]) != os.getpid():
                continue
            args = (path/'cmdline').read_bytes().split(b'\0')
            if port in args and Path(os.fsdecode(args[0])).resolve() == runtime.resolve():
                return int(path.name)
        except (OSError, ValueError, IndexError):
            continue
    raise RuntimeError('could not verify native child identity for CPU measurement')


def cpu_seconds(pid):
    # /proc process-level utime/stime include all worker threads. First field after comm is state (field 3).
    fields = (Path('/proc')/str(pid)/'stat').read_text().rsplit(')',1)[1].split()
    return (int(fields[11])+int(fields[12]))/os.sysconf('SC_CLK_TCK')


def render(url,prompt):
    messages = [{'role':'system','content':SYSTEM},{'role':'user','content':prompt}]
    return _post(url,'/apply-template',{'messages':messages,'chat_template_kwargs':{'enable_thinking':False}})['prompt']


def generate(url,pid,prompt,gbnf=None):
    body = dict(prompt=prompt,n_predict=BUDGET,temperature=0,seed=SEED,cache_prompt=False,stream=False)
    if gbnf is not None:
        body['grammar'] = gbnf
    before = cpu_seconds(pid)
    start = time.monotonic()
    out = _post(url,'/completion',body)
    elapsed = time.monotonic()-start
    return dict(raw=out['content'],seconds=round(elapsed,4),cpu_seconds=round(cpu_seconds(pid)-before,3),
                predicted_tokens=out['tokens_predicted'],prompt_tokens=out['tokens_evaluated'],
                stop_type=out.get('stop_type'),stopped_eos=out.get('stopped_eos'),truncated=out.get('truncated'),
                timings=out.get('timings'))


def write(path, value):
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n'); temp.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model',type=Path,required=True)
    parser.add_argument('--runtime',type=Path,required=True)
    parser.add_argument('--panel',type=Path,default=HERE/'panel.json')
    parser.add_argument('--out',type=Path,required=True,help='new receipt directory')
    parser.add_argument('--threads',type=int,default=2)
    args = parser.parse_args()
    if args.out.exists() and any(args.out.iterdir()):
        raise SystemExit('Use an empty measurement directory.')
    panel = json.loads(args.panel.read_bytes())
    rows = {row['id']: grammar(row) for row in panel}
    if not 8 <= len(rows) == len(panel) <= 12:
        raise SystemExit('expected 8–12 distinct preregistered tasks')
    if sha(args.model) != T80_SHA256:
        raise SystemExit('use the recorded Ternary-Bonsai-8B base')
    args.out.mkdir(parents=True, exist_ok=True)
    env = dict(panel_sha256=sha(args.panel),runner_sha256=sha(__file__),model_sha256=T80_SHA256,
               runtime_sha256=sha(args.runtime),seed=SEED,max_output_tokens=BUDGET,temperature=0,
               cache_prompt=False,threads=args.threads,system=SYSTEM,grammars=rows)
    write(args.out/'environment.json',env)
    records = []
    with _server(args.model,args.runtime,args.threads) as url:
        pid=owned_pid(url,args.runtime)
        sentinel = render(url,'Reply with just the letter A.')
        off = generate(url,pid,sentinel)
        on = generate(url,pid,sentinel,'root ::= "QZ"\n')
        write(args.out/'preflight.json', dict(control=off, forced=on))
        if off['raw'].strip() == 'QZ' or on['raw'] != 'QZ':
            raise RuntimeError('the native grammar did not demonstrate forced token selection')
        for i, row in enumerate(panel):
            prompt = render(url,row['prompt'])
            item = dict(id=row['id'],rendered_sha256=hashlib.sha256(prompt.encode()).hexdigest(),arms={})
            for arm in (('free','grammar') if i%2==0 else ('grammar','free')):
                item['arms'][arm] = generate(url,pid,prompt,rows[row['id']] if arm=='grammar' else None)
            records.append(item)
            write(args.out/'pairs.json',records)
            print(row['id'], 'completed',flush=True)


if __name__ == '__main__':
    main()

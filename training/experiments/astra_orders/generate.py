"""Run the frozen paired first turns with one locally loaded G55 trunk."""
import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import socket
import subprocess
import time
from urllib.request import Request, urlopen

HERE = Path(__file__).resolve().parent
ASSETS = {'runtime':'0dc642d61dc39d51a8b5da348c43ba19d29f720b2a3ac790e0019351239da3b2',
          'model':'1376f942aa90e60f7b570c1d81b3916fea1315ff85aa1c4d19006af68fb4b922',
          'lora':'72913f1c566638f2177574178f1d6925cde956a92b35af06795e7598c5729036'}


def file_hash(path):
    with path.open('rb') as f:
        h = sha256()
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
        return h.hexdigest()


def call(url, data=None, timeout=240):
    request = Request(url, data=None if data is None else json.dumps(data).encode(), headers={'Content-Type':'application/json'})
    with urlopen(request, timeout=timeout) as reply:
        return json.load(reply)


def cpu(pid):
    fields = Path(f'/proc/{pid}/stat').read_text().split(') ',1)[1].split()
    return (int(fields[11])+int(fields[12])) / os.sysconf('SC_CLK_TCK')


def save(path, record):
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(record, indent=2, sort_keys=True, ensure_ascii=False)+'\n')
    tmp.replace(path)


def original_offers(data):
    for index, row in enumerate(data['rows']):
        arms = ['short', 'full'] + (['scaffold'] if row['scaffold'] else [])
        first = index % len(arms)
        for arm in arms[first:] + arms[:first]:
            messages = [{'role': 'system', 'content': data['orders']['short' if arm == 'scaffold' else arm]},
                        {'role': 'user', 'content': row['user'] + (row['scaffold'] if arm == 'scaffold' else '')}]
            yield row['id'], arm, messages, {}


def run(args, offers=original_offers, inputs=None, inputs_hash='bf794b51abdbd4206d8df953f84968461435077a0775ba0a6efc385eed4b6062'):
    for k,h in ASSETS.items():
        if file_hash(getattr(args,k)) != h:
            raise ValueError(f'{k} digest mismatch')
    inputs = inputs or HERE / 'inputs.json'
    if file_hash(inputs) != inputs_hash:
        raise ValueError('frozen inputs digest mismatch')
    data = json.loads(inputs.read_bytes())
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', 0))
        port = probe.getsockname()[1]
    url = f'http://127.0.0.1:{port}'
    flags = ['-ngl','0','-c','2048','-t','2','-tb','2','-rtr','-b','128','-ub','128','--parallel','1',
             '--threads-http','2','--port',str(port),'--host','127.0.0.1','--jinja']
    settings = {'temperature':0.,'top_k':0,'top_p':1.,'cache_prompt':False,'max_tokens':192,
                'chat_template_kwargs':{'enable_thinking':False},'seed':8103}
    record = {'assets_sha256':ASSETS,'inputs_sha256':inputs_hash,'native_flags':flags,'sampling':settings,
              'affinity':sorted(os.sched_getaffinity(0)), 'utc_start':datetime.now(timezone.utc).isoformat(),'calls':[]}
    if args.out.exists():
        raise FileExistsError(args.out)
    with args.log.open('wb') as log:
        proc = subprocess.Popen([str(args.runtime),'-m',str(args.model),'--lora',str(args.lora),*flags],stdout=log,stderr=log)
        try:
            start = time.monotonic()
            while time.monotonic()-start < 120:
                if proc.poll() is not None:
                    raise RuntimeError(f'model server exited {proc.returncode}')
                try:
                    if call(url+'/health',timeout=1).get('status') == 'ok':
                        break
                except OSError:
                    pass
                time.sleep(.25)
            else:
                raise TimeoutError('startup exceeded 120s')
            record['load_seconds'] = round(time.monotonic()-start,3)
            adapters = call(url+'/lora-adapters')
            assert len(adapters)==1 and Path(adapters[0]['path']).name==args.lora.name and adapters[0]['scale']==1, adapters
            record['lora_adapters'] = adapters
            for ident, arm, messages, overrides in offers(data):
                start, prev = time.monotonic(), cpu(proc.pid)
                reply = call(url+'/v1/chat/completions', dict(settings | overrides, messages=messages))
                choice = reply['choices'][0]
                observed = {'id': ident, 'arm': arm, 'raw': choice['message'].get('content') or '',
                            'finish_reason': choice.get('finish_reason'), 'usage': reply['usage'],
                            'wall_s': round(time.monotonic()-start, 3), 'server_cpu_s': round(cpu(proc.pid)-prev, 3)}
                if overrides:
                    observed['sampling_override'] = overrides
                if offers is not original_offers:
                    observed['system_sha256'] = sha256(messages[0]['content'].encode()).hexdigest()
                record['calls'].append(observed)
                save(args.out, record)
                print(ident, arm, reply['usage']['completion_tokens'], flush=True)
            record['complete'] = True
            record['utc_finished'] = datetime.now(timezone.utc).isoformat()
            save(args.out,record)
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()


if __name__=='__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for key in ['runtime','model','lora','out','log']:
        p.add_argument('--'+key,type=Path,required=True)
    run(p.parse_args())

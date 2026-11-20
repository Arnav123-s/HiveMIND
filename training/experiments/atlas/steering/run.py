"""Create and check a native control vector on a small frozen binary-judgment task."""
import argparse
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import socket
import subprocess
import time
from urllib.request import Request, urlopen

HERE = Path(__file__).resolve().parent


@contextmanager
def server(args, vector, scale):
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0))
        port=sock.getsockname()[1]
    address=f'http://127.0.0.1:{port}'
    cmd=[str(args.runtime),'-m',str(args.model),'-t',str(args.threads),'-tb',str(args.threads),
         '-ngl','0','-c','512','--parallel','1','--port',str(port),'--host','127.0.0.1','--jinja','--no-graph-reuse']
    if scale:
        cmd+=['--control-vector-scaled',str(vector),str(scale),'--control-vector-layer-range','20','30']
    with (args.scratch/f'server-{scale}.log').open('wb') as log:
        proc=subprocess.Popen(cmd,stdout=log,stderr=log)
        try:
            for _ in range(240):
                if proc.poll() is not None:
                    raise RuntimeError(f'native server exited; see {log.name}')
                try:
                    with urlopen(address+'/health',timeout=1) as r:
                        if json.load(r).get('status')=='ok':
                            break
                except OSError:
                    pass
                time.sleep(.5)
            else:
                raise TimeoutError('native server startup')
            yield address
        finally:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=7)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()


def ask(address, text):
    data={'messages':[{'role':'user','content':text}],'max_tokens':1,'temperature':0,'cache_prompt':False,
          'seed':991,'chat_template_kwargs':{'enable_thinking':False}}
    req=Request(address+'/v1/chat/completions',data=json.dumps(data).encode(),headers={'Content-Type':'application/json'})
    t0=time.monotonic()
    with urlopen(req,timeout=60) as r:
        d=json.load(r)
    return {'token':d['choices'][0]['message']['content'],'seconds':round(time.monotonic()-t0,3),'usage':d['usage']}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for arg in ('model','runtime','generator','scratch','out'):
        p.add_argument('--'+arg,type=Path,required=True)
    p.add_argument('--threads',type=int,default=2)
    args=p.parse_args()
    data=json.loads((HERE/'study.json').read_text())
    args.scratch.mkdir(parents=True,exist_ok=False)
    vector=args.scratch/'verification.gguf'
    for n,name in enumerate(('positive','negative')):
        (args.scratch/(name+'.txt')).write_text(''.join(row[n]+'\n' for row in data['pairs']))
    cmd=[str(args.generator),'-m',str(args.model),'-ngl','0','-t',str(args.threads),'-tb',str(args.threads),
         '-c','256','--method','mean','--positive-file',str(args.scratch/'positive.txt'),
         '--negative-file',str(args.scratch/'negative.txt'),'-o',str(vector)]
    t0=time.monotonic()
    with (args.scratch/'generation.log').open('wb') as log:
        subprocess.run(cmd,stdout=log,stderr=log,check=True,timeout=300)
    result={'fit_seconds':round(time.monotonic()-t0,3),'vector_bytes':vector.stat().st_size,
            'vector_sha256':hashlib.sha256(vector.read_bytes()).hexdigest(),
            'benchmark_sha256':hashlib.sha256((HERE/'study.json').read_bytes()).hexdigest(),'arms':{}}
    for scale,arms in [(0,('bare','reminder')),(1,('positive',)),(-1,('negative',))]:
        with server(args,vector,scale) as address:
            for arm in arms:
                rows=[]
                for task,key in data['tasks']:
                    prompt=data['instruction']+' '+task
                    if arm=='reminder':
                        prompt+=' Double-check the claim before you finish.'
                    r=ask(address,prompt)
                    rows.append(dict(task=task,key=key,correct=r['token'].strip()==key,**r))
                result['arms'][arm]=dict(correct=sum(r['correct'] for r in rows),rows=rows)
                args.out.write_text(json.dumps(result,indent=2)+'\n')
                print(arm,result['arms'][arm]['correct'],flush=True)


if __name__=='__main__':
    main()

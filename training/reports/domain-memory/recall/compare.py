"""Compare actual legacy/current lexical recall in separate processes on identical inert banks."""
import argparse
from collections import defaultdict
import hashlib
import json
import os
from pathlib import Path
import statistics
import subprocess
import sys
import tempfile
import time


BASE = 't80'
MEMBER = 't80+child'
WORDS = ('calendar', 'invoice', 'shipment', 'meter', 'booking', 'balance', 'inventory', 'document')
VERBS = ('review', 'reconcile', 'compare', 'validate')
REPEATS = 3


def digest(value):
    data = json.dumps(value, ensure_ascii=True, separators=(',', ':'), sort_keys=True).encode()
    return hashlib.sha256(data).hexdigest()


def block(name, task, **other):
    return dict(name=name, task=task, dna=BASE, **other)


def setup(root, size):
    bank, adapters = root/'bank', root/'adapters'
    bank.mkdir(); adapters.mkdir()
    rows = [block(name,'tripod reflex sight inventory',cell=owner) for name,owner in
            [('a_other','sister'),('c_parent','parent'),('z_child','child'),('m_free','')]]
    rows += [block('a_tie','rose violet ledger'),block('z_tie','rose violet ledger'),
             block('folded','sealed sapphire carton',folded=5),block('archived','steel turquoise cylinder',archived=True),
             block('missing','brass citrine prism'),block('tampered','pink garnet bar',sha256='0'*64),
             block('shadowed','blue feldspar rod'),
             block('label_checked','North Desk',domain='math',form='label',labels=['fern','oak'],
                   cues=['stamp','office'],growth_group='desk',verified=True),
             block('label_pending','Other Desk',domain='math',form='label',labels=['fern','oak'],
                   cues=['stamp','office'],growth_group='another',verified=False)]
    for i in range(size-len(rows)):
        topic,verb=WORDS[i%len(WORDS)],VERBS[(i//len(WORDS))%len(VERBS)]
        row=block(f'e{i:05}',f'{verb} {topic} records for district{i%19} ticket{i:05}',
                  cell=('child','parent','sister','')[i%4])
        if i%13==0:row['dna']='t17'
        rows.append(row)
    for i,r in enumerate(rows):
        name=r['name'];data=('inert test file '+name).encode()
        if i%11==0 and 'sha256' not in r:r['sha256']=hashlib.sha256(data).hexdigest()
        if name!='missing':(bank/(r['dna']+'+'+name+'.gguf')).write_bytes(data)
        if name=='shadowed':(adapters/(BASE+'+'+name+'.gguf')).write_bytes(b'reserved active cell')
    (bank/'index.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
    return bank,adapters,rows


def queries(rows):
    calls=[]
    def add(kind,api,text,**options):
        calls.append((kind,api,text,options))
    normal=[r for r in rows if r['name'].startswith('e') and r['dna']==BASE]
    for i in range(10):
        row=normal[(i*97+1)%len(normal)]
        verb,topic,_,_,district,ticket=row['task'].split()
        add('specific','recall',f'{topic} {district} {ticket}')
        add('common','recall',f'{verb} {topic} records')
        add('absent','recall',f'quasar marzipan pencil{i}')
    for cell in (None,'child','parent','sister','unrelated'):
        add('lineage','recall','tripod reflex sight inventory now',cell=cell,most=5)
        add('lineage','recall_scaled','tripod reflex inventory now',cell=cell,most=3)
    for least in (0,0.34,1.0):
        for most in (0,1,4):
            add('tie_cutoff','recall','rose violet ledger now',least=least,most=most)
    add('tie_cutoff','recall_scaled','no lexical overlap',least=0,most=3)
    add('exact','recall','rose violet ledger')
    add('exact','for_request','rose violet ledger',labels=False)
    for text in ('sealed sapphire carton today','steel turquoise cylinder today','brass citrine prism today',
                 'pink garnet bar today','blue feldspar rod today'):
        add('integrity','recall',text)
    prompt='Choose fern or oak for the stamp at North Desk.'
    add('label','for_request',prompt,domain='math',labels=True)
    add('label','for_request',prompt,domain='math',labels=False)
    add('label','for_request',prompt,domain='conversation',labels=True)
    return calls


def mutate(engram,bank):
    answers={}
    name,program='late_pack',b'pristine'
    row=block(name,'cerulean raven gates',sha256=hashlib.sha256(program).hexdigest())
    path=bank/f'{BASE}+{name}.gguf'; path.write_bytes(program)
    with (bank/'index.jsonl').open('a') as f:f.write(json.dumps(row)+'\n')
    query=lambda:engram.recall('cerulean raven gates today',BASE)
    answers['append']=query()
    meta=path.stat();path.write_bytes(b'altered!')
    os.utime(path,ns=(meta.st_atime_ns,meta.st_mtime_ns))
    answers['same_size_mtime_tamper']=query()
    path.write_bytes(program);answers['restored']=query()
    path.unlink();answers['deleted']=query()
    path.write_bytes(program);answers['recreated']=query()
    answers['fold_count']=engram.fold([name],9);answers['post_fold']=query()
    shared=bank/f'{BASE}+hive.gguf';shared.touch()
    answers['shared']=engram.recall('nothing matches',BASE,most=0)
    shared.unlink();answers['shared_removed']=engram.recall('nothing matches',BASE,most=0)
    expected={'append':[name],'same_size_mtime_tamper':[],'restored':[name],'deleted':[],
              'recreated':[name],'fold_count':1,'post_fold':[],'shared':['hive'],'shared_removed':[]}
    if answers!=expected:raise AssertionError((answers,expected))
    return answers


def worker(root,checkout,size):
    bank,adapters,rows=setup(root,size)
    os.environ.update(HIVE_ENGRAMS_HOME=str(bank),HIVE_ENGRAMS='1',HIVE_ENGRAM_MATCH='words',HIVE_ENGRAM_GATE='0')
    sys.path.insert(0,str(checkout.resolve()))
    from team import engram,ternary
    ternary.ADAPTERS=adapters
    # This benchmark models a tiny explicit family, independent of the installed native model roster.
    ternary._parents=lambda: {'child':'parent','parent':'ancestor','sister':'parent'}
    calls=queries(rows)
    def execute(api,text,options):
        func=getattr(engram,api)
        return func(text,MEMBER if api=='for_request' else BASE,**options)
    _,api,text,options=calls[0]
    begin=time.process_time_ns();execute(api,text,options);cold=time.process_time_ns()-begin
    results=[];timings=defaultdict(list)
    for iteration in range(REPEATS):
        batch=[]
        for kind,api,text,options in calls:
            begin=time.process_time_ns(); value=execute(api,text,options);elapsed=time.process_time_ns()-begin
            timings[kind].append(elapsed);batch.append(value)
        if results and results!=batch:raise AssertionError('warm recall drifted across repetitions')
        results=batch
    if any(results[i] for i,(kind,*_) in enumerate(calls) if kind=='integrity'):
        raise AssertionError('disallowed weights surfaced')
    mutation=mutate(engram,bank)
    source=hashlib.sha256((checkout/'team/engram.py').read_bytes()).hexdigest()
    helper=checkout/'team/engram_index.py'
    helper_hash=hashlib.sha256(helper.read_bytes()).hexdigest() if helper.is_file() else None
    return {'source':source,'index_helper_sha256':helper_hash,'rows':size,'fixture_sha256':digest(rows),'queries_sha256':digest(calls),
            'answers_sha256':digest(results),'queries':len(calls),'repetitions':REPEATS,
            'mutations':mutation,'answers':results,'cold_cpu_ns':cold,
            'warm_median_cpu_ns':{k:int(statistics.median(v)) for k,v in timings.items()},
            'warm_total_cpu_ns':sum(sum(v) for v in timings.values())}


def launch(checkout, size):
    command=[sys.executable,'-I',str(Path(__file__).resolve()),'--worker',str(checkout.resolve()),'--size',str(size)]
    return json.loads(subprocess.check_output(command))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference',type=Path)
    parser.add_argument('--candidate',type=Path,default=Path.cwd())
    parser.add_argument('--out',type=Path)
    parser.add_argument('--worker',type=Path)
    parser.add_argument('--size',type=int)
    args=parser.parse_args()
    if hasattr(os,'sched_getaffinity'):os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
    if args.worker:
        with tempfile.TemporaryDirectory() as root:print(json.dumps(worker(Path(root),args.worker,args.size)))
        return
    if not args.reference or not args.out:parser.error('--reference and --out required')
    report={'clock':'process_time_ns, one CPU where affinity is supported','sizes':{}}
    for i,n in enumerate((128,1024)):
        methods=[('reference',args.reference),('indexed',args.candidate)]
        results={key:launch(path,n) for key,path in (methods if i==0 else reversed(methods))}
        a,b=results['reference'],results['indexed']
        for key in ('mutations','answers','fixture_sha256','queries_sha256'):
            if a[key]!=b[key]:raise AssertionError(f'{n} records: different {key}')
        for record in results.values():record.pop('answers')
        report['sizes'][n]=results
    args.out.write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()

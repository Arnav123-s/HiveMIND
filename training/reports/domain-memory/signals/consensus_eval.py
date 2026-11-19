"""Compare frozen signal and same-view centroid predictions through the serving agreement gate."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

from evaluate import DOMAINS, baseline

HERE = Path(__file__).resolve().parent
PANELS = {
    'retrospective': (HERE, '566a530032ab75138fd81807b3fb81e57c025d0c06723998152f2f60a375b7d7',
                     '05544d445bb2794df2d3f64d80f4b42fc52ce38a8240be6221cf06d9893c01e6'),
    'confirmation': (HERE/'consensus', '4d4f7155e539e0cac486fcd6b8018086f5f1bf4b06d8a3cc16f8266be17f3cae',
                     'e34037f844cd8fd47ca35b5ca79c8364fbfe73f4ab49dee5af67061004182dae'),
}


def read(path, expected):
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != expected:
        raise ValueError(str(path) + ' changed')
    return json.loads(data)


def grade(rows, gold, predictions):
    def tally(method, subset):
        cells = Counter()
        for r in subset:
            q=r['id']; expected=gold[q]['domain']; actual=predictions[q][method]
            if actual is None:
                cells['supported_withheld' if expected is not None else 'open_correct'] += 1
            elif actual == expected:
                cells['correct_advice'] += 1
            else:
                cells['wrong_on_supported' if expected is not None else 'spurious_on_open'] += 1
        keys = ('correct_advice','wrong_on_supported','spurious_on_open','supported_withheld','open_correct')
        values = {k:cells[k] for k in keys}
        values['exact'] = cells['correct_advice'] + cells['open_correct']
        values['issued'] = cells['correct_advice'] + cells['wrong_on_supported'] + cells['spurious_on_open']
        return values

    scores = {m:tally(m,rows) for m in ('pair','centroid','consensus')}
    scores['by_group']={g:tally('consensus',[r for r in rows if r['group']==g]) for g in sorted({r['group'] for r in rows})}
    scores['by_domain']={d:tally('consensus',[r for r in rows if gold[r['id']]['domain']==d]) for d in DOMAINS}
    relation=Counter();wrong_filtered=[];correct_filtered=[];wrong_retained=[]
    for r in rows:
        q=r['id'];a=predictions[q]['pair'];b=predictions[q]['centroid'];g=gold[q]['domain']
        relation['named_agreement' if a==b and a is not None else 'mutual_abstention' if a==b else 'disagreement']+=1
        if a is not None and a!=b:
            (correct_filtered if a==g else wrong_filtered).append(q)
        if a is not None and a==b and a!=g:wrong_retained.append(q)
    pair,consensus=scores['pair'],scores['consensus']
    # Cross products express strict improvement without rounded percentages.
    criterion=(consensus['issued']>0 and pair['issued']>0 and
               consensus['correct_advice']*pair['issued']>pair['correct_advice']*consensus['issued'] and
               4*consensus['correct_advice']>=3*pair['correct_advice'])
    scores.update(relation=dict(relation),correct_filtered=correct_filtered,
                  wrong_filtered=wrong_filtered,wrong_retained=wrong_retained,advisory_criterion=criterion)
    return scores


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--checkout',type=Path,default=Path.cwd())
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    sys.path.insert(0,str(a.checkout.resolve()))
    from team import domain_consensus,signals
    results={}
    for name,(d,input_hash,key_hash) in PANELS.items():
        rows=read(d/'cases.json',input_hash)
        references,metadata=baseline(rows,a.checkout);predictions={}
        for r in rows:
            q=r['id'];current=signals.read_request(r['message'],r['history'])
            paired=current['domain'] if current else None
            text=references[q]['public_centroid_prior_user_only']
            served=domain_consensus.read_consensus(r['message'],r['history'],current)
            routed=served['domain'] if served else None
            expected=paired if paired==text else None
            if expected!=routed:
                raise ValueError('Serving and reference disagree for '+q)
            predictions[q]={'pair':paired,'centroid':text,'consensus':routed}
        gold=read(d/'keys.json',key_hash)
        results[name]={'inputs':input_hash,'keys':key_hash,'centroid_training':metadata,
                       'metrics':grade(rows,gold,predictions),'predictions':predictions}
    results['sources']={p:hashlib.sha256((a.checkout/p).read_bytes()).hexdigest() for p in
                        ('team/signals.py','team/domain_consensus.py','team/assets/request-signals-v1.json.gz',
                         'team/assets/domain-centroid-v1.json.gz')}
    a.output.write_text(json.dumps(results,indent=2)+'\n')
    for name in PANELS:
        print(name, json.dumps({m:results[name]['metrics'][m] for m in ('pair','centroid','consensus','relation','correct_filtered','wrong_filtered','wrong_retained','advisory_criterion')}))

if __name__=='__main__':
    main()

"""Run the frozen six-domain routing study. Run from a checkout containing the signal bundle."""
import argparse
from collections import Counter
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import random
import re
import sys
import time

import centroid
import keywords

HERE = Path(__file__).resolve().parent
DOMAINS = tuple(keywords.TERMS)
CASES_SHA = '566a530032ab75138fd81807b3fb81e57c025d0c06723998152f2f60a375b7d7'
KEYS_SHA = '05544d445bb2794df2d3f64d80f4b42fc52ce38a8240be6221cf06d9893c01e6'


def read_frozen(name, expected):
    content = (HERE / name).read_bytes()
    if hashlib.sha256(content).hexdigest() != expected:
        raise ValueError('unexpected bytes in ' + name)
    return json.loads(content)


def permute(items, rng):
    # A fixed, label-independent single cycle in each eligible stratum.
    donors = list(items)
    for i in range(len(donors) - 1, 0, -1):
        j = rng.randrange(i)
        donors[i], donors[j] = donors[j], donors[i]
    return dict(zip(items, donors, strict=True))


def sections(path):
    result = {}
    current = None
    for line in path.read_text().splitlines():
        line = line.strip()
        if line.startswith('[') and line.endswith(']'):
            current = line[1:-1]
            result[current] = []
        elif line and not line.startswith('#'):
            result[current].append(line)
    return result


def baseline(cases, checkout):
    samples = sections(checkout/'training/signals/requests.txt')
    topics = sections(checkout/'training/signals/topics.txt')
    data = [(text, d if d in DOMAINS else None) for d, rows in samples.items() for text in rows[:32]]
    data.extend((text, d) for d, rows in topics.items() for text in rows)
    classifier, model_info = centroid.build(data)
    normalize = lambda text: ' '.join(re.findall(r'[a-z0-9]+', text.casefold()))
    public_text = {normalize(text) for text, _ in data}
    model_info['identical_public_training_messages'] = [r['id'] for r in cases if normalize(r['message']) in public_text]
    model_info['identical_public_history_turns'] = [r['id'] for r in cases if any(
        normalize(h['content']) in public_text for h in r['history'])]
    rows = {}
    for r in cases:
        m,h = r['message'],r['history']
        prior_user = [item for item in h if item['role'] == 'user'][-1:]
        rows[r['id']] = {'no_advice': None, 'keywords':keywords.read(m,h),
                         'keywords_no_history':keywords.read(m), 'public_centroid': classifier(m,h),
                         'keywords_prior_user_only': keywords.read(m,prior_user),
                         'public_centroid_prior_user_only': classifier(m,prior_user)}
    return rows, model_info


def decode(value):
    if value is None:
        return None
    domain = value['domain']
    if domain not in DOMAINS:
        raise ValueError(f'unknown routed domain {domain!r}')
    return domain


def collect(cases, checkout):
    # The sealed key is read by main only AFTER collect finishes. Runtime APIs see
    # just the current utterance, ordered chat turns and the two public wire frames.
    sys.path.insert(0, str(checkout.resolve()))
    from team import signals
    result, baseline_info = baseline(cases, checkout)
    source = {r['id']:r for r in cases}
    rng = random.Random(171119)
    query_peers = permute(list(source), rng)
    context_peers = permute([q for q in source if source[q]['history']], rng)
    frames = {q:signals.frames(r['message'],r['history']) for q,r in source.items()}
    quiet_frames = {q:signals.frames(r['message'],[]) for q,r in source.items()}
    blank_requests = {q:signals.frames('',r['history'])[1] for q,r in source.items()}
    meta, traces = {}, {}
    intact_seconds = 0.0
    started = time.perf_counter()
    for q,r in source.items():
        t, req, ctx = frames[q]
        _, _, zero_context = quiet_frames[q]
        other_req = frames[query_peers[q]][1]
        other_ctx = frames[context_peers.get(q,q)][2]
        before = time.perf_counter()
        normal = signals.read_request(r['message'],r['history'])
        intact_seconds += time.perf_counter() - before
        if signals.read_frames(t,[req,ctx]) != normal:
            raise AssertionError('public API and intact frames differ on '+q)
        experiments = {
            'intact':normal, 'missing_request': signals.read_frames(t,[ctx]),
            'missing_context':signals.read_frames(t,[req]), 'missing_both':signals.read_frames(t,[]),
            'empty_context':signals.read_frames(t,[req,replace(ctx,payload=zero_context.payload)]),
            'empty_request':signals.read_frames(t,[replace(req,payload=blank_requests[q].payload),ctx]),
            'shuffled_request':signals.read_frames(t,[replace(req,payload=other_req.payload),ctx]),
            'shuffled_context':signals.read_frames(t,[req,replace(ctx,payload=other_ctx.payload)]),
        }
        for key,val in experiments.items():
            result[q][key] = decode(val)
        traces[q] = {'intact':normal,'request_payload':list(req.payload),'context_payload':list(ctx.payload),
                     'request_payload_donor':query_peers[q],'context_payload_donor':context_peers.get(q),
                     'request_payload_changed':req.payload!=other_req.payload,'context_payload_changed':ctx.payload!=other_ctx.payload}
    elapsed = time.perf_counter() - started
    hashes = {str(f.relative_to(checkout)):hashlib.sha256(f.read_bytes()).hexdigest()
              for f in (checkout/'team/signals.py', checkout/'training/signals/requests.txt',
                        checkout/'training/signals/topics.txt', checkout/'training/signals/train.py',
                        checkout/'team/assets/request-signals-v1.json.gz') if f.is_file()}
    meta.update(classifier=baseline_info,intervention_loop_seconds=round(elapsed,5),
                normal_calls=len(cases),normal_cpu_wall_seconds=round(intact_seconds,5),cases=len(cases),sources=hashes)
    return result, traces, meta


def grade(cases, gold, outputs, traces):
    groups = sorted({r['group'] for r in cases})
    methods = list(next(iter(outputs.values())).keys())
    metrics = {}
    def score(method, group):
        return sum(outputs[r['id']][method] == gold[r['id']]['domain'] for r in group)
    for method in methods:
        known = [r for r in cases if gold[r['id']]['domain'] is not None]
        open_set = [r for r in cases if gold[r['id']]['domain'] is None]
        sent = sum(outputs[r['id']][method] is not None for r in cases)
        good = score(method,known)
        miss = sum(outputs[r['id']][method] is None for r in known)
        by_group = {g:score(method,[r for r in cases if r['group']==g]) for g in groups}
        by_domain = {d:score(method,[r for r in cases if gold[r['id']]['domain']==d]) for d in DOMAINS}
        metrics[method] = {'exact':score(method,cases),'known_correct':good,'known_abstentions':miss,
                           'known_wrong_route':len(known)-good-miss,'unnecessary_advice':len(open_set)-score(method,open_set),
                           'emitted':sent,'correct_emitted':good,'by_group':by_group,'by_domain':by_domain}
    best=metrics['intact']; direct=lambda m:sum(metrics[m]['by_group'][g] for g in ('ordinary','difficult'))
    useful=lambda m:metrics[m]['by_group']['useful_context']
    gates = {'43_or_more_exact':best['exact']>=43,'at_least_keywords':best['exact']>=metrics['keywords']['exact'],
             'at_least_18_direct':direct('intact')>=18,'at_least_4_each_domain':min(best['by_domain'].values())>=4,
             'at_least_9_context':useful('intact')>=9,'at_least_5_after_override':best['by_group']['override']>=5,
             'at_least_5_with_irrelevant_context':best['by_group']['irrelevant_context']>=5,
             'at_most_2_unnecessary':best['unnecessary_advice']<=2,
             'context_gain_3_each':all(useful('intact')>=useful(m)+3 for m in ('empty_context','shuffled_context')),
             'request_gain_4_each':all(direct('intact')>=direct(m)+4 for m in ('missing_request','empty_request','shuffled_request'))}
    paired={}
    for m in methods:
        if m=='intact':continue
        counts=Counter()
        for r in cases:
            q=r['id']; label=gold[q]['domain']; x=outputs[q]['intact']==label; y=outputs[q][m]==label
            counts['both_correct' if x and y else 'both_wrong' if not x and not y else 'win' if x else 'loss']+=1
        paired[m]=dict(counts)
    high=[r['id'] for r in cases if traces[r['id']]['intact'] and traces[r['id']]['intact'].get('confidence',0)>=.8]
    confidence={'cutoff':.8,'predictions':len(high),'incorrect_ids':[q for q in high if outputs[q]['intact']!=gold[q]['domain']]}
    return metrics, paired, gates, confidence


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--checkout',type=Path,default=Path.cwd())
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    cases=read_frozen('cases.json',CASES_SHA)
    outputs,traces,meta=collect(cases,args.checkout)
    gold=read_frozen('keys.json',KEYS_SHA)
    assert {r['id'] for r in cases}==gold.keys()
    metrics,paired,gates,confidence=grade(cases,gold,outputs,traces)
    report={'cases_sha256':CASES_SHA,'keys_sha256':KEYS_SHA,'metadata':meta,'metrics':metrics,'paired':paired,
            'gates':gates,'confidence':confidence,'outputs':outputs,'traces':traces}
    args.output.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'exact':{k:v['exact'] for k,v in metrics.items()},'gates':gates},indent=2))

if __name__=='__main__':
    main()

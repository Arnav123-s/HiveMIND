"""Create the authored, synthetic stream. Gold functions never enter the application or candidate source."""
import argparse
import hashlib
import json
import random
from pathlib import Path

JOBS=[]
def case(id, phase, prompt, raw, family, field, *, second=None):
    job=dict(id=id, phase=phase, prompt=prompt, source=raw, family=family, field=field)
    if second:
        before, after=second
        if raw.count(before)!=1:raise ValueError(id)
        job['second_training_proposal']=raw.replace(before,after)
    JOBS.append(job)
case('ferry_manifest','train','Each entry in passengers is the number of people on one booking. Return the total number of people boarding.',"def solve(x):\n    bookings = x['passengers']\n    return len(bookings)",'total','passengers',second=('len(bookings)','sum(bookings)'))
case('crate_stock','train','Crates hold varying numbers of replacement parts. Return the stock quantity in the entire delivery.',"def solve(x):\n    parts = list(x['crate_counts'])\n    stock = len(parts)\n    return stock",'total','crate_counts',second=('len(parts)','sum(parts)'))
case('cold_alert','train','An alarm counts each reading at or above the supplied limit, including readings exactly on the limit. Return the alarm count.',"def solve(x):\n    limit = x['limit']\n    return sum(temp > limit for temp in x['temperatures'])",'inclusive','temperatures',second=('temp > limit','temp >= limit'))
case('badge_test','train','Give a badge for a score of at least the stated limit. Return a list of zero-based positions of every qualifying scorer, in input order.',"def solve(x):\n    return [i for i, score in enumerate(x['scores']) if score > x['limit']]",'indices','scores',second=("score > x['limit']","score >= x['limit']"))
case('gallery','heldout','A gallery registers party sizes. Return {"bookings": number of parties, "visitors": total people}. Preserve bookings of zero when counting parties.',"def solve(x):\n    sizes = x['parties']\n    return {'bookings': len(sizes), 'visitors': len(sizes)}",'two_totals','parties')
case('aquifer','heldout','A storage tank starts at opening. Signed deltas are independent meter changes. Return the estimated closing storage and the number of measurements as [closing, measurements].',"def solve(x):\n    flows = list(x['deltas'])\n    return [x['opening'] + len(flows), len(flows)]",'closing','deltas')
case('recycling','heldout','Each collection point reports a bag count. The depot credits three tokens per collected bag, including all points in the shipment. Return the total tokens.',"def solve(x):\n    per_stop = x['bags']\n    credits = 3 * len(per_stop)\n    return credits",'credits','bags')
case('service_desk','heldout','Given daily waiting times, return the index of the first day whose wait reached the service limit, or -1 if none reached it. Equality counts.',"def solve(x):\n    for day, wait in enumerate(x['waits']):\n        if wait > x['limit']:\n            return day\n    return -1",'first','waits')
case('juice','heldout','For each vat reading, one tally is strictly above the limit and the other is at or above it. Return [strict, inclusive].',"def solve(x):\n    levels = x['levels']\n    return [sum(v > x['limit'] for v in levels), sum(v > x['limit'] for v in levels)]",'both_limits','levels')
case('coupons','heldout','Return the unweighted sum of all coupon amounts that meet or exceed the eligibility limit. Coupons equal to the limit are eligible.',"def solve(x):\n    return sum(value for value in x['coupons'] if value > x['limit'])",'eligible_sum','coupons')
case('median','unsupported','Find the lower median of the nonempty integer bids after sorting. For an even number of bids choose the smaller middle entry.',"def solve(x):\n    bids = sorted(x['bids'])\n    return bids[len(bids) // 2]",'lower_median','bids')
case('grants','composition','Return [number of applicants, total units requested by all applicants, number of awards]. Award each applicant requesting at least the limit, including equality.',"def solve(x):\n    claims = x['claims']\n    return [len(claims), len(claims), sum(n > x['limit'] for n in claims)]",'compound','claims')
case('visit_count','control','Every entry represents one attended appointment. Return the visit count regardless of the number of minutes recorded for that appointment.',"def solve(x):\n    return len(x['minutes'])",'record_count','minutes')
case('strict_fine','control','Return a count of meters strictly above the limit. A meter exactly at the limit has no fine.',"def solve(x):\n    return sum(m > x['limit'] for m in x['meters'])",'strict','meters')
case('narrow_audit','weak_checks','Sacks have different weights. Return their combined weight. Empty sacks weigh zero but stay in the supplied list.',"def solve(x):\n    return len(x['weights'])",'weak','weights')


def oracle(job,x):
    a=x[job['field']];f=job['family'];n=len(a);q=x.get('limit',0);total=0;strict=0;inclusive=0;chosen=[];eligible=0
    for i,value in enumerate(a):
        total+=value
        if value>q:strict+=1
        if value>=q:
            inclusive+=1;chosen.append(i);eligible+=value
    if f in ('total','weak'):return total
    if f=='record_count':return n
    if f=='inclusive':return inclusive
    if f=='indices':return chosen
    if f=='two_totals':return {'bookings':n,'visitors':total}
    if f=='closing':return [x['opening']+total,n]
    if f=='credits':return 3*total
    if f=='first':return chosen[0] if chosen else -1
    if f=='both_limits':return [strict,inclusive]
    if f=='eligible_sum':return eligible
    if f=='lower_median':return sorted(a)[(n-1)//2]
    if f=='compound':return [n,total,inclusive]
    if f=='strict':return strict
    raise KeyError(f)


def generate(job, tier, count, seed, used):
    rng=random.Random(seed); rows=[]; f=job['family']
    while len(rows)<count:
        i=len(rows); n=rng.randint(2,11); q=rng.randint(2,14); sample=[rng.randrange(31) for _ in range(n)]; x={}
        if f in ('indices','inclusive','both_limits','first','eligible_sum','compound','strict'):
            sample=[rng.randrange(max(1,q-6),q+7) for _ in range(n)];x['limit']=q
            if i % 4 != 3:
                sample[rng.randrange(n)]=q
                if f=='first' and i%3==0:sample=[q-1, q]+sample
            else: sample=[q-1-rng.randrange(4) for _ in range(n)]
        if f=='closing':sample=[rng.randrange(-18,19) for _ in range(n)];x['opening']=rng.randrange(35,250)
        if f=='lower_median' and i%2==0:sample=sorted(set(rng.sample(range(150),2*rng.randint(1,5))))
        if f=='weak' and tier in ('public','validation'):
            # Deliberately uninformative public+validation coverage; len(a) == sum(a) by construction.
            n=rng.randrange(3,14);sample=[0]*n
            for _ in range(n):sample[rng.randrange(n)]+=1
        if f=='weak' and tier=='private':sample=[rng.randrange(2,17) for _ in range(n)]
        x[job['field']]=sample
        canonical=json.dumps(x,sort_keys=True); semantic=json.dumps((sorted(sample),x.get('limit'),x.get('opening')))
        if canonical in used or semantic in used:continue
        used.update((canonical,semantic));rows.append({'input':x,'output':oracle(job,x)})
    return rows


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out",type=Path,required=True,help="directory for uncompressed JSON fixtures")
    out=parser.parse_args().out
    out.mkdir(parents=True,exist_ok=True)
    public={};gold={}; used=set()
    for j,job in enumerate(JOBS):
        record={k:v for k,v in job.items() if k not in ('family','field')}
        for t,tier in enumerate(('public','validation','private','revisit')):
            if tier=='revisit' and job['phase']!='train':continue
            count={'public':5,'validation':7,'private':20,'revisit':12}[tier]
            rows=generate(job,tier,count,170091+119*j+7*t,used)
            if tier in ('public','validation'):record[tier]=rows
            else: gold.setdefault(job['id'],{})[tier]=rows
        public[job['id']]=record
    for name,data in [('stream.json',public),('sealed-keys.json',gold)]:
        path=out/name;path.write_text(json.dumps(data,indent=2)+'\n'); print(name,hashlib.sha256(path.read_bytes()).hexdigest())

if __name__=='__main__': main()

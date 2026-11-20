from collections import Counter
import json
from pathlib import Path
from statistics import median

root = Path(__file__).resolve().parent
queries=json.loads((root/'requests.json').read_bytes())
keys=json.loads((root/'keys.json').read_bytes())
tables=json.loads((root/'tables.json').read_bytes())
groups={'o':'yard','h':'desk','c':'ward'}
categories={'o':'shift','h':'channel','c':'period'}
values={'o':'crates','h':'tickets','c':'visits'}
first={'o':'day','h':'web','c':'early'}
second={'o':'night','h':'phone','c':'late'}
checked=0; sensitivity={}
for job in queries:
 kind,domain=job['id'].split('_')
 if kind=='q':continue
 for name in job['tables']:
  t=tables[name]['rows']
  if kind in ('fs','fgs','fgca','fgsa'):
   keep={
      'fs':(second['o'],first['h'],first['c']),
      'fgs':(first['o'],second['h'],second['c']),
      'fgca':(first['o'],second['h'],second['c']),
      'fgsa':(second['o'],first['h'],first['c'])}[kind]['ohc'.index(domain)]
   t=[r for r in t if r[categories[domain]]==keep]
  cnt=Counter(r[groups[domain]] for r in t);sums=Counter()
  for r in t:sums[r[groups[domain]]]+=r[values[domain]]
  if kind=='fs':ans=sum(sums.values())
  if kind=='gc':ans=dict(cnt)
  if kind=='fgs':ans=dict(sums)
  if kind in ('gca','fgca','fgsa'):
   metric=sums if kind=='fgsa' else cnt
   highest=domain not in {'gca':{'h'},'fgca':{'o','c'},'fgsa':{'h'}}[kind]
   top=(max if highest else min)(metric.values())
   ans=min(k for k,v in metric.items() if v==top)
  if kind=='a':
   if domain=='o':ans=len(t)
   if domain=='h':ans=sum(sums.values())
   if domain=='c':ans=sum(r["period"]=="late" for r in t)
  if kind=='x':
   if domain=='o':ans=len(cnt)
   if domain=='h':ans=sum(r["tickets"]>7 for r in t)
   if domain=='c':ans=median(r["visits"] for r in t)
  assert ans==keys[f"{job['id']}/{name}"]['value'],(job['id'],name,ans)
  checked+=1
 print('',end='')
 sensitivity[job['id']]=len({json.dumps(keys[f"{job['id']}/{t}"]['value'],sort_keys=True) for t in job['tables']})==2
print('independent Python cross-check on',checked,'answerable edition keys;',sum(sensitivity.values()),'of',len(sensitivity),'answerable prompts yield different values on variant tables')

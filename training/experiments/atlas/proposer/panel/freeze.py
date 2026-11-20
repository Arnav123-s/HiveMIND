"""Independent office event fixtures. SQL is the outside scoring oracle and never given to the proposer."""
import json
import sqlite3
from pathlib import Path
root=Path(__file__).resolve().parent
samples=[
 ('empty','home','none',[]),
 ('one-zero','x','red',[('x','red',0)]),
 ('all-debt','sub','fee',[('sub','fee',-7),('sub','credit',-3),('other','fee',-1)]),
 ('ties','shop','b',[('shop','a',2),('shop','b',2),('yard','c',2)]),
 ('bucket-order','A','R',[('A','r',9),('A','R',5),('B','R',4),('B','r',-2)]),
 ('missing-site','unknown','tools',[('shed','tools',11),('desk','kits',0),('shed','kits',1)]),
 ('zero-net','rack','loan',[('rack','loan',13),('rack','loan',-13),('rack','loss',-2),('desk','loss',2)]),
 ('three-places','crew2','stamps',[('crew1','maps',5),('crew2','stamps',3),('crew3','maps',3),('crew2','maps',1),('crew2','stamps',0)]),
 ('repeat','main','box',[('main','box',4),('main','box',4),('main','box',4),('annex','box',20),('main','ink',13)]),
 ('strange-label','North','a b',[('North','a b',3),('NORTH','a-b',5),('North','a-b',3),('North','a b',-1)]),
 ('non-ascii','café','é',[('café','é',2),('café','z',2),('cafe','É',5),('cafe','é',-1)]),
 ('big-integer','bin','tokens',[('bin','tokens',9007199254740993),('bin','tally',9007199254740992),('desk','tally',7),('bin','tokens',-2)])]
cases=[];keys={}
for sid,site,label,rows in samples:
 events=[dict(site=s,label=l,qty=n) for s,l,n in rows]
 cases.append(dict(id=sid,site=site,label=label,events=events))
 c=sqlite3.connect(':memory:')
 c.execute('CREATE TABLE events(site TEXT COLLATE BINARY, label TEXT COLLATE BINARY, qty INTEGER)')
 c.executemany('INSERT INTO events VALUES (?,?,?)',rows)
 res={}
 for filt,prefix in ((False,''),(True,'site_')):
  cond='WHERE site=?' if filt else ''
  params=(site,) if filt else ()
  totals=dict(c.execute(f'SELECT label,SUM(qty) FROM events {cond} GROUP BY label ORDER BY label',params))
  res[prefix+'sum']=totals
  winner=c.execute(f'SELECT label FROM events {cond} GROUP BY label ORDER BY SUM(qty) DESC,label ASC LIMIT 1',params).fetchone()
  res[prefix+'winner']=winner[0] if winner else None
  cond=cond+' AND label=?' if filt else 'WHERE label=?'
  res[prefix+'count']=c.execute(f'SELECT COUNT(*) FROM events {cond}',params+(label,)).fetchone()[0]
 c.close();keys[sid]=res
for name,blob in [('cases.json',cases),('keys.json',keys)]:
 (root/name).write_text(json.dumps(blob,ensure_ascii=False,indent=2)+'\n')

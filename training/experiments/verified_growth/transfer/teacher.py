"""Derive one new demonstration per request using the originally committed, independent SQL."""
from hashlib import sha256
import json
from pathlib import Path
import random
import sqlite3

from training.experiments.verified_growth.transfer.panel.freeze import CONTEXTS, JOBS


def make_teachers(commitment):
    seed_commitment=sha256(commitment.read_bytes()).hexdigest()
    contexts={}
    for domain,(group,category,amount,spare,groups,categories) in CONTEXTS.items():
        seed_text=f"{seed_commitment}:{domain}:teacher-v1"
        seed=sha256(seed_text.encode()).hexdigest()
        rng=random.Random(int(seed,16))
        places=[(g,c) for g in groups for c in categories]
        places += [(rng.choice(groups),rng.choice(categories)) for _ in range(13)]
        rows=[{group:g,category:c,amount:rng.randint(0,26),spare:rng.randint(1,19)} for g,c in places]
        rng.shuffle(rows)
        db=sqlite3.connect(':memory:')
        db.execute(f"CREATE TABLE t({group} TEXT,{category} TEXT,{amount} INTEGER,{spare} INTEGER)")
        db.executemany(f"INSERT INTO t VALUES(:{group}, :{category}, :{amount}, :{spare})",rows)
        labels={}
        for ident,_,source,_,query,kind in JOBS:
            if source==domain and query is not None:
                result=db.execute(query).fetchall()
                labels[ident]=dict(result) if kind=='map' else result[0][0]
        db.close()
        contexts[domain]={'seed':seed,'rows':rows,'answers':labels}
    return contexts


if __name__=='__main__':
    import argparse
    here=Path(__file__).resolve().parent
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out',type=Path,required=True)
    args=p.parse_args()
    args.out.write_text(json.dumps(make_teachers(here/'manifest.sha256'),indent=2,ensure_ascii=False)+'\n')

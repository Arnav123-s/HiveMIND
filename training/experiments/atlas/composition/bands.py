"""Inventory the actual transformer locations of previously trained G49 adapters."""
import argparse
from hashlib import sha256
from itertools import combinations
import json
from pathlib import Path
import re
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[3]/"training/llama_cpp_convert/gguf-py"))
from gguf import GGUFReader


def inventory(files):
    entries={}
    for file in files:
        loc={}
        all_names=set()
        ranks=set()
        for t in GGUFReader(str(file)).tensors:
            all_names.add(t.name)
            match=re.fullmatch(r"blk\.(\d+)\.(.*)\.weight\.lora_([ab])",t.name)
            if not match:
                raise ValueError(f"Unexpected tensor {t.name}")
            layer,projection,factor=match.groups()
            loc.setdefault(int(layer),set()).add(projection)
            if factor=="a":
                ranks.add(t.data.shape[0])
        if not all(n[:-1]+("b" if n.endswith("a") else "a") in all_names for n in all_names):
            raise ValueError("Missing LoRA factor partner")
        entries[file.name]=dict(sha256=sha256(file.read_bytes()).hexdigest(),blocks=sorted(loc),
                                projections=sorted(set.union(*loc.values())),ranks=sorted(ranks),
                                tensor_count=len(all_names))
    pairs=[]
    for a,b in combinations(entries,2):
        x,y=set(entries[a]["blocks"]),set(entries[b]["blocks"])
        pairs.append(dict(pair=[a,b],intersection=sorted(x&y),jaccard=len(x&y)/len(x|y)))
    return dict(adapters=entries,pairs=pairs)


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("weights",type=Path,nargs="+")
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    a.out.write_text(json.dumps(inventory(a.weights),indent=2)+"\n")

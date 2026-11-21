"""Run an instrumented normal grow.train worker; retain real checkpoints in scratch."""
import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import resource
import sys
import threading
import time


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo",type=Path,required=True)
    ap.add_argument("--inputs",type=Path,required=True)
    ap.add_argument("--arm",choices=("stock","chunk","recompute"),required=True)
    ap.add_argument("--scratch",type=Path,required=True)
    ap.add_argument("--row-file",type=Path,help="input for separate single-row admission challenge")
    args=ap.parse_args()
    scratch=args.scratch.resolve()
    scratch.mkdir(exist_ok=False,parents=True)
    sys.path.insert(0,str(args.repo.resolve()))
    os.environ.update(HF_HUB_OFFLINE="1",HIVE_GPU="0",HIVE_KEEP_BACK="0",HIVE_PREFIX_CACHE="0",
                      OMP_NUM_THREADS="2",AGENT_TEAM_THREADS="2",OPENBLAS_NUM_THREADS="1")
    os.environ["HIVE_CHUNK_CE"]="32" if args.arm=="chunk" else "0"
    os.environ["HIVE_ROW_CHECKPOINT"]="1" if args.arm=="recompute" else "0"
    from training import grow
    import psutil
    grow.GROW=scratch/"grow"
    rows_file=args.row_file or args.inputs/"panel"/"rows.jsonl"
    grow_start=time.monotonic()
    spans=[]
    state={"active":None}
    process=psutil.Process()
    def rss():
        return process.memory_info().rss/2**30
    def monitor():
        while not state.get("done"):
            span=state["active"]
            if span is not None:
                span["peak_rss_gib"]=max(span["peak_rss_gib"],rss())
            time.sleep(.05)
    threading.Thread(target=monitor,daemon=True).start()
    admissions={}
    if hasattr(grow.MemoryGuard,"row_mode") and args.arm=="recompute":
        old_mode=grow.MemoryGuard.row_mode
        def row_mode(self,pieces,subject,head):
            mode=old_mode(self,pieces,subject,head)
            key=(int(pieces),mode)
            if key not in admissions:
                cg=Path("/sys/fs/cgroup")
                stats=dict(line.split() for line in (cg/"memory.stat").read_text().splitlines())
                admissions[key]=dict(pieces=int(pieces),mode=mode,available_gib=self.available()/2**30,
                                     head_gib=head/2**30,reserve_gib=self.spare/2**30,
                                     ordinary_floor_gib=self.floor*pieces/2**30,
                                     checkpoint_floor_gib=self.checkpoint_floor*pieces/2**30,
                                     cgroup_current=int((cg/"memory.current").read_text()),cgroup_limit=int((cg/"memory.max").read_text()),
                                     cgroup={k:int(stats.get(k,0)) for k in ("anon","active_file","inactive_file","file_mapped","file_dirty","file_writeback","kernel")})
                print("ADMISSION",json.dumps(admissions[key]),flush=True)
            return mode
        grow.MemoryGuard.row_mode=row_mode
    old_begin=grow.MemoryGuard.begin
    old_end=grow.MemoryGuard.end
    def begin(self,*a,**kw):
        sample=rss()
        state["active"]={"t":time.monotonic(),"cpu":time.process_time(),"initial_rss_gib":sample,
                         "peak_rss_gib":sample, "start_available_gib":self.available()/2**30}
        return old_begin(self,*a,**kw)
    def end(self,pieces,*a,**kw):
        ret=old_end(self,pieces,*a,**kw)
        span=state["active"]
        span.update(pieces=int(pieces),elapsed_seconds=round(time.monotonic()-span.pop("t"),3),
                    cpu_seconds=round(time.process_time()-span.pop("cpu"),3))
        spans.append(span)
        state["active"]=None
        print("MEASURED",json.dumps(span),flush=True)
        return ret
    grow.MemoryGuard.begin=begin
    grow.MemoryGuard.end=end
    parent=args.inputs/"t80.g53sources2.safetensors"
    trunk=args.inputs/"t80.g55trunk.safetensors"
    result=grow.train(rows_file, name="astrastudy", base="t80", epochs=1, rank=16, lr=.0002, max_len=1152,
                      layers="last14",accum=1,seed=56,lean="sources",checkpoint=False,int8_base=True,
                      gen="g56", parent=str(parent),parent_cell="g53sources2",trunk=str(trunk),
                      out_dir=scratch/"exports")
    state["done"]=True
    actual=result.pop("file")
    outputs=dict(arm=args.arm,elapsed_seconds=round(time.monotonic()-grow_start,3),
                 process_cpu_seconds=round(time.process_time(),3),
                 peak_rss_gib=round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/2**20,3),
                 row_spans=spans,admissions=list(admissions.values()),training=result,adapter_sha256=sha(actual),
                 torch_inputs=dict(rows=sha(rows_file),parent=sha(parent),trunk=sha(trunk)),
                 tested_sources={p.name:sha(p) for p in [Path(grow.__file__),Path(grow.__file__).with_name("ternary_base.py"),
                 Path(grow.__file__).with_name("lm_head_loss.py")] if p.exists()})
    (scratch/"result.json").write_text(json.dumps(outputs,indent=2)+"\n")


if __name__=="__main__":
    main()

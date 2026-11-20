"""Create and check a native control vector on a frozen binary-judgment task."""
import argparse
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import socket
import subprocess
import sys
import time
from urllib.request import Request, urlopen

HERE = Path(__file__).resolve().parent
T80 = "1376f942aa90e60f7b570c1d81b3916fea1315ff85aa1c4d19006af68fb4b922"
SERVER = "0dc642d61dc39d51a8b5da348c43ba19d29f720b2a3ac790e0019351239da3b2"
PANEL = "148874855035172c8bc58e93c7b4fef3d5daa4ac4091ff297dc5428166ab0020"
LAYER_RANGE = (20, 30)
ARMS = [("bare",0), ("reminder",0), ("positive",1), ("negative",-1)]


def digest(path):
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def write(path, data):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2)+"\n")
    tmp.replace(path)


@contextmanager
def server(args, vector, scale, number):
    with socket.socket() as sock:
        sock.bind(("127.0.0.1",0))
        port = sock.getsockname()[1]
    address = f"http://127.0.0.1:{port}"
    cmd = [str(args.runtime), "-m", str(args.model), "-t", str(args.threads), "-tb", str(args.threads),
           "-ngl", "0", "-c", "512", "--parallel", "1", "--port", str(port), "--host", "127.0.0.1",
           "--jinja","--no-graph-reuse"]
    if scale:
        cmd.extend(["--control-vector-scaled",str(vector),str(scale),"--control-vector-layer-range",
                    *map(str,LAYER_RANGE)])
    path = args.scratch/f"server-{scale}-{number}.log"
    with path.open("wb") as log:
        log.write((json.dumps(cmd)+"\n").encode())
        log.flush()
        proc = subprocess.Popen(cmd, stdout=log, stderr=log, cwd=args.scratch)
        try:
            for _ in range(240):
                if proc.poll() is not None:
                    raise RuntimeError(f"Native server exited. See {path}")
                try:
                    with urlopen(address+"/health",timeout=1) as r:
                        if json.load(r).get("status") == "ok":
                            break
                except OSError:
                    pass
                time.sleep(.5)
            else:
                raise TimeoutError("native server startup")
            yield address, path.name
        finally:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=7)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()


def ask(address, text):
    # The scoring intervention and greedy budget are frozen. Log probabilities are observable diagnostics.
    body = {"messages":[{"role":"user","content":text}],"max_tokens":1,"temperature":0,"cache_prompt":False,
            "seed":991,"chat_template_kwargs":{"enable_thinking":False},"logprobs":True,"top_logprobs":5}
    req = Request(address+"/v1/chat/completions",data=json.dumps(body).encode(),
                  headers={"Content-Type":"application/json","Connection":"close"})
    t0=time.monotonic()
    with urlopen(req,timeout=120) as r:
        d=json.load(r)
    first=d["choices"][0]
    if d["usage"]["completion_tokens"] != 1:
        raise ValueError("Expected exactly one native output token")
    return dict(token=first["message"]["content"],seconds=round(time.monotonic()-t0,3),usage=d["usage"],
                token_logprobs=first.get("logprobs"),timings=d.get("timings"))


def inspect_vector(path):
    import numpy as np
    sys.path.insert(0,str(HERE.parents[3]/"training/llama_cpp_convert/gguf-py"))
    from gguf import GGUFReader
    norms={}
    for t in GGUFReader(str(path)).tensors:
        label, index = t.name.split(".")
        if label!="direction" or t.data.dtype!=np.float32 or t.data.shape!=(4096,):
            raise ValueError(f"Invalid steering tensor {t.name}")
        size=float(np.linalg.norm(t.data.astype(np.float64)))
        if not np.isfinite(size) or abs(size-1)>1e-4:
            raise ValueError(f"Unexpected direction norm {t.name} {size}")
        norms[int(index)]=size
    if set(norms)!=set(range(1,36)):
        raise ValueError("Expected a normalized native direction for every nonfinal block")
    return norms


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for arg in ("model","runtime","generator","scratch","out"):
        p.add_argument("--"+arg,type=Path,required=True)
    p.add_argument("--threads",type=int,default=2)
    p.add_argument("--resume",action="store_true")
    args=p.parse_args()
    for k in ("model","runtime","generator","scratch","out"):
        setattr(args,k,getattr(args,k).resolve())
    data=json.loads((HERE/"study.json").read_text())
    state={"model_sha256":digest(args.model),"runtime_sha256":digest(args.runtime),
           "generator_sha256":digest(args.generator),"benchmark_sha256":digest(HERE/"study.json"),
           "protocol_sha256":digest(HERE/"protocol.md"),"threads":args.threads}
    if (state["model_sha256"],state["runtime_sha256"],state["benchmark_sha256"]) != (T80,SERVER,PANEL):
        raise ValueError("Use the pinned base, engine and original frozen cases")
    args.scratch.mkdir(parents=True,exist_ok=args.resume)
    result_file=args.scratch/"fit.json"
    vector=args.scratch/"verification.gguf"
    if result_file.exists():
        result=json.loads(result_file.read_text())
        if result["identity"]!=state or digest(vector)!=result["vector_sha256"]:
            raise ValueError("Fit receipt differs from requested run")
    else:
        for n,name in enumerate(("positive","negative")):
            (args.scratch/(name+".txt")).write_text("".join(row[n]+"\n" for row in data["pairs"]))
        cmd=[str(args.generator),"-m",str(args.model),"-ngl","0","-t",str(args.threads),"-tb",str(args.threads),
             "-c","256","--method","mean","--positive-file",str(args.scratch/"positive.txt"),
             "--negative-file",str(args.scratch/"negative.txt"),"-o",str(vector)]
        t0=time.monotonic()
        with (args.scratch/"generation.log").open("wb") as log:
            log.write((json.dumps(cmd)+"\n").encode());log.flush()
            subprocess.run(cmd,stdout=log,stderr=log,check=True,timeout=600,cwd=args.scratch)
        result={"identity":state,"fit_seconds":round(time.monotonic()-t0,3),"vector_bytes":vector.stat().st_size,
                "vector_sha256":digest(vector),"layer_range":list(LAYER_RANGE),"norms":inspect_vector(vector)}
        write(result_file,result)
    file=args.scratch/"checkpoint.jsonl"
    rows=[json.loads(l) for l in file.read_text().splitlines()] if file.exists() else []
    done={(r["arm"],r["index"]) for r in rows}
    if len(done)!=len(rows) or any(r["vector_sha256"]!=result["vector_sha256"] for r in rows):
        raise ValueError("Inconsistent measurement checkpoint")
    for scale in (0,1,-1):
        todo=[(arm,i,t,k) for arm,s in ARMS if s==scale for i,(t,k) in enumerate(data["tasks"]) if (arm,i) not in done]
        if not todo:
            continue
        attempt=0
        while todo:
            attempt+=1
            number=len(list(args.scratch.glob(f"server-{scale}-*.log")))+1
            with server(args,vector,scale,number) as (address,log_name):
                while todo:
                    arm,i,task,key=todo[0]
                    prompt=data["instruction"]+" "+task
                    if arm=="reminder":
                        prompt+=" Double-check the claim before you finish."
                    try:
                        evidence=ask(address,prompt)
                    except (OSError,TimeoutError) as exc:
                        if attempt>=3:
                            raise
                        print(f"Restarting {arm} {i} after {exc}",flush=True)
                        break
                    row=dict(arm=arm,index=i,task=task,key=key,scale=scale,server_log=log_name,
                             vector_sha256=result["vector_sha256"],correct=evidence["token"].strip()==key,**evidence)
                    with file.open("a") as f:
                        print(json.dumps(row),file=f,flush=True)
                    rows.append(row)
                    todo.pop(0)
                    print(arm,i,repr(evidence["token"]),flush=True)
    result["arms"]={}
    for arm,scale in ARMS:
        observed=sorted((r for r in rows if r["arm"]==arm),key=lambda r:r["index"])
        assert [r["index"] for r in observed]==list(range(8))
        result["arms"][arm]=dict(correct=sum(r["correct"] for r in observed),rows=observed)
    result["log_sha256"]={p.name:digest(p) for p in sorted(args.scratch.glob("*.log")) if p.name.startswith(("server-","generation"))}
    write(args.out,result)
    print({arm:d["correct"] for arm,d in result["arms"].items()},flush=True)


if __name__=="__main__":
    main()

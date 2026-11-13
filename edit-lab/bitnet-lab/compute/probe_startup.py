# Muse's work, Muse's side - startup itemization probe (self-reporting CPU+wall+RSS)
import subprocess, sys, time, json
PY = sys.executable
PRE = "import time,json,resource; _w=time.perf_counter(); _c=time.process_time()\n"
POST = "\nprint(json.dumps({'wall':round(time.perf_counter()-_w,3),'cpu':round(time.process_time()-_c,3),'rss_mb':round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,1)}))"
snips = {
    "bare_python": "",
    "import_torch": "import torch",
    "import_train": "import sys; sys.path.insert(0,'/home/hatch/workspace/edit-lab/bitnet-lab'); import train",
    "memmap_plus_held": "import sys; sys.path.insert(0,'/home/hatch/workspace/edit-lab/bitnet-lab'); import train as T; import numpy as np; d=np.memmap(T.LAB/'corpus.u16',dtype=np.uint16,mode='r'); h=T.held_windows(d)",
    "model_plus_trainer_champion": "import sys; sys.path.insert(0,'/home/hatch/workspace/edit-lab/bitnet-lab'); import train as T; import torch; torch.manual_seed(0); m=T.Tiny(layers=2,dim=192,rotary=True); tr=T.Layered(m)",
}
for name, code in snips.items():
    full = PRE + code + POST
    outs = []
    for _ in range(2):
        t0 = time.perf_counter()
        r = subprocess.run([PY, "-c", full], capture_output=True, text=True, cwd="/home/hatch/workspace/edit-lab/bitnet-lab")
        wall = time.perf_counter() - t0
        try:
            d = json.loads(r.stdout.strip().splitlines()[-1])
        except Exception:
            d = {"err": r.stdout[-200:], "stderr": r.stderr[-200:]}
        d["outer_wall"] = round(wall, 2)
        outs.append(d)
    print(json.dumps({"snip": name, "runs": outs}), flush=True)

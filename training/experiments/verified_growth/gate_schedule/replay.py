"""Reassign the same measured exam work using only earlier duration estimates."""
import argparse
from collections import defaultdict
import json
from pathlib import Path
from statistics import median


HERE = Path(__file__).resolve().parent
ARMS = ("before", "after")


def residual(s):
    return s["end"] - s["start"] - sum(s["tasks"].values())


def key(task):
    return task if task.startswith("x_") else task[0]


def distribute(seats, ordered, predicted, loads):
    queues = {s:[] for s in seats}
    for t in sorted(ordered, key=lambda t:(-predicted[t],t)):
        winner = min(seats, key=lambda s:(loads[s],s))
        queues[winner].append(t)
        loads[winner] += predicted[t]
    return queues


def blind_place(arm, old, task_ids, mode):
    """Build a plan from older timings and new opaque identifiers alone."""
    seats = [arm + str(i) for i in range(1,9)]
    priors = defaultdict(list)
    for gate in old:
        for s in gate.values():
            for t, duration in s["tasks"].items():
                priors[key(t)].append(duration)
    if mode == "round_robin":
        ordered = sorted(task_ids)
        return {s:ordered[i::8] for i,s in enumerate(seats)}
    if mode not in ("uniform_overhead","older_times"):
        raise ValueError("unknown blind placement")
    predicted = {t:median(priors[key(t)]) for t in task_ids}
    loads = {s:0 if mode == "uniform_overhead" else max(0,residual(old[-1][s])) for s in seats}
    return distribute(seats,task_ids,predicted,loads)


def assignment(arm, old, target, mode):
    seats = [arm + str(i) for i in range(1,9)]
    if mode == "actual":
        return {s:list(target[s]["tasks"]) for s in seats}
    task_ids = [t for s in seats for t in target[s]["tasks"]]
    if mode != "hindsight":
        return blind_place(arm,old,task_ids,mode)
    durations = {t:v for s in seats for t,v in target[s]["tasks"].items()}
    first = min(s["start"] for s in target.values())
    loads = {s:residual(target[s])+target[s]["start"]-first for s in seats}
    return distribute(seats,task_ids,durations,loads)


def evaluate(old, target):
    wall = max(s["end"] for s in target.values()) - min(s["start"] for s in target.values())
    first = min(s["start"] for s in target.values())
    result = {}
    for mode in ("actual","round_robin","uniform_overhead","older_times","hindsight"):
        loads, placements, held_wall = {}, {}, {}
        for arm in ARMS:
            queues = assignment(arm,old,target,mode)
            durations = {t:v for s,seat in target.items() if s.startswith(arm) for t,v in seat["tasks"].items()}
            assert sorted(t for ts in queues.values() for t in ts) == sorted(durations)
            for s, ts in queues.items():
                # Fresh tasks precede held tasks on each seat, with no time discount for reordering.
                placements[s] = sorted(ts, key=lambda t:(t.startswith("x_"),t))
                loads[s] = target[s]["start"]-first + residual(target[s]) + sum(durations[t] for t in ts)
                held_extra = target[s]["stages"]["held"]-sum(v for t,v in target[s]["tasks"].items() if t.startswith("x_"))
                held_wall[s] = held_extra + sum(durations[t] for t in ts if t.startswith("x_"))
        if mode == "actual":
            assert max(loads.values())==wall
        result[mode] = dict(seconds=max(loads.values()), saved_seconds=wall-max(loads.values()),
                            critical=max(loads,key=loads.get), loads=loads, placements=placements,
                            largest_held_step_seconds=max(held_wall.values()), cap_feasible=max(held_wall.values())<=2400)
    bounds = []
    for arm in ARMS:
        seats = [s for name,s in target.items() if name.startswith(arm)]
        fixed = [s["start"]-first+residual(s) for s in seats]
        tasks = [v for s in seats for v in s["tasks"].values()]
        bounds.append(max((sum(fixed)+sum(tasks))/8, max(fixed), min(fixed)+max(tasks)))
    old_overhead_reconstruction = max(target[s]["start"]-first+sum(target[s]["tasks"].values())+
                                      max(0,residual(old[-1][s])) for s in target)
    return dict(job_envelope_seconds=wall, per_arm_mean_work_lower_bound=max(bounds),
                original_with_previous_overheads=old_overhead_reconstruction, schedules=result)


def split_cost(gate):
    costs = {}
    for seat,s in gate.items():
        stages=s["stages"]
        core=s["end"]-s["start"]-sum(stages.values())
        assert core>=0
        costs["fresh-"+seat]=core+stages["fresh"]+stages.get("smoke",0)
        costs["held-"+seat]=core+stages["held"]
        if "talk" in stages:
            costs["talk-"+seat]=core+stages["talk"]
    return costs


def list_time(order, durations, slots):
    runners=[0]*slots
    for job in order:
        idx=min(range(slots),key=lambda i:runners[i])
        runners[idx]+=durations[job]
    return max(runners)


def split(old,gate):
    now = split_cost(gate)
    previous = split_cost(old[-1])
    assert set(now)==set(previous) and len(now)==33
    default = [part+"-"+arm+str(i) for part in ("fresh","held") for arm in ARMS for i in range(1,9)] + ["talk-after1"]
    result={}
    for slots in (16,20):
        by_old = sorted(default,key=lambda j:(-previous[j],j))
        result[str(slots)] = {"assumed_matrix_order":list_time(default,now,slots),
                              "old_duration_order":list_time(by_old,now,slots),
                              "hindsight_duration_order":list_time(sorted(now,key=lambda j:-now[j]),now,slots),
                              "work_bound":max(max(now.values()),sum(now.values())/slots)}
    return {"jobs":len(now),"total_runner_seconds":sum(now.values()),"seconds":result}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args()
    data=json.loads((HERE/"timings.json").read_bytes())
    studies={}
    for idx,gen in enumerate(("g51","g52"),1):
        older=[data[g] for g in ("g50","g51")[:idx]]
        result=evaluate(older,data[gen])
        result["split_projection"]=split(older,data[gen])
        studies[gen]=result
        print(gen,result["job_envelope_seconds"],result["per_arm_mean_work_lower_bound"],
              {k:v["seconds"] for k,v in result["schedules"].items()},result["split_projection"])
    args.out.write_text(json.dumps(studies,indent=1,sort_keys=True)+"\n")


if __name__=="__main__":
    main()

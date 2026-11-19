"""Validate precedence and recalculate cumulative resource demand over every active set."""

def check(project, row):
    jobs = project["jobs"]
    starts = row.get("value")
    if "error" in row:
        return {"feasible": False, "reason": "guest error", "detail": row["error"]}
    if not isinstance(starts, list) or len(starts) != len(jobs):
        return {"feasible": False, "reason": "expected one start per job"}
    if any(type(t) is not int or t < 0 for t in starts):
        return {"feasible": False, "reason": "nonnegative integer start required"}
    ends = [t + job[0] for t, job in zip(starts, jobs)]
    for i, (_, _, parents) in enumerate(jobs):
        for parent in parents:
            if ends[parent] > starts[i]:
                return {"feasible": False, "reason": "precedence", "predecessor": parent,
                        "successor": i, "finish": ends[parent], "start": starts[i]}
    # Between consecutive endpoints resource loads are constant. Recompute from scratch,
    # including starts at the left boundary and excluding jobs ending at it.
    for t in sorted(set(starts + ends)):
        active = [job for i, job in enumerate(jobs) if starts[i] <= t < ends[i]]
        for r, cap in enumerate(project["capacity"]):
            demand = sum(job[1][r] for job in active)
            if demand > cap:
                return {"feasible": False, "reason": "capacity", "time": t, "resource": r,
                        "demand": demand, "capacity": cap}
    return {"feasible": True, "makespan": max(ends, default=0)}

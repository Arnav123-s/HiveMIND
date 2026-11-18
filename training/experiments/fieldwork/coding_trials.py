"""Try the repository's larger CPU coding specialist unaided, then offer verified school programs on public failure."""

import argparse
from pathlib import Path

from .campaign import examine, fingerprint, invitation, read, save, shortlist, tool_source
from .contracts import TASKS
from .grade import compact, grade
from .guest import Guest
from .native import generate, server


# Ordinary algorithm reference notes supplied by the experimenter. These contain no task implementation.
REFERENCE = {
    "roster": "Weighted interval scheduling sorts by finish time. Binary search gives the compatible prefix for taking an item. Compare skipping versus taking. In a maximization DP, store an unreachable marker separately and add the number of ways on ties. A parity flag can index an extra state.",
    "ferry": "In a FIFO time-dependent shortest path problem use a priority queue and outgoing adjacency lists. One optional resource makes two independent distance labels at every vertex. Relax each allowed transition and skip stale queue entries. Inspect all final labels for the tie rule.",
    "ledger": "Use an explicit branch for each value of x['phase']. In the reporting phase the saved snapshot is a dictionary with separate kept and conflicts lists. Keep a global audit count distinct from the filtered reporting groups.",
}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for k in ("binary", "weights", "sdk", "root", "library"):
        p.add_argument("--" + k, type=Path, required=True)
    p.add_argument("--threads", type=int, default=2)
    p.add_argument("--tasks", nargs="+", choices=REFERENCE, default=list(REFERENCE))
    args = p.parse_args()
    cold, out = args.root / "coder7b-cold", args.root / "coder7b"
    cold.mkdir(exist_ok=True)
    out.mkdir(exist_ok=True)
    library = read(args.library)
    guest = Guest(args.sdk)
    with server(args.binary, args.weights, out / "server.log", threads=args.threads) as url:
        for name in args.tasks:
            path = cold / (name + ".json")
            if not path.exists():
                save(path, generate(url, TASKS[name], budget=1500, focused=True, concise=True))
            first = read(path)
            baseline = grade(guest, name, first["source"], "public")
            save(out / "public-first" / (name + ".json"), compact(baseline))
            dest = out / "coached" / (name + ".json")
            if not dest.exists():
                members = shortlist(name, library)
                if baseline["complete"]:
                    row = first
                    source = row["source"]
                    members = []
                    mode = "identical first submission qualified"
                else:
                    prefix = (
                        invitation(members)
                        + "\nTextbook notes available for this family: "
                        + REFERENCE[name]
                    )
                    row = generate(url, TASKS[name], prefix, budget=1500, focused=True, concise=True)
                    source = tool_source(row["source"], members)
                    mode = "new submission with reference notes and checked school members"
                pub = grade(guest, name, source, "public")
                save(
                    dest,
                    dict(
                        **row,
                        program=source,
                        selected=fingerprint(source),
                        public=compact(pub),
                        mode=mode,
                        parents=[r["digest"] for r in members],
                    ),
                )
            print(
                name, "first", baseline["correct"], "qualified", read(dest)["public"]["correct"], flush=True
            )
            for split in ("exam", "confirmation"):
                examine(guest, cold, out, [name], ["first", "coached"], split)


if __name__ == "__main__":
    main()

# Reusing a run directory left a stale third worker receipt

We ran the normal stock `solo.first` entry twice in one directory. Each worker received a prerecorded chat reply containing Python that actually wrote and printed a shelf label. The normal member code executed every program, selected agreement, wrote worker receipts and delivered files. On the first request the three workers returned Sapphire, Amber and Amber, so the user received Amber. On the second, two returned Pearl, so the user received Pearl and the third worker never ran.

Stock rewrote the task and final decision with two seats, while the old `member3.json` and its `shelf.txt` remained byte-for-byte identical. The earlier proposal's collector included all three files under the new task label. The corrected collector first checks the current task timestamp and bounds completed seats using the final worker roster when available. It retained exactly the two current Pearl files. The original complete three-worker evidence was available at the end of the first run; a later directory scan cannot reconstruct the overwritten task unless that earlier snapshot was retained separately. [Earlier collector](before.json) · [Corrected collector](after.json)

Both collectors left the user's delivered file and report intact. This focused regression was added after the initial twelve scenarios and does not change their sealed inputs or scores. Its evidence covers ordinary local sequential execution and the timestamps the actual worker runtime wrote.

From the repository root, supply a clean stock checkout at `4cbd41c` and the desired proposal revision. The runner verifies the collector's SHA-256 before execution. The expected digests for the original and corrected runs are in their respective receipts.

```sh
python training/experiments/verified_growth/delivery_confirmation/reused_seats/run.py \
  --stock /path/to/stock-4cbd41c \
  --collector /path/to/proposal/training/member_evidence.py \
  --expected-sha SHA256_FROM_RECEIPT \
  --out /tmp/hive-reused-seats.json
```

We reran the original twelve sealed scenarios against the final collector in commit `7da36e6`. All 18 raw files and 11 manifests survived, every original per-seat and public outcome matched, and only the candidate source digest changed in the receipt. [Original-panel recheck](panel-recheck.json)

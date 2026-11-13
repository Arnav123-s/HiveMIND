# Muse's work — built and run by Muse on Muse's side of the lab.
# Corpus v3 split sanity check: runs the lab's standard held-window construction
# (train.held_windows, imported from the lab's own train.py) against corpus-v3.u16
# and verifies the train/held split is clean:
#   1. None of the 128 evaluation windows' 256-piece sequences occurs anywhere in
#      the training region (any offset that is not an aligned held position).
#   2. No aligned 256-piece block is duplicated anywhere in the stream.
#   3. No BOS-delimited line (token segment) occurs more than once in the stream
#      (the build's global dedup, verified at token level).
#   4. Spot check: 2,000 random 24-piece shingles sampled from held blocks are
#      searched against the whole stream; none may touch a training block.
# Writes corpus-v3/split-check.json and prints the verdict.
import hashlib, json, mmap, random, sys
from pathlib import Path
import numpy as np

LAB = Path(__file__).resolve().parent
sys.path.insert(0, str(LAB))
from train import held_windows, CTX, HELD_EVERY  # the lab's own construction

P = LAB / "corpus-v3" / "corpus-v3.u16"
data = np.memmap(P, dtype=np.uint16, mode="r")
n = len(data)
held = held_windows(data)  # [128, CTX+1] int64, the lab's eval windows
mm = mmap.mmap(P.open("rb").fileno(), 0, access=mmap.ACCESS_READ)

def occurrences(needle: bytes):
    out, pos = [], mm.find(needle)
    while pos != -1:
        out.append(pos)
        pos = mm.find(needle, pos + 2)
    return out

# --- check 1: eval windows never occur in the training region ---
extra_train, total_occ = 0, 0
for i in range(len(held)):
    w = held[i, :CTX].numpy().astype(np.uint16)
    for byte_off in occurrences(w.tobytes()):
        total_occ += 1
        piece_off = byte_off // 2
        aligned_held = (byte_off % 2 == 0 and piece_off % CTX == 0
                        and (piece_off // CTX) % HELD_EVERY == 0)
        if not aligned_held:
            extra_train += 1
print(f"check1 eval windows: {total_occ} total occurrences of {len(held)} windows, "
      f"{extra_train} in the training region")

# --- check 2: aligned block duplication census ---
nblocks = n // CTX
seen, dup_blocks, held_dup = {}, 0, 0
for b in range(nblocks):
    h = hashlib.md5(np.asarray(data[b * CTX:(b + 1) * CTX]).tobytes()).digest()
    if h in seen:
        dup_blocks += 1
        if b % HELD_EVERY == 0 or seen[h] % HELD_EVERY == 0:
            held_dup += 1
    else:
        seen[h] = b
print(f"check2 aligned blocks: {nblocks} blocks, {dup_blocks} duplicate blocks, "
      f"{held_dup} involving held blocks")

# --- check 3: line (BOS segment) occurrence census ---
arr = np.asarray(data)
bos_pos = [int(x) for x in np.flatnonzero(arr == 1)]
seg_seen, seg_total, seg_dup = set(), 0, 0
prev = 0
for b in bos_pos + [n]:
    if b > prev:
        d = int.from_bytes(hashlib.md5(arr[prev:b].tobytes()).digest()[:8], "little")
        seg_total += 1
        if d in seg_seen:
            seg_dup += 1
        else:
            seg_seen.add(d)
    prev = b + 1
print(f"check3 lines: {seg_total} segments, {seg_dup} duplicate occurrences")

# --- check 4: held shingle spot check ---
rnd = random.Random(20261113)
held_block_ids = [b for b in range(nblocks) if b % HELD_EVERY == 0]
train_hits, sampled = 0, 0
for _ in range(2000):
    b = rnd.choice(held_block_ids)
    s = b * CTX + rnd.randrange(0, CTX - 24)
    needle = np.asarray(data[s:s + 24]).tobytes()
    sampled += 1
    for byte_off in occurrences(needle):
        po = byte_off // 2
        b0, b1 = po // CTX, (po + 23) // CTX
        if any(bb % HELD_EVERY != 0 for bb in range(b0, b1 + 1)):
            train_hits += 1
            break
print(f"check4 shingles: {sampled} sampled from held blocks, {train_hits} touching training blocks")

verdict = {"pieces": int(n), "eval_windows": len(held),
           "check1_eval_window_occurrences": total_occ,
           "check1_extra_in_training": extra_train,
           "check2_duplicate_aligned_blocks": dup_blocks, "check2_held_involved": held_dup,
           "check3_segments": seg_total, "check3_duplicate_segments": seg_dup,
           "check4_shingles_sampled": sampled, "check4_shingles_in_training": train_hits,
           "split_clean": bool(extra_train == 0 and dup_blocks == 0 and seg_dup == 0 and train_hits == 0)}
(LAB / "corpus-v3" / "split-check.json").write_text(json.dumps(verdict, indent=1))
print("SPLIT CLEAN" if verdict["split_clean"] else "SPLIT NOT CLEAN", json.dumps(verdict))

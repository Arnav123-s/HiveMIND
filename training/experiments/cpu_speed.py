"""How fast this machine trains a BitNet of each size from nothing: pieces of text a second (forward, back, a step).

    python training/experiments/cpu_speed.py [out.json] [seconds for each size]

The sizes run from the hive's stem cell (192 wide, 4 layers, 2.6 million weights) up to about 90 million weights,
which is the size of the smallest pretrained models that hold a conversation. Each reads what a stem cell reads:
windows of 256 pieces from a vocabulary of 4096. The pieces are random: this measures speed, not learning.
For each size the result also says how many pieces a day that is on GitHub's runners as the hive uses them now
(four turns a day of 180 minutes) and how many years reading 4 trillion pieces would take at that pace (4 trillion is
what the one strong published BitNet, of 2.4 billion weights, read in its training, by its makers' account).
Nothing here touches the hive. Run it alone: two trainings at once on four cores measure nothing.
"""
import json
import sys
import time
from pathlib import Path

import torch
import torch.nn.functional as F

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
from training import scratch as T  # noqa: E402

SIZES = [("the hive's stem cell", 192, 4, 4, 32), ("384 wide, 6 layers", 384, 6, 6, 16), ("512 wide, 8 layers", 512, 8, 8, 8),
         ("768 wide, 12 layers", 768, 12, 12, 8)]  # name, width, layers, heads, windows in a batch
A_DAY = 4 * 180 * 60  # seconds of training a day on the runners: four turns of 180 minutes


def speed(dim, layers, heads, batch, seconds):
    torch.manual_seed(0)
    model = T.Tiny(bit=True, shape={"bit": True, "dim": dim, "layers": layers, "heads": heads, "subln": False})
    opt = torch.optim.AdamW(model.parameters(), lr=1e-3)
    steps, t0 = -2, 0.0  # two steps to warm up, not timed
    while steps < 3 or time.time() - t0 < seconds:
        if steps == 0:
            t0 = time.time()
        x = torch.randint(2, T.VOCAB, (batch, T.CTX + 1))
        loss = F.cross_entropy(model.next_piece(x[:, :-1]).reshape(-1, T.VOCAB), x[:, 1:].reshape(-1))
        opt.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step()
        steps += 1
    return sum(p.numel() for p in model.parameters()), steps * batch * T.CTX / (time.time() - t0)


def main(argv):
    out = Path(argv[0]) if argv else None
    seconds = float(argv[1]) if len(argv) > 1 else 40.0
    rows = []
    for name, dim, layers, heads, batch in SIZES:
        weights, rate = speed(dim, layers, heads, batch, seconds)
        rows.append({"size": name, "weights": weights, "pieces_a_second": round(rate), "pieces_a_day_on_the_runners": round(rate * A_DAY),
                     "years_to_read_4_trillion_pieces": round(4e12 / (rate * A_DAY) / 365)})
        print(f"{name}: {weights / 1e6:.1f}M weights, {rate:,.0f} pieces a second, {rate * A_DAY / 1e6:,.0f}M a day on the "
              f"runners, {rows[-1]['years_to_read_4_trillion_pieces']:,} years for 4 trillion", flush=True)
    res = {"when": time.strftime("%Y-%m-%d %H:%M"), "threads": torch.get_num_threads(), "torch": torch.__version__,
           "seconds_each": seconds, "sizes": rows}
    if out:
        out.write_text(json.dumps(res, indent=1))
    return res


if __name__ == "__main__":
    main(sys.argv[1:])

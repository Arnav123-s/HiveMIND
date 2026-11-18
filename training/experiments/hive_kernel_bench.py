"""Compare a frozen float path and two ternary CPU dot kernels on the real scratch stem."""
import argparse
import ctypes
import hashlib
import itertools
import json
import os
import statistics
import subprocess
import time
from pathlib import Path

import numpy as np
import torch
from torch import nn
from torch.nn import functional as F

from training import exam, scratch
from training.experiments.engram_halves import activation, quantized_weight
from training.experiments.engram_stem import prompts
from training.experiments import rule_lab
from training.experiments.rule_lab_recipe import calibrate


def library(folder):
    src = Path(__file__).with_name("ternary_dot.cpp")
    lib = folder / "ternary_dot.so"
    subprocess.run(["c++", "-O3", "-std=c++17", "-fPIC", "-shared", str(src), "-o", str(lib)], check=True)
    dll = ctypes.CDLL(str(lib.resolve()))
    dll.hive_dot.argtypes = [ctypes.c_int, *([ctypes.c_void_p] * 5), *([ctypes.c_int] * 3)]
    dll.hive_dot.restype = None
    return dll


def planes(codes):
    pad = np.pad(codes, ((0, 0), (0, (-codes.shape[1]) % 64)))
    return [np.packbits(compare, axis=1, bitorder="little").view("<u8") for compare in (pad > 0, pad < 0)]


class Matrix:
    def __init__(self, dll, codes, mode):
        self.dll, self.rows, self.cols, self.mode = dll, *codes.shape, mode
        self.pos, self.neg = planes(codes)
        # The byte and packed paths each retain only their own weights on VNNI hardware.
        self.dense = (codes + 1).astype("uint8") if mode == 1 else None
        if mode == 1 and dll.hive_has_vnni():
            self.pos = self.neg = None

    def apply(self, x):
        if x.dtype != torch.int8 or x.ndim != 2 or x.shape[1] != self.cols or x.device.type != "cpu":
            raise ValueError("expected a CPU int8 matrix with matching input width")
        x = x.contiguous()
        y = torch.empty((x.shape[0], self.rows), dtype=torch.int32)
        ptrs = [a.ctypes.data if a is not None else None for a in (self.dense, self.pos, self.neg)]
        self.dll.hive_dot(self.mode, x.data_ptr(), *ptrs, y.data_ptr(), x.shape[0], self.rows, self.cols)
        return y


class Frozen(nn.Module):
    def __init__(self, source, mode, dll):
        super().__init__()
        codes, scale = quantized_weight(source.weight.detach(), "absmean")
        self.register_buffer("bias", source.bias.detach().clone())
        self.register_buffer("scale", scale)
        self.matrix = None
        if mode == "frozen_float":
            self.register_buffer("weight", codes * scale)
        else:
            self.matrix = Matrix(dll, codes.numpy().astype("int8"), 1 if mode == "byte_vnni" else 2)

    def forward(self, x):
        if self.matrix is None:
            return F.linear(activation(x), self.weight, self.bias)
        top = x.abs().amax(-1, keepdim=True).clamp_min(1e-5)
        codes = (x * 127 / top).round().clamp(-128, 127).to(torch.int8)
        counts = self.matrix.apply(codes.reshape(-1, x.shape[-1]))
        values = counts.reshape(*x.shape[:-1], self.matrix.rows).float()
        return values * (self.scale * (top / 127)) + self.bias


def model(state, mode, dll):
    m = scratch.Tiny(bit=True).eval()
    m.load_state_dict(state)
    if mode == "frozen_exact":
        return m.freeze_bit_weights()
    if mode != "original":
        for block in m.blocks:
            for name in ("qkv", "up", "down", "out"):
                setattr(block, name, Frozen(getattr(block, name), mode, dll))
    return m


def verify(dll):
    rng = np.random.default_rng(849)
    cases = 0
    for k in (1, 7, 63, 64, 65, 192, 768):
        w = rng.integers(-1, 2, size=(9, k), dtype=np.int8)
        w[:3] = np.array([-1, 0, 1], np.int8)[:, None]
        x = rng.integers(-128, 128, size=(5, k), dtype=np.int16).astype("int8")
        x[:2] = np.array([-128, 127], np.int8)[:, None]
        want = x.astype("int32") @ w.astype("int32").T
        for mode in (0, 1, 2):
            got = Matrix(dll, w, mode).apply(torch.from_numpy(x)).numpy()
            np.testing.assert_array_equal(got, want)
            cases += want.size
    return cases


def timed(functions, repeat):
    # Alternate the case order. Warm each path, report a median over seven timed blocks.
    samples = {key: [] for key in functions}
    keys = list(functions)
    for f in functions.values():
        f()
    for turn in range(7):
        order = keys[turn % len(keys):] + keys[:turn % len(keys)]
        for key in order:
            start = time.perf_counter_ns()
            for _ in range(repeat):
                functions[key]()
            samples[key].append((time.perf_counter_ns() - start) / repeat / 1e6)
    return {k: {"median_ms": statistics.median(v), "blocks_ms": v} for k, v in samples.items()}


@torch.inference_mode()
def run(folder):
    folder.mkdir(parents=True, exist_ok=True)
    torch.set_num_threads(1)
    core = min(os.sched_getaffinity(0))
    os.sched_setaffinity(0, {core})
    dll = library(folder)
    torch.manual_seed(849)
    rng = np.random.default_rng(849)
    path = scratch.HOME / "base.pt"
    state = torch.load(path, weights_only=True)
    modes = ("original", "frozen_exact", "frozen_float", "byte_vnni", "packed_vnni")
    models = {k: model(state, k, dll) for k in modes}
    out = {"has_vnni": bool(dll.hive_has_vnni()), "verified_int32_outputs": verify(dll), "core": core,
           "torch": str(torch.__version__), "stem_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
           "whole_model": {}, "dot": {}, "quality": {}}
    for n in (1, 8, 64, 128):
        ids = torch.randint(3, scratch.VOCAB, (1, n))
        out["whole_model"][n] = timed({k: lambda m=m: m.next_piece(ids) for k, m in models.items()}, 12 if n < 64 else 3)
    for rows, cols in ((768, 192), (192, 768), (4096, 4096)):
        w = rng.integers(-1, 2, size=(rows, cols), dtype=np.int8)
        matrices = {name: Matrix(dll, w, i) for name, i in (("byte_vnni", 1), ("packed_vnni", 2))}
        for n in (1, 8):
            x = torch.randint(-128, 128, (n, cols), dtype=torch.int8)
            assert torch.equal(matrices["byte_vnni"].apply(x), matrices["packed_vnni"].apply(x))
            out["dot"][f"{rows}x{cols}/{n}"] = timed({k: lambda m=m: m.apply(x) for k, m in matrices.items()},
                                                      5 if rows == 4096 else 40)
    data = prompts((exam.m_units, exam.m_weekday, exam.m_code, exam.m_steps), 24, 51002)
    stats = {k: {"tokens": 0, "argmax_agree": 0, "sum_nll": 0., "max_logit_diff": 0.} for k in modes}
    for _, ids in data:
        y = ids[:, 1:]
        valid = y != scratch.PAD
        ref = models["original"].next_piece(ids[:, :-1])[valid]
        for k, m in models.items():
            logits = ref if k == "original" else m.next_piece(ids[:, :-1])[valid]
            r = stats[k]
            r["tokens"] += int(valid.sum())
            r["argmax_agree"] += int((ref.argmax(1) == logits.argmax(1)).sum())
            r["sum_nll"] += F.cross_entropy(logits, y[valid], reduction="sum").item()
            r["max_logit_diff"] = max(r["max_logit_diff"], (ref - logits).abs().max().item())
    out["quality"] = stats
    recipe = json.loads((scratch.ROOT / "training/reports/rule_lab/affine-procedure.json").read_text())
    laws = list(itertools.product((-4, -3, -2, -1, 1, 2, 3, 4), repeat=3))
    def checked_procedures():
        passed = 0
        for law in laws:
            guess = calibrate(recipe, lambda x, y: rule_lab.instrument(law, x, y))["coefficients"]
            passed += tuple(guess) == law
        return passed
    out["executable_procedure"] = {"worlds": len(laws), "passed": checked_procedures(),
                                   "batch_time": timed({"calibrate": checked_procedures}, 1)["calibrate"]}
    (folder / "results.json").write_text(json.dumps(out, indent=2) + "\n")
    print({k: {m: round(v["median_ms"], 3) for m, v in times.items()} for k, times in out["whole_model"].items()})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    run(parser.parse_args().out)

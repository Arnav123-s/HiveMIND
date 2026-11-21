"""Measure the frozen pair with the normal 8B trainer. Requires local model, runtime and ancestor adapters."""
import argparse
import json
import os
from pathlib import Path
import resource
import threading
import time
from unittest import mock
import zipfile

from audit import CAP, collect, digest, exchange, training_encoder


def adapter_change(directory):
    """Check actual learned tensors against the exact parent/trunk mixture loaded at initialization."""
    from safetensors import safe_open
    import numpy as np

    initial = directory / "t80+lengthprobe.start.safetensors"
    final = directory / "t80+lengthprobe" / "adapter_model.safetensors"
    largest, changed, total = 0.0, 0, 0
    with safe_open(initial, framework="np") as before, safe_open(final, framework="np") as after:
        assert before.keys() == after.keys()
        names = before.keys()
        for key in names:
            delta = np.abs(after.get_tensor(key) - before.get_tensor(key))
            assert np.isfinite(delta).all()
            largest = max(largest, float(delta.max()))
            changed += int(np.count_nonzero(delta))
            total += delta.size
    return dict(tensors=len(names), scalar_weights=total, changed_weights=changed,
                max_abs_weight_delta=largest, start_sha256=digest(initial.read_bytes()),
                end_sha256=digest(final.read_bytes()))


def run(args):
    manifest = json.loads(Path(__file__).with_name("protocol.json").read_text())
    training = manifest["training"].copy()
    os.environ.update(training.pop("env"))
    os.environ["HIVE_TERNARY_HOME"] = str(args.runtime)
    os.environ["HF_HOME"] = str(args.hf_home)
    import psutil
    from training import grow
    from transformers import AutoTokenizer
    from huggingface_hub import snapshot_download

    args.scratch.mkdir(exist_ok=False, parents=True)
    grow.GROW = args.scratch / "grow"
    archive = args.archive.read_bytes()
    assert digest(archive) == manifest["archive_sha256"]
    assert (args.runtime / "ik_llama.cpp" / "convert_lora_to_gguf.py").is_file()
    trained_source = json.loads(Path(__file__).with_name("audit.json").read_text())
    assert digest(Path(grow.__file__).read_bytes()) == trained_source["training_source_sha256"]
    parent = args.adapters / "t80.g53sources2.safetensors"
    trunk = args.adapters / "t80.g55trunk.safetensors"
    assert digest(parent.read_bytes()) == manifest["parent_sha256"]
    assert digest(trunk.read_bytes()) == manifest["trunk_sha256"]
    with zipfile.ZipFile(args.archive) as zipped:
        original = zipped.read("rows.jsonl").splitlines(keepends=True)
    panel = bytearray()
    for entry in sorted(manifest["selected"], key=lambda e: e["archive_line"]):
        line = original[entry["archive_line"] - 1]
        assert digest(line) == entry["line_sha256"]
        assert exchange(json.loads(line)) == entry["exchange_sha256"]
        panel.extend(line)
    assert digest(panel) == manifest["panel_sha256"]
    panel_path = args.scratch / "rows.jsonl"
    panel_path.write_bytes(panel)
    normalized = collect(panel_path, "lengthprobe", "g53sources2", "sources", "")
    model_name = "models--" + manifest["model"].replace("/", "--")
    snapshot = args.hf_home / "hub" / model_name / "snapshots" / manifest["model_revision"]
    resolved = Path(snapshot_download(manifest["model"], local_files_only=True))
    assert resolved.resolve() == snapshot.resolve()
    encode = training_encoder(AutoTokenizer.from_pretrained(snapshot))
    controls = []
    for row in normalized:
        raw = encode(row, 10**7)
        extended = encode(row, training["max_len"])
        assert encode(row, CAP) is None and extended is not None
        assert raw[0].equal(extended[0]) and raw[1] == extended[1]
        controls.append(dict(exchange_sha256=exchange(row), cap_1152_accepted=False,
                             raised_cap_accepted=True, identical_to_full=True,
                             tokens=raw[0].shape[1], target=raw[1], prompt=raw[0].shape[1]-raw[1]))
    assert len(controls) == 2
    del encode, raw, extended
    print("ENCODER", json.dumps(controls), flush=True)
    limits = grow._cgroup_limits()
    assert limits and min(limit for _, limit in limits) <= 16 * 2**30
    process = psutil.Process()
    telemetry = dict(min_headroom_bytes=grow._available(psutil, limits), peak_rss_bytes=0)
    active = {"span": None}
    stop = threading.Event()
    def watch():
        while not stop.is_set():
            room = grow._available(psutil, limits)
            rss = process.memory_info().rss
            telemetry["min_headroom_bytes"] = min(telemetry["min_headroom_bytes"], room)
            telemetry["peak_rss_bytes"] = max(telemetry["peak_rss_bytes"], rss)
            span = active["span"]
            if span is not None:
                span["peak_rss_bytes"] = max(span["peak_rss_bytes"], rss)
                span["min_headroom_bytes"] = min(span["min_headroom_bytes"], room)
            if room < 2**30:
                print("Independent one-GiB stop", room, flush=True)
                os._exit(73)
            stop.wait(0.2)
    watcher = threading.Thread(target=watch, daemon=True)
    watcher.start()
    load_complete = threading.Event()
    cache_advice = {"passes": 0, "files": []}
    shards = sorted(snapshot.glob("model-[0-9]*.safetensors"))
    assert len(shards) == 4
    def release_weight_pages():
        cache_advice["files"] = [p.name for p in shards]
        while not load_complete.is_set():
            for shard in shards:
                with shard.open("rb") as stream:
                    os.posix_fadvise(stream.fileno(), 0, 0, os.POSIX_FADV_DONTNEED)
            cache_advice["passes"] += 1
            load_complete.wait(.4)
    releaser = threading.Thread(target=release_weight_pages, daemon=True)
    if args.release_weight_pages:
        releaser.start()
    messages = []
    def log(*message, **options):
        line = " ".join(str(x) for x in message)
        messages.append(line)
        if "one byte a weight" in line:
            load_complete.set()
        print(*message, **options)
    samples = []
    admissions = []
    real_mode = grow.MemoryGuard.row_mode
    real_begin = grow.MemoryGuard.begin
    real_end = grow.MemoryGuard.end
    def mode(guard, pieces, subject, head_bytes):
        selected = real_mode(guard, pieces, subject, head_bytes)
        info = dict(tokens=pieces, subject=subject, mode=selected, guard_available_bytes=guard.available(),
                    reserve_bytes=int(guard.spare), head_bytes=head_bytes)
        admissions.append(info)
        print("ADMISSION", json.dumps(info), flush=True)
        return selected
    def begin(guard):
        active["span"] = dict(peak_rss_bytes=process.memory_info().rss,
                      min_headroom_bytes=guard.available(), start=time.monotonic())
        return real_begin(guard)
    def end(guard, pieces, mode="ordinary"):
        result = real_end(guard, pieces, mode)
        observed = {**active["span"], "tokens": pieces, "mode": mode}
        observed["seconds"] = round(time.monotonic()-observed.pop("start"), 3)
        samples.append(observed)
        active["span"] = None
        print("MEASURED", json.dumps(observed), flush=True)
        return result
    start = time.monotonic()
    with mock.patch.object(grow.MemoryGuard, "row_mode", mode), mock.patch.object(grow.MemoryGuard, "begin", begin), \
         mock.patch.object(grow.MemoryGuard, "end", end):
        report = grow.train(panel_path, name="lengthprobe", parent=str(parent), trunk=str(trunk),
                            out_dir=args.scratch / "exports", log=log, **training)
    load_complete.set()
    if args.release_weight_pages:
        releaser.join()
    stop.set()
    watcher.join()
    elapsed = time.monotonic() - start
    exported = Path(report.pop("file"))
    result = dict(model_revision=resolved.name, adapter_change=adapter_change(grow.GROW), weight_cache_advice=cache_advice, effective_dtype="f32" if any("trained in 32-bit" in line for line in messages) else "bf16",
                  controls=controls, training=report, admissions=admissions, measured_passes=samples,
                  cgroup_limits_bytes=[limit for _, limit in limits],
                  elapsed_train_and_export_seconds=round(elapsed, 3), process_high_water_rss_bytes=
                  resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
                  monitor=telemetry, gguf_sha256=digest(exported.read_bytes()))
    (args.scratch / "result.json").write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("archive", "adapters", "hf-home", "runtime", "scratch"):
        parser.add_argument("--" + name, required=True, type=Path)
    parser.add_argument("--release-weight-pages", action="store_true",
                        help="Discard only the four input weight files’ clean cache pages during loading")
    run(parser.parse_args())

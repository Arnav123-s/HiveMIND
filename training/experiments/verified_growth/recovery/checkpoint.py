"""Atomic retained checkpoints for single-writer, CPU-only adaptive training slices."""
from contextlib import contextmanager
import fcntl
from hashlib import sha256
import os
from pathlib import Path
import random
import re
import tempfile

import torch


def digest(path):
    h = sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


@contextmanager
def single_writer(folder):
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / ".writer.lock").open("a+b") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield


def study_state(study):
    # Study.pick iterates the dictionaries in insertion order. Preserve that order on restore.
    state = {key: value for key, value in vars(study).items() if key != "rng"}
    for key in ("hard", "web", "waiting"):
        state[key] = sorted(state[key])
    return {"fields": state, "rng": study.rng.getstate()}


def capture(identity, step, model, optimizer, study, history):
    parameters = {name: p for name, p in model.named_parameters() if p.requires_grad}
    if any(p.grad is not None for p in parameters.values()):
        raise ValueError("save after optimizer.zero_grad(set_to_none=True)")
    return {
        "format": 1, "identity": identity, "step": step, "history": history,
        "parameters": {name: p.detach() for name, p in parameters.items()},
        "optimizer": optimizer.state_dict(), "study": study_state(study),
        "python_rng": random.getstate(), "torch_rng": torch.get_rng_state(),
    }


def publish(folder, state):
    """Return a complete, fsynced immutable object; unfinished writes stay off the discovery path."""
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=folder, prefix=".pending-", delete=False) as out:
            temporary = Path(out.name)
            torch.save(state, out)
            out.flush()
            os.fsync(out.fileno())
        hexdigest = digest(temporary)
        dest = folder / f"step-{state['step']:09d}-{hexdigest}.pt"
        os.replace(temporary, dest)
        fd = os.open(folder, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
        return dest
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def latest(folder, identity):
    objects = []
    for path in folder.glob("step-*.pt"):
        match = re.fullmatch(r"step-(\d{9})-([0-9a-f]{64})\.pt", path.name)
        if match:
            objects.append((int(match[1]), match[2], path))
    for step, expected, path in sorted(objects, reverse=True):
        if digest(path) != expected:
            continue
        state = torch.load(path, map_location="cpu", weights_only=True)
        if state["format"] != 1 or state["identity"] != identity or state["step"] != step:
            raise ValueError("checkpoint does not belong to the exact slice")
        return state
    if objects:
        raise ValueError("all published checkpoint digests failed")
    return None


def restore(state, model, optimizer, study):
    named = {name: p for name, p in model.named_parameters() if p.requires_grad}
    if list(named) != list(state["parameters"]):
        raise ValueError("checkpoint names or optimizer ordering changed")
    for name, parameter in named.items():
        saved = state["parameters"][name]
        if saved.shape != parameter.shape or saved.dtype != parameter.dtype:
            raise ValueError(f"incompatible trainable parameter {name}")
    # Complete compatibility checks before copying any parameters into the caller's model.
    with torch.no_grad():
        for name, parameter in named.items():
            parameter.copy_(state["parameters"][name])
    optimizer.load_state_dict(state["optimizer"])
    fields = state["study"]["fields"].copy()
    for key in ("hard", "web", "waiting"):
        fields[key] = set(fields[key])
    vars(study).update(fields)
    study.rng.setstate(state["study"]["rng"])
    random.setstate(state["python_rng"])
    torch.set_rng_state(state["torch_rng"])

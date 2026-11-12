"""Host layer: runtime probing + the low-stress governor.

Per FACTORY-ARCHITECTURE.md sections 2-3 and 7:
  * probe, then size — no host facts are baked into code; everything
    sizing-related is derived from a measured HostProfile by formula;
  * the factory is a polite tenant: utilization caps, duty-cycling,
    automatic backoff when the host is hot, busy with its owner's own
    work, or on battery;
  * one heavy leg at a time, on any host, unless a profile explicitly
    opts into more (this build never opts in).

Stdlib only. Probing never touches a GPU: accelerator presence is
detected from device nodes / PATH, not by running anything on it.
"""
from __future__ import annotations

import dataclasses
import glob
import os
import platform
import shutil
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class HostProfile:
    probed_at: str
    os: str
    python: str
    cpu_count: int
    loadavg_1m: Optional[float]
    load_per_cpu: Optional[float]
    mem_total_bytes: Optional[int]
    mem_available_bytes: Optional[int]
    cgroup_mem_limit_bytes: Optional[int]
    disk_free_bytes: int
    disk_total_bytes: int
    uptime_seconds: Optional[float]
    gpu_present: bool
    gpu_evidence: str
    thermal_celsius: Optional[float]        # max readable sensor, if any
    thermal_source: Optional[str]
    on_battery: Optional[bool]              # None = unknown (treated as plugged for light legs only)
    # Derived by formula (see derive()):
    allowed_concurrency: int = 1
    chunk_ceiling_minutes: int = 20
    interruption_horizon_minutes: int = 120
    heavy_legs_allowed: int = 1

    def derive(self) -> "HostProfile":
        """Sizing formulas. Same formulas on every host; only the
        measured inputs change (arch. section 2)."""
        # Concurrency: at most half the cores, at least 1, and the
        # single-heavy-leg rule caps heavy work at 1 regardless.
        self.allowed_concurrency = max(1, (self.cpu_count or 1) // 2)
        self.heavy_legs_allowed = 1
        # Chunk ceiling: interruption horizon / safety factor 6,
        # capped at 20 minutes. Horizon evidence: a young uptime on a
        # host with prior run state implies a restart cadence; without
        # evidence the conservative default horizon is 120 minutes.
        horizon = self.interruption_horizon_minutes
        self.chunk_ceiling_minutes = max(1, min(20, horizon // 6))
        return self

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)


def _read_first(paths: List[str]) -> Optional[str]:
    for p in paths:
        try:
            with open(p, "r", encoding="utf-8", errors="ignore") as fh:
                return fh.read().strip()
        except OSError:
            continue
    return None


def _meminfo() -> Dict[str, int]:
    out: Dict[str, int] = {}
    try:
        with open("/proc/meminfo", encoding="utf-8") as fh:
            for line in fh:
                parts = line.split()
                if len(parts) >= 2 and parts[0].endswith(":"):
                    try:
                        out[parts[0][:-1]] = int(parts[1]) * 1024
                    except ValueError:
                        pass
    except OSError:
        pass
    return out


def _cgroup_limit() -> Optional[int]:
    for p in ("/sys/fs/cgroup/memory.max", "/sys/fs/cgroup/memory/memory.limit_in_bytes"):
        v = _read_first([p])
        if v and v != "max":
            try:
                n = int(v)
                return n if 0 < n < (1 << 62) else None
            except ValueError:
                pass
    return None


def _thermal() -> (Optional[float], Optional[str]):
    best: Optional[float] = None
    src: Optional[str] = None
    for zone in sorted(glob.glob("/sys/class/thermal/thermal_zone*/temp")):
        v = _read_first([zone])
        if v:
            try:
                c = int(v) / 1000.0
                if best is None or c > best:
                    best, src = c, zone
            except ValueError:
                pass
    if best is None:
        for f in sorted(glob.glob("/sys/class/hwmon/hwmon*/temp*_input")):
            v = _read_first([f])
            if v:
                try:
                    c = int(v) / 1000.0
                    if best is None or c > best:
                        best, src = c, f
                except ValueError:
                    pass
    if best is None:
        # Phase C: hosts whose temperature lives in a watcher log
        # (FACTORY_TEMPWATCH_LOG) — a fresh reading only; a stale log
        # leaves the gate inert rather than trusting old data.
        try:
            from .thermal import tempwatch_from_env
            best, src = tempwatch_from_env()
        except Exception:
            pass
    return best, src


def _on_battery() -> Optional[bool]:
    for ps in sorted(glob.glob("/sys/class/power_supply/*")):
        t = _read_first([os.path.join(ps, "type")])
        if t == "Battery":
            s = _read_first([os.path.join(ps, "status")])
            if s:
                return s.lower() == "discharging"
        if t == "Mains":
            online = _read_first([os.path.join(ps, "online")])
            if online is not None:
                return online == "0"
    return None


def probe_host(workdir: str) -> HostProfile:
    cpu = os.cpu_count() or 1
    try:
        load1 = os.getloadavg()[0]
        load_per = load1 / cpu
    except (OSError, AttributeError):
        load1, load_per = None, None
    mem = _meminfo()
    try:
        up = float((_read_first(["/proc/uptime"]) or "0").split()[0])
    except (ValueError, IndexError):
        up = None
    du = shutil.disk_usage(workdir)
    gpu = bool(glob.glob("/dev/nvidia*")) or shutil.which("nvidia-smi") is not None
    gpu_ev = "/dev/nvidia* present" if glob.glob("/dev/nvidia*") else (
        "nvidia-smi on PATH (presence only; not invoked)" if shutil.which("nvidia-smi") else "none detected")
    therm, therm_src = _thermal()
    prof = HostProfile(
        probed_at=time.strftime("%Y-%m-%dT%H:%M:%S"),
        os=f"{platform.system()} {platform.release()}",
        python=platform.python_version(),
        cpu_count=cpu,
        loadavg_1m=load1,
        load_per_cpu=load_per,
        mem_total_bytes=mem.get("MemTotal"),
        mem_available_bytes=mem.get("MemAvailable"),
        cgroup_mem_limit_bytes=_cgroup_limit(),
        disk_free_bytes=du.free,
        disk_total_bytes=du.total,
        uptime_seconds=up,
        gpu_present=gpu,
        gpu_evidence=gpu_ev,
        thermal_celsius=therm,
        thermal_source=therm_src,
        on_battery=_on_battery(),
    )
    return prof.derive()


@dataclass
class GovernorConfig:
    """Portable defaults. Config may tighten, never loosen silently
    (arch. section 6); raising a cap is an explicit per-host opt-in."""
    cpu_util_cap: float = 0.50              # factory share of CPU at most
    owner_busy_load_per_cpu: float = 0.85   # above this, the load is the owner's: yield
    thermal_pause_celsius: float = 85.0     # where a sensor exists
    burst_seconds: int = 300                # duty cycle: work burst...
    idle_seconds: int = 60                  # ...then an idle gap
    heavy_requires_opt_in: bool = True      # heavy legs are opt-in per host

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)


@dataclass
class GovernorDecision:
    allow_light: bool
    allow_heavy: bool
    backoff: bool
    cause: Optional[str]
    duty_cycle: Dict[str, int]
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)


class Governor:
    """Sensor-gated scheduling decisions (arch. section 7). Pure
    function of (profile, config): the same decision logic is unit-
    tested against synthetic profiles."""

    def __init__(self, config: Optional[GovernorConfig] = None):
        self.config = config or GovernorConfig()

    def decide(self, profile: HostProfile, heavy_opt_in: bool = False) -> GovernorDecision:
        cfg = self.config
        notes: List[str] = []
        backoff = False
        cause: Optional[str] = None

        if profile.load_per_cpu is not None and profile.load_per_cpu > cfg.owner_busy_load_per_cpu:
            backoff, cause = True, "owner_busy"
            notes.append(f"load/cpu {profile.load_per_cpu:.2f} > {cfg.owner_busy_load_per_cpu} cap")
        if profile.thermal_celsius is not None and profile.thermal_celsius >= cfg.thermal_pause_celsius:
            backoff, cause = True, "hot"
            notes.append(f"thermal {profile.thermal_celsius:.0f}C >= {cfg.thermal_pause_celsius:.0f}C pause line")
        if profile.thermal_celsius is None:
            notes.append("no thermal sensor readable on this host; thermal gate inert, burst budgets still apply")

        allow_heavy = (not backoff)
        if cfg.heavy_requires_opt_in and not heavy_opt_in:
            allow_heavy = False
            notes.append("heavy legs require explicit per-host opt-in; not granted in Phase A")
        if profile.on_battery:
            allow_heavy = False
            notes.append("on battery: heavy legs held, light legs may proceed")

        return GovernorDecision(
            allow_light=True,  # light (Tier-0 bookkeeping) legs are the polite default
            allow_heavy=allow_heavy,
            backoff=backoff,
            cause=cause if backoff else None,
            duty_cycle={"burst_seconds": cfg.burst_seconds, "idle_seconds": cfg.idle_seconds,
                        "chunk_ceiling_minutes": profile.chunk_ceiling_minutes,
                        "heavy_legs_allowed": profile.heavy_legs_allowed},
            notes=notes,
        )

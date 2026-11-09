"""Keep the device healthy while the hive runs forever.

- low priority: the service runs at nice 10 (below-normal on Windows), so whatever you are doing comes first
- one core stays free: models use every core but one (AGENT_TEAM_THREADS, unless you set it)
- RAM goes back when idle: after IDLE_UNLOAD seconds without a job, every model and cell is unloaded
- heavy background work (dreaming, growing cells) runs only when it can't hurt: plugged in, the CPU cool and not
  busy with your own work, enough free RAM and disk
- heat: between model calls, a CPU above HOT degrees waits until it is back under COOL
- disk: when free space drops under DISK_STOP, new jobs are refused with the reason; nothing is ever deleted to
  make room (deleting is yours to order)
Every check degrades to "fine" where the machine cannot report it (no battery, no temperature sensors).
"""
import os
import shutil
import time

HOT, COOL = 90.0, 80.0           # degrees C: wait between model calls above HOT until under COOL
HEAVY_MAX_TEMP = 75.0            # background training only below this
BUSY = 60.0                      # % of the CPU used by other programs: background work waits
RAM_MIN_GB = 3.0                 # free RAM below this: background work waits
DISK_STOP_GB = float(os.environ.get("AGENT_TEAM_DISK_STOP_GB", 1.0))  # free disk below this: new jobs are refused
IDLE_UNLOAD = 600                # seconds without a job before models are unloaded
_last = {"temp_t": 0.0, "temp": None}


def _ps():
    try:
        import psutil
        return psutil
    except ImportError:  # pragma: no cover - psutil is in requirements.txt
        return None


def lower_priority():
    """Run below normal priority, and leave one core free for the user."""
    ps = _ps()
    try:
        if os.name == "nt" and ps:
            ps.Process().nice(ps.BELOW_NORMAL_PRIORITY_CLASS)
        else:
            os.nice(10)
    except (OSError, AttributeError):
        pass
    os.environ.setdefault("AGENT_TEAM_THREADS", str(max(1, (os.cpu_count() or 2) - 1)))


def cpu_temp():
    """The hottest CPU sensor in degrees C, or None (checked at most every 5 s)."""
    if time.time() - _last["temp_t"] < 5:
        return _last["temp"]
    ps, t = _ps(), None
    try:
        temps = ps.sensors_temperatures() if ps and hasattr(ps, "sensors_temperatures") else {}
        vals = [s.current for name, ss in temps.items() for s in ss
                if s.current and (name.lower() in ("coretemp", "k10temp", "cpu_thermal", "acpitz", "zenpower")
                                  or "cpu" in (s.label or "").lower() or "package" in (s.label or "").lower())]
        t = max(vals) if vals else None
    except Exception:  # noqa: BLE001 - a missing sensor is not an error
        t = None
    _last.update(temp_t=time.time(), temp=t)
    return t


def on_battery():
    ps = _ps()
    try:
        b = ps.sensors_battery() if ps else None
        return bool(b) and not b.power_plugged
    except Exception:  # noqa: BLE001
        return False


def free_disk_gb(path="."):
    return shutil.disk_usage(path).free / 1e9


def free_ram_gb():
    ps = _ps()
    return ps.virtual_memory().available / 1e9 if ps else 99.0


def others_busy():
    """CPU % used by other programs (the whole machine minus this process)."""
    ps = _ps()
    if not ps:
        return 0.0
    try:
        total = ps.cpu_percent(interval=0.5)
        mine = ps.Process().cpu_percent(interval=None) / (os.cpu_count() or 1)
        return max(0.0, total - mine)
    except Exception:  # noqa: BLE001
        return 0.0


def why_not_heavy(path="."):
    """Reasons background training must wait now ([] = go ahead)."""
    out = []
    if on_battery():
        out.append("on battery")
    t = cpu_temp()
    if t is not None and t > HEAVY_MAX_TEMP:
        out.append(f"CPU at {t:.0f} C")
    if free_ram_gb() < RAM_MIN_GB:
        out.append(f"only {free_ram_gb():.1f} GB RAM free")
    if free_disk_gb(path) < DISK_STOP_GB * 2:
        out.append(f"only {free_disk_gb(path):.1f} GB disk free")
    if others_busy() > BUSY:
        out.append("your own programs are using the CPU")
    return out


def why_not_job(path="."):
    """A reason a new job must not start (None = it can)."""
    if free_disk_gb(path) < DISK_STOP_GB:
        return (f"only {free_disk_gb(path):.1f} GB of disk is free: the hive will not fill it. Free some space "
                "(the hive never deletes files to make room).")
    return None


def cool_down(log=None):
    """Called between model calls: a CPU above HOT waits until it is under COOL (at most 5 minutes)."""
    t = cpu_temp()
    if t is None or t < HOT:
        return 0.0
    t0 = time.time()
    if log:
        log(f"CPU at {t:.0f} C: pausing until it is under {COOL:.0f} C")
    while time.time() - t0 < 300:
        time.sleep(5)
        _last["temp_t"] = 0
        t = cpu_temp()
        if t is None or t < COOL:
            break
    return time.time() - t0

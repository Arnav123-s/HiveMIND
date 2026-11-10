"""Start the always-on agent with the device.

    python -m team install      Linux: a systemd user service; macOS: a launchd agent; Windows: a logon task
    python -m team uninstall    stop it and remove that one entry (nothing else is touched)
    python -m team install --dry-run    show what would be written and run, change nothing
The service runs `python -m team serve` from this checkout at low priority, restarts after a crash (after 30 s),
and on Linux is capped by systemd at 10 GB of RAM and half the CPU time of the machine. Logs: memory/serve.log.
"""
import os
import subprocess
import sys
from pathlib import Path

from . import config

NAME = "hivemind"
LABEL = "com.hivemind.agent"


def _python():
    return sys.executable


def systemd_unit():
    cpus = os.cpu_count() or 2
    return f"""[Unit]
Description=HiveMIND personal agent (always on)
After=network-online.target

[Service]
Type=simple
WorkingDirectory={config.ROOT}
ExecStart={_python()} -m team serve
Restart=on-failure
RestartSec=30
Nice=10
IOSchedulingClass=idle
CPUQuota={cpus * 50}%
MemoryHigh=9G
MemoryMax=10G

[Install]
WantedBy=default.target
"""


def launchd_plist():
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>{LABEL}</string>
  <key>ProgramArguments</key><array><string>{_python()}</string><string>-m</string><string>team</string><string>serve</string></array>
  <key>WorkingDirectory</key><string>{config.ROOT}</string>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><dict><key>SuccessfulExit</key><false/></dict>
  <key>ThrottleInterval</key><integer>30</integer>
  <key>Nice</key><integer>10</integer>
  <key>ProcessType</key><string>Background</string>
  <key>LowPriorityIO</key><true/>
  <key>StandardOutPath</key><string>{config.ROOT / "memory" / "serve.out.log"}</string>
  <key>StandardErrorPath</key><string>{config.ROOT / "memory" / "serve.err.log"}</string>
</dict></plist>
"""


def plan(home=None):
    """(file to write, its text, commands to run) for this system."""
    home = Path(home or Path.home())
    if sys.platform.startswith("linux"):
        unit = home / ".config" / "systemd" / "user" / f"{NAME}.service"
        return unit, systemd_unit(), [["systemctl", "--user", "daemon-reload"],
                                      ["systemctl", "--user", "enable", "--now", f"{NAME}.service"]]
    if sys.platform == "darwin":
        p = home / "Library" / "LaunchAgents" / f"{LABEL}.plist"
        return p, launchd_plist(), [["launchctl", "load", "-w", str(p)]]
    if os.name == "nt":
        cmd = f'"{_python()}" -m team serve'
        return None, "", [["schtasks", "/Create", "/F", "/SC", "ONLOGON", "/RL", "LIMITED", "/TN", "HiveMIND", "/TR",
                           f'cmd /c cd /d "{config.ROOT}" && start "" /belownormal {cmd}']]
    raise SystemExit(f"no service manager known for {sys.platform}: run `python -m team serve` yourself")


def install(dry_run=False, home=None):
    path, text, cmds = plan(home)
    if dry_run:
        print(f"would write {path}:\n{text}" if path else "nothing to write")
        for c in cmds:
            print("would run:", " ".join(c))
        return 0
    if path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        print(f"wrote {path}")
    for c in cmds:
        print("running:", " ".join(c))
        r = subprocess.run(c)
        if r.returncode:
            print(f"failed ({r.returncode}): {' '.join(c)}")
            return r.returncode
    if sys.platform.startswith("linux"):
        print("HiveMIND starts when you log in. To start it at boot even before you log in, run once:\n"
              f"  loginctl enable-linger {os.environ.get('USER', '$USER')}")
    print("It is on: http://127.0.0.1:8766  (hive \"your prompt\" now goes to it)")
    return 0


def uninstall(home=None):
    path, _, _ = plan(home)
    if sys.platform.startswith("linux"):
        subprocess.run(["systemctl", "--user", "disable", "--now", f"{NAME}.service"])
    elif sys.platform == "darwin" and path:
        subprocess.run(["launchctl", "unload", "-w", str(path)])
    elif os.name == "nt":
        subprocess.run(["schtasks", "/Delete", "/F", "/TN", "HiveMIND"])
    if path and path.exists():
        path.unlink()  # only the entry install wrote
        print(f"removed {path}")
    return 0

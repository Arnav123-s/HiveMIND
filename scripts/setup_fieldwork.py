"""Install the optional pinned CPython WASI guest and its Python runtime."""

import argparse
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import venv
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from team import config

URL = "https://github.com/brettcannon/cpython-wasi-build/releases/download/v3.13.9/python-3.13.9-wasi_sdk-24.zip"
ARCHIVE_SHA256 = "f974d681668b8a51bf548474c9999630fe83a316155a4e937eaff57ea3ea4f39"
TREE_SHA256 = "848ad8313d100b629bf88bc86fc6ad0bdb2640c9b0edea7cb54a1904a6520161"


def installed(sdk):
    """Recognize the full pinned distribution, including an existing manual installation."""
    if not (sdk / "python.wasm").is_file():
        return False
    tree = hashlib.sha256()
    for path in sorted(p for p in sdk.rglob("*") if p.is_file()):
        tree.update(path.relative_to(sdk).as_posix().encode() + b"\0" + hashlib.sha256(path.read_bytes()).digest())
    return tree.hexdigest() == TREE_SHA256


def install_guest(sdk, archive=None):
    if sdk.exists() and (not sdk.is_dir() or any(sdk.iterdir())):
        if installed(sdk):
            return
        raise ValueError(f"{sdk} already contains a different or incomplete installation; choose a fresh HIVE_FIELDWORK_SDK")
    sdk.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=sdk.parent) as tmp:
        tmp = Path(tmp)
        if archive is None:
            archive = tmp / "sdk.zip"
            with urllib.request.urlopen(URL, timeout=90) as response, archive.open("wb") as output:
                shutil.copyfileobj(response, output)
        if hashlib.sha256(archive.read_bytes()).hexdigest() != ARCHIVE_SHA256:
            raise ValueError("the CPython WASI archive has a different SHA-256 from the pinned release")
        with zipfile.ZipFile(archive) as zipped:
            zipped.extractall(tmp / "sdk")
        try:
            (tmp / "sdk").rename(sdk)
        except OSError:
            if not installed(sdk):  # Another installer may have published the same complete guest.
                raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, help="use a previously downloaded copy of the pinned WASI zip")
    args = parser.parse_args(argv)
    sdk = config.fieldwork_sdk_path()
    try:
        install_guest(sdk, args.archive)
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        parser.exit(1, f"setup_fieldwork: {exc}\n")
    env = config.ROOT / ".venv"
    local_python = env / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    override = os.environ.get("HIVE_PYTHON")
    if override:
        python = Path(override).expanduser()
    elif local_python.is_file():
        python = local_python
    elif sys.prefix != sys.base_prefix:
        python = Path(sys.executable)
    else:
        venv.EnvBuilder(with_pip=True).create(env)
        python = local_python
    probe = "import wasmtime; from importlib.metadata import version; raise SystemExit(version('wasmtime') != '36.0.0')"
    if subprocess.run([str(python), "-c", probe], stderr=subprocess.DEVNULL).returncode:
        subprocess.run([str(python), "-m", "pip", "install", "wasmtime==36.0.0"], check=True)
    print(f"Fieldwork is ready in {python} with the guest at {sdk}.")


if __name__ == "__main__":
    main()

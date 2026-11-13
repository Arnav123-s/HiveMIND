"""Generator for the sec-code subject (niche-expansion pick #1).

Muse's side, Hive growth department. Patterned on
factory/dream_gen_niches.py: three DISJOINT template partitions
(train / screen=held-A / confirm=held-B) crossed with bands 1-3.
Partitions use different function/argument names, different literal
pools (domains, paths, file names) and different framing lines, so a
held surface is never a renamed train surface.

Labels are PROVED at generation: an item is kept only if it parses
(ast.parse) and the coding/swarm/field_sec.py finder ensemble fires
on exactly its labelled class and no other (clean = none fire).
Drops are counted with reasons, never relabelled by hand.

Band design (plan 5.5, binding):
  band 1: the signal shape alone;
  band 2: the shape inside ordinary surrounding code;
  band 3: the shape beside a near-miss distractor — and for `clean`,
          band 3 IS the near-miss set (verify=True beside a fetch,
          random used for a shuffle, yaml.safe_load, literal-only
          paths/URLs, secrets-module tokens).
"""
from __future__ import annotations

import ast
import random
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

LAB_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(LAB_ROOT / "coding"))

from swarm import field_sec as FS  # noqa: E402

CLASSES = ["clean", "path-traversal", "insecure-random",
           "unsafe-yaml-load", "tls-verify-off", "ssrf"]

_FINDERS = {
    "path-traversal": FS.path_traversal_finder,
    "insecure-random": FS.insecure_random_finder,
    "unsafe-yaml-load": FS.unsafe_yaml_load_finder,
    "tls-verify-off": FS.tls_verify_off_finder,
    "ssrf": FS.ssrf_finder,
}

# ------------------------------------------------------------ pools
# One pool set per partition: names and literals never cross over.
_POOLS = {
    "train": {
        "fns": ["load_profile", "fetch_report", "open_export",
                "read_invoice", "grab_page", "make_token"],
        "args": ["user_file", "target_url", "raw_blob", "form_data"],
        "domains": ["api.northwind.example", "cdn.northwind.example"],
        "paths": ["reports/daily.txt", "data/seed.csv", "notes/readme.txt"],
        "files": ["export_2024.csv", "profile_dump.json", "ledger.txt"],
        "banner": "northwind helper",
    },
    "screen": {
        "fns": ["retrieve_ledger", "download_statement", "pull_snapshot",
                "request_otp", "import_settings", "proxy_lookup"],
        "args": ["entry_key", "remote_ref", "payload_text", "query_blob"],
        "domains": ["portal.blueridge.example", "files.blueridge.example"],
        "paths": ["statements/march.txt", "archive/index.csv",
                  "shared/handbook.txt"],
        "files": ["statement_q1.pdf", "snapshot_blob.bin", "catalog.json"],
        "banner": "blueridge utility",
    },
    "confirm": {
        "fns": ["extract_archive_entry", "collect_telemetry",
                "issue_reset_code", "parse_manifest", "call_upstream",
                "serve_download"],
        "args": ["record_ref", "inbound_link", "config_stream",
                 "posted_body"],
        "domains": ["gateway.copperfield.example",
                    "relay.copperfield.example"],
        "paths": ["telemetry/batch.txt", "manifests/main.csv",
                  "guides/intro.txt"],
        "files": ["archive_member.dat", "telemetry_pack.json",
                  "manifest_copy.txt"],
        "banner": "copperfield routine",
    },
}


def _url(pool, rng, path_word):
    return f"https://{rng.choice(pool['domains'])}/{path_word}"


# ------------------------------------------------------------ bodies
# Each builder returns (imports, body_lines). Body lines are plain
# statements, indented by the wrapper.
def _body(pool, cls, band, rng, variant):
    fn_arg = pool["args"][variant % len(pool["args"])]
    lit_url = _url(pool, rng, rng.choice(["status", "health", "ping"]))
    lit_path = rng.choice(pool["paths"])
    fname = rng.choice(pool["files"])

    if cls == "path-traversal":
        if band == 1:
            opts = [
                [f"handle = open({fn_arg})", "return handle.read()"],
                [f"return open('../shared/{fname}').read()"],
                [f"return send_file({fn_arg})"],
            ]
        elif band == 2:
            opts = [
                [f"chosen = {fn_arg}", "with open(chosen) as fh:",
                 "    return fh.read()"],
                [f"import os", f"joined = os.path.join(base_dir, {fn_arg})",
                 "return open(joined).read()"],
                [f"wanted = '../private/{fname}'",
                 "stream = open(wanted)", "return stream.read()"],
            ]
        else:  # band 3: a literal (clean) open beside the real shape
            opts = [
                [f"notes = open('{lit_path}').read()",
                 f"blob = open({fn_arg}).read()", "return blob"],
                [f"guide = open('{lit_path}').read()",
                 f"return open('../vault/{fname}').read()"],
                [f"preview = open('{lit_path}').read()",
                 f"return send_file({fn_arg})"],
            ]
        return [], opts[variant % len(opts)]

    if cls == "insecure-random":
        if band == 1:
            opts = [
                ["token = '%06d' % random.randint(0, 999999)",
                 "return token"],
                ["otp_value = random.randrange(100000, 999999)",
                 "return str(otp_value)"],
                ["session_key = random.getrandbits(48)",
                 "return session_key"],
            ]
        elif band == 2:
            opts = [
                ["digits = []", "for _ in range(6):",
                 "    digits.append(str(random.randint(0, 9)))",
                 "reset_code = ''.join(digits)", "return reset_code"],
                ["api_token = ''.join(random.choice('abcdef0123456789') "
                 "for _ in range(12))", "return api_token"],
                ["password_hint = random.choice(['sun', 'moon', 'star'])",
                 "nonce = random.randint(10, 99)",
                 "return password_hint + str(nonce)"],
            ]
        else:  # band 3: a non-secret shuffle beside the secret use
            opts = [
                ["random.shuffle(play_order)",
                 "token = random.randint(1000, 9999)", "return token"],
                ["random.shuffle(deck_order)",
                 "otp_pin = '%04d' % random.randint(0, 9999)",
                 "return otp_pin"],
                ["random.shuffle(queue_slots)",
                 "api_key_part = random.randrange(10 ** 6)",
                 "return api_key_part"],
            ]
        return ["import random"], opts[variant % len(opts)]

    if cls == "unsafe-yaml-load":
        if band == 1:
            opts = [
                [f"data = yaml.load({fn_arg})", "return data"],
                [f"cfg = yaml.unsafe_load({fn_arg})", "return cfg"],
                [f"obj = yaml.load({fn_arg}, Loader=yaml.Loader)",
                 "return obj"],
            ]
        elif band == 2:
            opts = [
                [f"raw = open('{lit_path}').read()",
                 f"data = yaml.load({fn_arg})", "return data"],
                [f"parsed = yaml.unsafe_load({fn_arg})",
                 "count = len(parsed)", "return count"],
                [f"data = yaml.load({fn_arg}, Loader=yaml.Loader)",
                 "return sorted(data)"],
            ]
        else:  # band 3: a safe_load beside the unsafe one
            opts = [
                [f"preview = yaml.safe_load({fn_arg})",
                 f"data = yaml.load({fn_arg})", "return data"],
                [f"safe_copy = yaml.load({fn_arg}, Loader=yaml.SafeLoader)",
                 f"real = yaml.unsafe_load({fn_arg})", "return real"],
                [f"check = yaml.safe_load({fn_arg})",
                 f"full = yaml.load({fn_arg}, Loader=yaml.Loader)",
                 "return full"],
            ]
        return ["import yaml"], opts[variant % len(opts)]

    if cls == "tls-verify-off":
        if band == 1:
            opts = [
                [f"resp = requests.get('{lit_url}', verify=False)",
                 "return resp.status_code"],
                [f"resp = requests.post('{lit_url}', verify=False)",
                 "return resp.text"],
                [f"resp = httpx.get('{lit_url}', verify=False)",
                 "return resp.status_code"],
            ]
        elif band == 2:
            opts = [
                ["headers = {'Accept': 'application/json'}",
                 f"resp = requests.get('{lit_url}', headers=headers, "
                 "verify=False)", "return resp.json()"],
                [f"resp = requests.request('GET', '{lit_url}', "
                 "timeout=5, verify=False)", "return resp.status_code"],
                [f"resp = client.get('{lit_url}', verify=False)",
                 "return resp.content"],
            ]
        else:  # band 3: a verify=True call beside the verify=False one
            opts = [
                [f"good = requests.get('{lit_url}', verify=True)",
                 f"bad = requests.get('{_url(pool, rng, 'data')}', "
                 "verify=False)", "return bad.status_code"],
                [f"probe = httpx.get('{lit_url}', verify=True)",
                 f"resp = requests.post('{lit_url}', verify=False)",
                 "return resp.text"],
                [f"ok_call = requests.get('{lit_url}', verify=True)",
                 f"resp = client.get('{lit_url}', verify=False)",
                 "return resp.status_code"],
            ]
        return ["import requests"], opts[variant % len(opts)]

    if cls == "ssrf":
        if band == 1:
            opts = [
                [f"resp = requests.get({fn_arg})", "return resp.text"],
                [f"resp = requests.post({fn_arg}, json={{}})",
                 "return resp.status_code"],
                [f"data = urllib.request.urlopen({fn_arg}).read()",
                 "return data"],
            ]
        elif band == 2:
            opts = [
                [f"target = config['endpoint']",
                 "return requests.get(target).text"],
                [f"dest = {fn_arg}.strip()",
                 f"resp = requests.get(dest)", "return resp.content"],
                [f"resp = session_get({fn_arg})", "return resp",
                 ],  # placeholder replaced below if chosen
            ]
            opts[2] = [f"import urllib.request",
                       f"raw = urllib.request.urlopen({fn_arg}).read()",
                       "return raw.decode()"]
        else:  # band 3: a literal (clean) fetch beside the steered one
            opts = [
                [f"health = requests.get('{lit_url}').status_code",
                 f"resp = requests.get({fn_arg})", "return resp.text"],
                [f"ping = requests.post('{lit_url}')",
                 f"resp = requests.post({fn_arg})", "return resp.text"],
                [f"home = requests.get('{lit_url}')",
                 f"data = urllib.request.urlopen({fn_arg}).read()",
                 "return data"],
            ]
        imports = ["import requests"]
        if any("urllib" in line for line in opts[variant % len(opts)]):
            imports.append("import urllib.request")
        return imports, opts[variant % len(opts)]

    # clean
    if band == 1:
        opts = [
            [f"resp = requests.get('{lit_url}')", "return resp.json()"],
            [f"return open('{lit_path}').read()"],
            [f"data = yaml.safe_load({fn_arg})", "return data"],
            ["token = secrets.token_hex(16)", "return token"],
            [f"resp = requests.get('{lit_url}', verify=True)",
             "return resp.text"],
            [f"data = yaml.load({fn_arg}, Loader=yaml.SafeLoader)",
             "return data"],
        ]
        imports = []
        chosen = opts[variant % len(opts)]
        if any("requests" in l for l in chosen):
            imports.append("import requests")
        if any("yaml" in l for l in chosen):
            imports.append("import yaml")
        if any("secrets" in l for l in chosen):
            imports.append("import secrets")
        return imports, chosen
    if band == 2:
        opts = [
            ["entries = [3, 1, 2]", "random.shuffle(entries)",
             "return entries"],
            [f"text = open('{lit_path}').read()", "lines = text.splitlines()",
             "return len(lines)"],
            [f"cfg = yaml.safe_load({fn_arg})", "name = cfg.get('name')",
             "return name"],
            [f"resp = requests.get('{lit_url}', timeout=5)",
             "total = len(resp.content)", "return total"],
        ]
        imports = []
        chosen = opts[variant % len(opts)]
        if any("random" in l for l in chosen):
            imports.append("import random")
        if any("yaml" in l for l in chosen):
            imports.append("import yaml")
        if any("requests" in l for l in chosen):
            imports.append("import requests")
        return imports, chosen
    # band 3 clean: the near-miss set — every line LOOKS like a
    # weakness shape and is not one.
    opts = [
        [f"resp = requests.get('{lit_url}', verify=True)",
         f"cfg = yaml.safe_load({fn_arg})", "return cfg"],
        ["random.shuffle(play_order)",
         f"text = open('{lit_path}').read()", "return text"],
        ["token = secrets.token_urlsafe(24)",
         f"resp = requests.get('{lit_url}')", "return token"],
        [f"data = yaml.load({fn_arg}, Loader=yaml.SafeLoader)",
         "random.shuffle(deck_order)", "return data"],
    ]
    imports = []
    chosen = opts[variant % len(opts)]
    if any("random" in l for l in chosen):
        imports.append("import random")
    if any("yaml" in l for l in chosen):
        imports.append("import yaml")
    if any("requests" in l for l in chosen):
        imports.append("import requests")
    if any("secrets" in l for l in chosen):
        imports.append("import secrets")
    return imports, chosen


def _wrap(pool, partition, fn_name, arg, imports, body):
    lines = list(imports)
    if partition == "screen":
        lines.append(f"# {pool['banner']}: reviewed helper")
    if partition == "confirm":
        lines.append(f"# {pool['banner']} (intake copy)")
    lines.append(f"def {fn_name}({arg}):")
    if partition == "screen":
        lines.append(f"    marker = '{pool['banner']}'")
    if partition == "confirm":
        lines.append("    outcome = None")
    for ln in body:
        lines.append("    " + ln if ln.strip() else ln)
    return "\n".join(lines)


# ------------------------------------------------------------ oracle
def oracle_fired(text: str) -> Optional[List[str]]:
    """Classes the finder ensemble fires on, or None if unparseable."""
    try:
        ast.parse(text)
    except SyntaxError:
        return None
    fired = []
    for cls, finder in _FINDERS.items():
        res = finder({"code": text})
        if not res.get("ok"):
            fired.append(cls)
    return fired


def verify_item(text: str, label: str) -> Optional[str]:
    """None to keep, else the drop reason (dream_gen_niches style)."""
    fired = oracle_fired(text)
    if fired is None:
        return "ast_parse_failed"
    want = [] if label == "clean" else [label]
    if fired != want:
        return f"oracle_fired_{'+'.join(fired) or 'none'}_want_{label}"
    return None


# ------------------------------------------------------------ pools
def _pool(partition: str, band_counts: Dict[int, int], seed: int,
          group_prefix: str):
    pool = _POOLS[partition]
    items: List[Dict[str, Any]] = []
    stats: Dict[str, Any] = {"families": 0, "drops": {}}
    rng = random.Random(seed)
    for band in (1, 2, 3):
        count = band_counts.get(band, 0)
        for cls in CLASSES:
            for i in range(count):
                variant = i + (band - 1) * 7 + CLASSES.index(cls)
                imports, body = _body(pool, cls, band, rng, variant)
                fn_name = pool["fns"][(i + band) % len(pool["fns"])]
                arg = pool["args"][variant % len(pool["args"])]
                text = _wrap(pool, partition, fn_name, arg, imports, body)
                stats["families"] += 1
                gid = f"{group_prefix}:{partition}-b{band}-{cls}-{i}"
                reason = verify_item(text, cls)
                if reason is not None:
                    key = reason.split("_want_")[0]
                    stats["drops"][key] = stats["drops"].get(key, 0) + 1
                    continue
                items.append({"text": text, "label": cls, "group": gid,
                              "band": band, "family": cls})
    stats["items"] = len(items)
    return items, stats


def gen_pool(band_counts, seed, group_prefix="train"):
    return _pool("train", band_counts, seed, group_prefix)


def gen_screen_pool(band_counts, seed, group_prefix="screen"):
    return _pool("screen", band_counts, seed, group_prefix)


def gen_confirm_pool(band_counts, seed, group_prefix="confirm"):
    return _pool("confirm", band_counts, seed, group_prefix)


DEFAULT_TRAIN_BANDS = {1: 14, 2: 14, 3: 12}
DEFAULT_HELD_BANDS = {1: 6, 2: 6, 3: 6}


def gen_train(seed: int = 101):
    return gen_pool(DEFAULT_TRAIN_BANDS, seed, "train")


def gen_held_a(seed: int = 102):
    return gen_screen_pool(DEFAULT_HELD_BANDS, seed, "screen")


def gen_held_b(seed: int = 103):
    return gen_confirm_pool(DEFAULT_HELD_BANDS, seed, "confirm")

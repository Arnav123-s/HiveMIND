"""The hive recruits: it finds small open models it does not have yet, tries each one on the exams of its school
roles, and enrols what measures up. Nobody picks the models for it.

    python -m team recruit                 find one new model, download it, try it out on every role with an exam
    python -m team recruit --repo <gguf repo on Hugging Face>   try this one (the same checks apply)
    python -m team recruit --tryout <name> [role]               try a recruit it already has on a role again

Why: copies of one model make the same mistakes (the planner's second specialist got the same 9 exam lessons right
as the first), and a weight edit sharpens what a model can nearly do but adds little where it cannot. Other families
miss other things, and one of them may be the better student for a job.

What it will take (suitable): a chat model in GGUF, at most MAX_PARAMS parameters, ungated (nothing here logs in or
uses a token), under a licence in ALLOWED (its own and its base model's), a file of at most MAX_FILE bytes, from the
model's own makers or a known converter (TRUSTED), and not a variant made to drop the model's safety behaviour.
It never deletes anything, and it stops while less than DISK_FLOOR would stay free.

A tryout is the role's own exam (team/school.py: lessons nobody trained on, the teacher's answer as the key):
- the recruit alone, untouched;
- at least as good as the role's untouched student: it is enrolled as one more voice of that role, and the role's exam
  decides by measurement whether answering together beats the best one alone;
- better than the untouched student by the school's margin: it is the better student. An edit of ITS weights is
  trained on the lessons the teacher already gave (no new teacher time), and that specialist takes the exam too.
Everything is recorded in cells/recruits.json and in the role's school record; `python -m team org` shows it.
"""
import json
import re
import shutil
import sys
import time

from . import config, school

RECORD = config.ROOT / "cells" / "recruits.json"
ALLOWED = {"apache-2.0", "mit", "bsd-3-clause", "bsd-2-clause"}
MAX_PARAMS, MAX_FILE, DISK_FLOOR = 2.0e9, 2.3e9, 4e9
TRUSTED = {"bartowski", "unsloth", "lmstudio-community", "QuantFactory", "mradermacher", "TheBloke", "ggml-org"}
SEARCHES = ["1.5B", "1.7B", "1.3B", "1.2B", "1B", "0.5B", "360M", "coder 1", "instruct 1", "mini", "small", "tiny"]
_NOT_TEXT = re.compile(r"vl\b|vision|embed|rerank|tts|audio|music|ocr|guard|whisper|speech|image|video", re.I)
_UNSAFE = re.compile(r"abliterat|uncensor|heretic|jailbreak|unfilter|nsfw", re.I)
_QUANT = ["Q8_0", "Q6_K", "Q5_K_M", "Q4_K_M"]  # the first that fits: more bits where the file is small anyway


def record():
    try:
        return json.loads(RECORD.read_text())
    except (OSError, ValueError):
        return {}


def slug(repo):
    return re.sub(r"[^a-z0-9]", "", repo.split("/")[-1].lower().replace("-gguf", ""))[:24]


def pick_file(files, limit=MAX_FILE):
    """The model file to use: the most exact one that fits the size limit. files: [(name, bytes)]."""
    for q in _QUANT:
        for name, size in files:
            if re.search(rf"[-.]{q}\.gguf$", name, re.I) and size and size <= limit:
                return name, size
    return None


def suitable(c):
    """(True, "") if the hive may take this model, else (False, why). c: what Hugging Face says about the GGUF repo
    and its base model (facts)."""
    if _NOT_TEXT.search(c["id"]) or not c.get("template"):
        return False, "not a chat model for text"
    if _UNSAFE.search(c["id"]) or _UNSAFE.search(c.get("base") or ""):
        return False, "a variant made to drop the model's safety behaviour"
    if c.get("gated") or c.get("base_gated"):
        return False, "gated: it would need a login"
    if not c.get("base"):
        return False, "names no base model (no tokenizer to build its prompt with)"
    if c.get("license") not in ALLOWED or c.get("base_license") not in ALLOWED:
        return False, f"licence {c.get('license')} / {c.get('base_license')} is not one of {sorted(ALLOWED)}"
    if not c.get("params") or c["params"] > MAX_PARAMS:
        return False, f"{(c.get('params') or 0) / 1e9:.2f}B parameters: over {MAX_PARAMS / 1e9:.1f}B or unknown"
    if c["author"] not in TRUSTED and c["author"] != c["base"].split("/")[0]:
        return False, f"converted by {c['author']}, who is neither its maker nor a known converter"
    if not c.get("file"):
        return False, "no model file that fits"
    return True, ""


def facts(repo):
    """What Hugging Face says about a GGUF repo and its base model. No login, no token."""
    from huggingface_hub import HfApi
    api = HfApi(token=False)
    i = api.model_info(repo, files_metadata=True)
    card = i.card_data.to_dict() if i.card_data else {}
    base = card.get("base_model")
    base = base[0] if isinstance(base, list) and base else base
    lic = next((t.split(":", 1)[1] for t in i.tags or [] if t.startswith("license:")), None)
    gg = getattr(i, "gguf", None) or {}
    picked = pick_file([(s.rfilename, s.size) for s in i.siblings or []])
    c = {"id": repo, "author": i.author or repo.split("/")[0], "gated": bool(i.gated), "license": lic,
         "params": gg.get("total"), "template": bool(gg.get("chat_template")), "base": base if isinstance(base, str) else None,
         "file": picked[0] if picked else None, "size": picked[1] if picked else None, "downloads": i.downloads}
    if c["base"]:
        try:
            b = api.model_info(c["base"])
            c["base_gated"] = bool(b.gated)
            c["base_license"] = next((t.split(":", 1)[1] for t in b.tags or [] if t.startswith("license:")), None)
            if b.safetensors and b.safetensors.total:
                c["params"] = b.safetensors.total
        except Exception as e:  # noqa: BLE001 - a base that cannot be read is a base that cannot be used
            c["base_gated"], c["base_license"] = True, None
            c["base_error"] = f"{type(e).__name__}"
    return c


def families():
    """The base models the hive already has or has already looked at: a recruit must be another one."""
    have = {v[2].lower() for v in config.GGUF_MODELS.values()}
    return have | {v.get("base", "").lower() for v in record().values()}


def find(log=print, per=12):
    """The next suitable model the hive has not looked at: small models by downloads, one search word after another.
    Every model looked at is recorded with the reason, so it is never looked at twice."""
    from huggingface_hub import HfApi
    api, rec = HfApi(token=False), record()
    looked = {v["repo"] for v in rec.values()} | set(rec.get("_passed_over", {}))
    passed = rec.setdefault("_passed_over", {})
    for term in SEARCHES:
        for m in api.list_models(filter="gguf", search=term, sort="downloads", limit=per):
            if m.id in looked or _NOT_TEXT.search(m.id) or _UNSAFE.search(m.id):
                continue
            looked.add(m.id)
            try:
                c = facts(m.id)
            except Exception as e:  # noqa: BLE001
                passed[m.id] = f"could not be read: {type(e).__name__}"
                continue
            ok, why = suitable(c)
            if ok and c["base"].lower() in families():
                ok, why = False, "the hive already has this model"
            if not ok:
                passed[m.id] = why
                continue
            RECORD.write_text(json.dumps(rec, indent=1, ensure_ascii=False))
            return c
    RECORD.write_text(json.dumps(rec, indent=1, ensure_ascii=False))
    log("[recruit] no new suitable model found in this round of searches", flush=True)
    return None


def enlist(c, log=print):
    """Download the model file and its tokenizer, and put the recruit on record. Returns its name, or None when the
    disk would get too full (nothing is ever deleted to make room: that is his decision)."""
    from huggingface_hub import hf_hub_download, snapshot_download
    free = shutil.disk_usage(config.ROOT).free
    if free - c["size"] < DISK_FLOOR:
        log(f"[recruit] {c['id']}: {c['size'] / 1e9:.1f} GB would leave under {DISK_FLOOR / 1e9:.0f} GB free "
            f"({free / 1e9:.1f} GB now): not downloaded", flush=True)
        return None
    hf_hub_download(c["id"], c["file"], token=False)
    snapshot_download(c["base"], allow_patterns=["tokenizer*", "*.json", "vocab*", "merges*", "*.model"],
                      ignore_patterns=["*.safetensors", "*.bin"], token=False)
    rec, name = record(), slug(c["base"])
    rec[name] = {"repo": c["id"], "file": c["file"], "base": c["base"], "params": c["params"], "license": c["license"],
                 "size_gb": round(c["size"] / 1e9, 2), "found": time.strftime("%Y-%m-%d"), "tryouts": {}}
    RECORD.write_text(json.dumps(rec, indent=1, ensure_ascii=False))
    config.GGUF_MODELS[name] = (c["id"], c["file"], c["base"])
    log(f"[recruit] {name}: {c['base']} ({c['params'] / 1e9:.2f}B, {c['license']}), {c['size'] / 1e9:.1f} GB", flush=True)
    return name


def tryout(name, role, log=print, train=True):
    """The recruit takes the role's exam untouched. What follows from the score is in the module's first lines."""
    from . import llm
    te = [x for x in school.lessons(role) if x["exam"]]
    srec = school.record().get(role, {})
    if len(te) < school.MIN_TEST or "untouched_agrees" not in srec:
        return None  # the role has held no exam yet: nothing to measure a recruit against
    got = school.answers(role, [name], te, log)[name]
    alone = round(sum(got[x["task"]] == x["key"] for x in te) / len(te), 3)
    holder = srec["general"][0]
    theirs = school.answers(role, [holder], te, log)[holder]
    covers = sum(got[x["task"]] == x["key"] and theirs[x["task"]] != x["key"] for x in te)
    out = {"exam_lessons": len(te), "alone": alone, "untouched_student": srec["untouched_agrees"],
           "role_best": srec["taught_agrees"], "right_where_the_holder_is_wrong": covers, "when": time.strftime("%Y-%m-%d %H:%M")}
    voices = list(srec.get("recruits") or [])
    if alone >= srec["untouched_agrees"] and name not in voices:
        voices.append(name)
        out["enrolled"] = "a voice of the role"
    if train and alone >= srec["untouched_agrees"] + school.MARGIN:
        edit = f"{role}_school_{name}"
        if f"{name}+{edit}" not in voices:
            free = shutil.disk_usage(config.ROOT).free
            if free < DISK_FLOOR + 4e9:  # its full weights are needed to train an edit of them
                out["student"] = f"better than the untouched student, but {free / 1e9:.1f} GB free is too little to train it"
            else:
                llm.unload_all()
                school.train(role, edit, None, log, model=record()[name]["base"])
                voices.append(f"{name}+{edit}")
                out["student"] = f"taught: {name}+{edit}"
    log(f"[recruit] {name} at {role}: {alone:.0%} alone on {len(te)} unseen lessons (untouched student "
        f"{srec['untouched_agrees']:.0%}, the role's best {srec['taught_agrees']:.0%}); right on {covers} the holder gets "
        f"wrong; {out.get('student') or out.get('enrolled') or 'not enrolled'}", flush=True)
    rec = record()
    rec[name].setdefault("tryouts", {})[role] = out
    RECORD.write_text(json.dumps(rec, indent=1, ensure_ascii=False))
    if voices != list(srec.get("recruits") or []):
        s = school.record()
        s[role]["recruits"] = voices
        school.RECORD.write_text(json.dumps(s, indent=1, ensure_ascii=False))
        school.attend(role, n=len(school.lessons(role)), log=log)  # the role's exam again, now with its new voices
    return out


def main(argv):
    opt = lambda k: argv[argv.index(k) + 1] if k in argv else None  # noqa: E731
    if opt("--tryout"):
        name = opt("--tryout")
        roles = [a for a in argv if a in school.ROLES] or list(school.ROLES)
    else:
        if opt("--repo"):
            c = facts(opt("--repo"))
            ok, why = suitable(c)
            if not ok:
                print(f"[recruit] {c['id']}: not taken: {why}")
                return 1
        else:
            c = find()
        name = c and (slug(c["base"]) if slug(c["base"]) in record() else enlist(c))
        if not name:
            return 0
        roles = list(school.ROLES)
    for role in roles:
        tryout(name, role, train="--no-train" not in argv)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

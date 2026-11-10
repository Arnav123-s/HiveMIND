"""A translator: a surgical weight edit of the 1.7B, trained on human translations, kept only if it beats the members
that translate today on sentences it never saw.

    WMT_DIR=<folder of wmt24pp parquet files> python training/translator.py prep
                                             # -> training/data/translator.jsonl and the held-out set
    python training/train_lora.py writer --data training/data/translator.jsonl --out adapters/translator --epochs 1
    bash training/to_gguf.sh translator
    python training/translator.py eval       # chrF on the held-out set: writer (1.7B + its edit), editor (4B), translator

Why: in held-out set 2 the writer (1.7B + its edit) translated 'The train leaves at nine in the morning.' as
'Der Zug fährt um 9 Uhr in der Morgens.' (a grammar error). A small specialist can sharpen a skill its model has; it
cannot create one it lacks, so the edit goes on the 1.7B (which knows German, French and Spanish), not on a 135M cell.
Data: google/wmt24pp (open; professional translations of the same 998 English segments into each language: social
posts, news, fiction, speech; Tatoeba's and FLORES's sets need a login, and OPUS-100 is mostly loose film subtitles).
The split is by document and the same for every language, so no held-out sentence, nor any sentence of its document,
is trained on in any language. Each pair is put in exactly the prompt the hive sends for work on his own text
(team/specialists/writer.py messages()). Score: chrF (character n-gram F-score, beta 2, n 1-6) against the
professional translation, and seconds per sentence.
Writes training/reports/translator.json.
"""
import json
import os
import random
import re
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
RAW = Path(os.environ.get("WMT_DIR", ROOT / "training" / "data" / "wmt24pp"))  # the downloaded parquet files
DATA = ROOT / "training" / "data" / "translator.jsonl"
HELD = ROOT / "training" / "evals" / "translator_heldout.jsonl"
OUT = ROOT / "training" / "reports" / "translator.json"
LANGS = {"de": ("en-de_DE", "German"), "fr": ("en-fr_FR", "French"), "es": ("en-es_MX", "Spanish")}
ORDERS = ["Translate into {L}: '{t}'", "Translate this into {L}: {t}", "How do I say '{t}' in {L}?",
          "Put this sentence into {L}, please: '{t}'", "Translate to {L} and give me only the translation: '{t}'"]
N_TRAIN, N_HELD = 300, 40


def clean(en, xx):
    """A usable segment: 4 to 25 words, no user handles or URLs, similar lengths."""
    if not (4 <= len(en.split()) <= 25) or re.search(r"https?://|www\.|@\w|<|>|\{|\}", en + xx):
        return False
    return 0.6 <= len(xx) / max(1, len(en)) <= 1.8


def held_doc(doc):
    """30% of documents are held out, the same documents for every language."""
    import hashlib
    return int(hashlib.sha1(str(doc).encode()).hexdigest(), 16) % 10 >= 7


def pairs(code, held):
    import pandas as pd
    cfg, _ = LANGS[code]
    d = pd.read_parquet(RAW / f"{cfg}.parquet")
    d = d[(~d["is_bad_source"]) & (d["domain"] != "canary")]
    out = [(r["source"].strip(), r["target"].strip()) for _, r in d.iterrows() if held_doc(r["document_id"]) == held]
    return list(dict.fromkeys(p for p in out if clean(*p)))


def messages(order):
    from team.specialists.writer import OWN_TEXT, messages as writer_messages
    return writer_messages(order, f"Write the finished answer for Arnav: {order}", f"{OWN_TEXT}\n{order}", [])


def prep():
    rng = random.Random(7)
    rows, held = [], []
    for code, (_, name) in LANGS.items():
        train = pairs(code, held=False)
        test = [p for p in pairs(code, held=True) if p[0] not in {t[0] for t in train}]
        for en, xx in rng.sample(train, min(N_TRAIN, len(train))):
            order = rng.choice(ORDERS).format(L=name, t=en)
            rows.append({"messages": messages(order), "output": xx})  # train_lora.py: the prompt, then the reply
        for en, xx in rng.sample(test, min(N_HELD, len(test))):
            held.append({"lang": code, "order": f"Translate into {name}: '{en}'", "en": en, "ref": xx})
    rng.shuffle(rows)
    DATA.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n")
    HELD.parent.mkdir(parents=True, exist_ok=True)
    HELD.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in held) + "\n")
    print(f"{len(rows)} training pairs -> {DATA}; {len(held)} held-out -> {HELD}")


def chrf(hyp, ref, n=6, beta=2.0):
    """Character n-gram F-score (as in sacreBLEU's chrF): precision and recall averaged over n = 1..6, spaces out."""
    precs, recs = [], []
    h0, r0 = re.sub(r"\s+", "", hyp), re.sub(r"\s+", "", ref)
    for k in range(1, n + 1):
        h = Counter(h0[i:i + k] for i in range(len(h0) - k + 1))
        r = Counter(r0[i:i + k] for i in range(len(r0) - k + 1))
        if not h or not r:
            continue
        m = sum((h & r).values())
        precs.append(m / sum(h.values()))
        recs.append(m / sum(r.values()))
    if not precs:
        return 0.0
    p, r = sum(precs) / len(precs), sum(recs) / len(recs)
    return 0.0 if p + r == 0 else 100 * (1 + beta ** 2) * p * r / (beta ** 2 * p + r)


def answer(text):
    """The translation itself: the first non-empty line, without a list number, quotes or a label."""
    line = next((ln.strip() for ln in (text or "").splitlines() if ln.strip()), "")
    line = re.sub(r"^(\d+[.)]\s*|[-*]\s*|\*\*?[^*]+\*\*?:\s*|[A-Za-z ]{2,20}:\s+)", "", line)
    return line.strip(" \"'“”«»*")


def evaluate(roles=("writer", "editor", "translator")):
    from team import config, llm
    held = [json.loads(ln) for ln in HELD.read_text().splitlines() if ln.strip()]
    if "translator" in roles and not (ROOT / "adapters_gguf" / "translator.gguf").exists():
        roles = tuple(r for r in roles if r != "translator")
    config.GGUF_ROSTER.setdefault("translator", "fast+translator")
    res = {}
    for role in roles:
        rows = []
        for h in held:
            t = time.time()
            out = llm.chat(role, messages(h["order"]), max_new_tokens=120)
            hyp = answer(out)
            rows.append({"lang": h["lang"], "en": h["en"], "ref": h["ref"], "hyp": hyp, "seconds": round(time.time() - t, 2),
                         "chrf": round(chrf(hyp, h["ref"]), 1)})
        by = {c: round(sum(r["chrf"] for r in rows if r["lang"] == c) / max(1, sum(r["lang"] == c for r in rows)), 1)
              for c in LANGS}
        res[role] = {"model": config.GGUF_ROSTER.get(role), "chrf": round(sum(r["chrf"] for r in rows) / len(rows), 1),
                     "by_language": by, "seconds_per_sentence": round(sum(r["seconds"] for r in rows) / len(rows), 2),
                     "rows": rows}
        print(f"{role:11s} ({res[role]['model']}): chrF {res[role]['chrf']} {by}, "
              f"{res[role]['seconds_per_sentence']} s/sentence", flush=True)
        llm.unload_all()
    prev = json.loads(OUT.read_text()) if OUT.exists() else {}
    OUT.write_text(json.dumps({**prev, **res}, indent=1, ensure_ascii=False))


NEWS = ROOT / "training" / "evals" / "translator_news_de.jsonl"
CHAIN = ROOT / "training" / "reports" / "translator_chain_de.json"


def chain(threshold=0.5):
    """The smallest-specialist way to translate into German: the 1.7B writer translates, the de_grammar cell (135M)
    says ok or error, and only a sentence it calls an error is translated by the 4B. Scored like the members on 160
    sentences none of them trained on (120 from WMT news 2014, 40 from WMT24++), against the writer alone and the
    4B alone: chrF and seconds per sentence."""
    from team import llm
    from team.cells import runtime
    items = [json.loads(ln) for ln in NEWS.read_text().splitlines() if ln.strip()]
    items += [json.loads(ln) for ln in HELD.read_text().splitlines() if ln.strip() and json.loads(ln)["lang"] == "de"]
    done = json.loads(CHAIN.read_text()) if CHAIN.exists() else {}
    rows = done.get("rows", [])
    have = {r["en"] for r in rows}
    for role in ("writer", "editor"):  # all of one member's translations, then the other's (one model loaded at a time)
        for it in items:
            row = next((r for r in rows if r["en"] == it["en"]), None)
            if row is None:
                row = {"en": it["en"], "ref": it["ref"], "set": "news" if it in items[:120] else "wmt24pp"}
                rows.append(row)
            if role in row:
                continue
            t = time.time()
            row[role] = answer(llm.chat(role, messages(it["order"]), max_new_tokens=160))
            row[f"{role}_s"] = round(time.time() - t, 2)
            row[f"{role}_chrf"] = round(chrf(row[role], it["ref"]), 1)
            CHAIN.write_text(json.dumps({"rows": rows}, indent=1, ensure_ascii=False))
        llm.unload_all()
    for row in rows:  # the cell's verdict on the writer's German
        t = time.time()
        p = runtime.label_probs("de_grammar", f"SENTENCE: {row['writer']}")
        row["cell_s"] = round(time.time() - t, 3)
        row["p_error"] = round(float(p.get("error", 0.0)), 3)
    def score(flag):
        chosen = [r["editor_chrf"] if flag(r) else r["writer_chrf"] for r in rows]
        secs = [r["writer_s"] + r["cell_s"] + (r["editor_s"] if flag(r) else 0) for r in rows]
        return round(sum(chosen) / len(rows), 1), round(sum(secs) / len(rows), 2), sum(map(flag, rows))
    res = {"n": len(rows), "threshold": threshold,
           "writer": {"chrf": round(sum(r["writer_chrf"] for r in rows) / len(rows), 1),
                      "s": round(sum(r["writer_s"] for r in rows) / len(rows), 2)},
           "editor_always": {"chrf": round(sum(r["editor_chrf"] for r in rows) / len(rows), 1),
                             "s": round(sum(r["editor_s"] for r in rows) / len(rows), 2)}}
    c, s_, k = score(lambda r: r["p_error"] >= threshold)
    res["chain"] = {"chrf": c, "s": s_, "sent_to_4b": k}
    o, so, ko = score(lambda r: r["editor_chrf"] > r["writer_chrf"])  # the best any judge could do
    res["oracle_chain"] = {"chrf": o, "s": so, "sent_to_4b": ko}
    CHAIN.write_text(json.dumps({**res, "rows": rows}, indent=1, ensure_ascii=False))
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    {"prep": prep, "eval": lambda: evaluate(tuple(sys.argv[2:]) or ("writer", "editor", "translator")),
     "chain": lambda: chain(float(sys.argv[2]) if len(sys.argv) > 2 else 0.5)}[sys.argv[1]]()

# Muse's work, Muse's side

# Engine proof — seed 12004, members-alone (the LIVE sitting), 2026-11-13 ~13:35 PT

*Prompted by Fable's side's discovery today (their commit 7171805, relayed by the parent):
every GitHub sitting before their fix silently ran FALLBACK small PyTorch models — on a
fresh runner no GGUF files exist, so the hive used the 1.7B/1.5B PyTorch bases instead of
the real brain4b + coder7b (llama.cpp). Their rule: never compare across that line. This
proof establishes, from the running sitting's OWN records, what is serving on ashp.*

## Verdict

**No silent fallback is in play on ashp. The campaign is NOT halted.** What serves —
Qwen2.5-Coder-1.5B-Instruct for the members (this arm), Qwen3-1.7B for the roles (the
other arms) — is the campaign's *declared* configuration: named in Q1-RUN-PLAN.md's frozen
config and on the Q1 page before any launch, and pinned in the launcher. Fable's side's
failure mode was a *silent substitution away from* their declared config (brain4b/coder7b
GGUF); here there is no divergence between declared and served, because the declared stack
IS the PyTorch stack. The substitution mechanism exists in the code (see item 3) — on this
lane it points at the models we declared, on purpose, with the engine pinned so the GGUF
path cannot engage at all.

## The proof chain (each link checkable)

1. **RUN-METADATA.json, read from the live sitting copy on ashp mid-run:** env carries
   `AGENT_TEAM_ENGINE: "hf"`, `AGENT_TEAM_SOLO: "2"`, `AGENT_TEAM_SOLO_ALONE: "1"`,
   threads 8, `HF_HOME: D:\agents\muse\for-hive\hf`, code manifest rollup
   `fb51cf44e430216844b86eaf57517391d3e92e97a3541e0c4531465824671730`, `started_at:
   2026-11-13 11:03:00`, `restart_count: 0`.
2. **Sit log START line** (`campaign\sit-12004-members-alone.log`): `2026-11-13 11:03:00
   START seed=12004 members-alone SOLO=2 ALONE=1 ENGINE=hf HIVE_LIBRARY=0 threads=8
   manifest=fb51cf44… restarts=0` — the launched process ran under the pin.
3. **Code path at the sitting's own manifest (campaign chassis, rollup-verified):**
   `team/llm.py` `gguf_available()` returns `False` on its first line when
   `config.ENGINE == "hf"` — under the pin the GGUF path is unreachable, deterministically.
   All generation flows through `llm._load()` = `AutoModelForCausalLM.from_pretrained(
   model_id, dtype=torch.bfloat16)`. Members chat via `llm.chat("coder", …)`
   (`team/solo.py:189`); `team/config.py` maps `"coder"` → `CODER_MODEL =
   "Qwen/Qwen2.5-Coder-1.5B-Instruct"` and all roles → `BASE_MODEL = "Qwen/Qwen3-1.7B"`.
   The fallback mechanism Fable's side found is the third element of `GGUF_MODELS`
   (`brain4b → Qwen/Qwen3-1.7B`, `coder7b → Qwen/Qwen2.5-Coder-1.5B-Instruct`,
   `config.py:36-41`) — the same two models this campaign declares openly.
4. **The machine cannot serve the GGUF models in any mode:** ashp's HF hub cache holds
   exactly `Qwen--Qwen3-1.7B`, `Qwen--Qwen2.5-Coder-1.5B-Instruct` (plus the
   `SmolLM2-135M-Instruct` utility) and **no GGUF model repos**; `llama_cpp` is not
   installed on ashp (proven operationally: pilot 12003's tasks died on
   `from llama_cpp import Llama`). The 32 `.gguf` files inside the sitting copy are
   `adapters_gguf\` specialist adapters (and cells files) — reachable only through the
   llama path the pin disables; the adopted cells patch additionally forces cells off
   under hf.
5. **Behaviour in the records matches the declared stack:** the live mirror
   (`campaign-records/12004-members-alone/`, 11 of 16 task dirs landed by ~13:35 PT) shows
   real member work under the copy's own paths — member programs written and run turn by
   turn, `events.jsonl` per task, e.g. e12004_00's agreed answer "La biblioteca cierra a
   las diez los lunes." produced by member3 after member1/member2 failed their turns.

## What this does and does not change

- **Unchanged:** every campaign claim stays internal to the ashp/HF batch. The plan's
  caveat (absolute levels not comparable to GitHub sittings; ranking crosses only as a
  hypothesis with engine as blocking factor) stands — hardware, threads and runner
  provenance still differ, and Fable's side's pre-fix runs were unpinned and unrecorded.
- **Weakened further:** the seed-9007 hint (10/9/9) that motivated the members-first
  default is now known to be fallback-stack numbers. That is exactly the tier of evidence
  Fable's own method allows a *reversible default* to rest on — and exactly why this
  campaign measures the question fresh, pinned, and recorded, instead of inheriting it.
- **Standing gate added (plan v2.1):** a sitting counts only if its records affirmatively
  show the serving stack — RUN-METADATA with the pinned env, a matching sit-log START
  line, the chassis code-path proof at the sitting's manifest rollup, and the lane's HF
  cache inventory. A sitting whose records cannot show this is excluded as unprovenanced,
  like a pilot. 12004 satisfies the gate on the evidence above; the same check is
  re-derived by each trio's Row Verifier.

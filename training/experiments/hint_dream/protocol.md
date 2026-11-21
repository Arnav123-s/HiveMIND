# Paired synthetic practice on the kept G55 body

Freeze seed `spade-development-20261120`, six consecutive generated format/rule pairs, a two-core native G55 trunk, one unhinted and one hinted first program per pair, greedy sampling and at most 256 generated tokens. Run both arms even when the blind program passes. Compile the program inside CPython WASI. The host computes expected answers from the source event sequence. Each program must produce the exact typed value on both fixed suites of twelve inputs. The two suites share boundary shapes and have independent seeded data; their calls do not count as independent tasks.

Admit one unhinted supervised prompt and the verified hinted program only for a blind failure and a fully passing hinted reply. A broken inference or guest setup voids the affected trial. A zero-window run trains no synthetic rows. Report raw replies, timing, all paired outcomes and measured proportion. Six pairs would need at least two qualifying tasks to exceed 20%. None of these tasks is drawn from an official exam. Weight training and fresh task performance are separate measurements.

## Run the ordinary training path

Set `HIVE_SPADE_DREAM=1` in repository variables or in the local environment. A grow dream shard reserves one slot for the current trunk, falling back to the first configured native member if there is no trunk. The shard stops after a successful blind answer and sends a private implementation hint only on failure. Each generated pair shares one task timeout and the existing job deadline. A missing WASI runtime or missing member leaves the slot available for an ordinary dream. The workflow installs the pinned CPython WASI guest only when enabled. `HIVE_SPADE_DREAM=0` is the default.

On a local checkout with a native roster and the fieldwork guest installed, this runs one slot and gathers its checked rows into the ordinary training format.

```sh
mkdir -p runs/hint-practice
HIVE_SPADE_DREAM=1 HIVE_FIELDWORK_SDK=runs/fieldwork-assets/wasi python training/grow.py dream --tasks 1 --seed 39005651 --out runs/hint-practice/rows.jsonl
python training/grow.py gather --out runs/hint-practice/gathered.jsonl --gen practice runs/hint-practice/rows.jsonl
```

The per-shard `runs/exam/dream_<seed>/hint-regret.json` retains the blind/hinted verification counts, selected member and admission decision. Only admitted tasks go to `rows.jsonl`. The existing gather stage stamps and deduplicates these alongside the body's other checked practice. Its normal supervised training worker reads the resulting rows.

`python -m team dream` also shares the opt-in lane when local rehearsals are requested. Its synthetic rows enter `runs/grow/rows.jsonl` for the ternary body trainer. The role-specific dream command retains its own existing training and memory log.

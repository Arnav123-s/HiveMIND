# What the 8B model actually learned

A local Ternary-Bonsai-8B with the G47 coding adapter wrote programs for three new work orders. It failed all three after two attempts each. An easier fourth order, added after those failures, passed on its first attempt. Later, a repair rule learned from two independently checked, human-written corrections helped the same frozen transit program deliver all forty new answers. The model generated no additional text for that repair.

| Order | Original model drafts, public checks out of 4 | Original draft accuracy out of 40 if run directly | Stock delivered | Fixed repairs delivered | Fixed and learned repairs delivered |
| --- | --- | --- | ---: | ---: | ---: |
| Transit ticket count | 3, 3 | 33, 33 | 0/40 | 0/40 | 40/40 |
| Library overdue fees | 0, 0 | 0, 0 | 0/40 | 0/40 | 0/40 |
| Longest hot sensor streak with one missing value | 0, 0 | 0, 0 | 0/40 | 0/40 | 0/40 |
| Range of price quotes, added fourth | 4 | 40 | 40/40 | 40/40 | 40/40 |
| **Correct files delivered** | | | **40/160** | **40/160** | **80/160** |

All three arms withheld the other jobs and delivered zero wrong files. Each qualified program passed twelve separate checks before delivery. The forty private answers per order served only to grade the files after execution. Each task's public examples, qualification checks and fresh jobs had distinct inputs. An independent calculation confirmed all 224 expected outputs across the four tasks.

The transit contract says the passenger needs a new ticket exactly fifty minutes after the old one starts. The model's second draft repeated the first draft's mistake at the expiry boundary. The later selector tried one public candidate, changing `t > end` to `t >= end`. Its receipt traces the edit to corroborating donations from the cold-alert and badge-test tasks. The fixed decoded-input adapter by itself qualified neither the library nor the sensor code. The library program also capped the whole bill instead of each title, and the sensor program failed to advance past a cool reading.

**How the two stages differ.** The original stock model ran seven times on three CPU threads, with greedy decoding and a cap of 450 tokens per attempt. It generated 674 completion tokens in total. Each retry received its own draft and public feedback. The price program took 47 tokens. It demonstrates acquisition and reuse on the previous fieldwork engine. The later comparison used fixed model source for both arms and replayed no model inference. Both arms started each order with the same four human-taught, independently qualified donor programs and allowed at most two public repair candidates. Only one arm used their repair histories. The transfer comparison followed inspection of the original failures. These four tasks support a diagnostic comparison, and none of the seven generations independently produced a successful self-correction.

## Try the retained programs

From the repository root, with the fieldwork runtime installed, run either command. Each uses a fresh input. The model-free terminal returned 24 cents and 3 tickets respectively.

```sh
HIVE_BANK=training/reports/verified-learning/live/example-bank ./hive --once 'Run quote_spread with {"quotes":[173,197,184]}'
HIVE_BANK=training/reports/verified-learning/live/example-bank ./hive --once 'Run transit_tickets with {"minutes":[1200,1250,1217,1300]}'
```

`quote-spread.json` is a small work order with four public examples, three separate checks and a file-delivery job. The two JSON records in `example-bank/` came from the successful clean quote acquisition and the learned transit transfer respectively. Each carries the actual source and its verification counts.

## Reproduce the transfer comparison

Install the project's fieldwork Python environment and WebAssembly guest. From the root, supply the installed guest directory to the replay. The script reads only the four designated training rows from the separate authored study, grows their bank before starting any of these four orders, and copies that bank afresh for each arm and order. When the donor bank differs from the native generation context, it holds the model's original source fixed. The script reports model-free terminal checks for each admitted order and includes the historical native results for comparison.

```sh
.venv/bin/python training/reports/verified-learning/live/replay.py --sdk "$HIVE_FIELDWORK_SDK" --output /tmp/hive-live-transfer.json
```

[`evidence.json.gz`](evidence.json.gz) contains the full public specs, separate qualification rows, fresh outputs, seven raw model replies, extracted source, public feedback, exact model and adapter hashes, and the original decisions. The native checkout was `1414d49243987ea58c5913af251c39e104d77b68`. [`transfer.json.gz`](transfer.json.gz) records each arm's exact selected source, proposals, per-file grades, edit receipts, engine hashes and terminal output. [`replay.py`](replay.py) reruns that comparison using the included evidence and the project guest.

# Runs 3 and 4: the final product from a fresh clone of main

Same task as run 2. Both runs: fresh clone, cells built with `python training/cells_build.py`, 14 cells on, `--approve never`.

| run | plan | answer | your instructions | time |
|---|---|---|---|---|
| 3 (`run3_fresh_clone`, writer before the fix) | researcher → writer | Apache-2.0, 0.135B, verified 3/3 | 3/4: "give me a two-line summary" ❌, not acted on | 8 min |
| 4 (this folder, writer with the fix round) | researcher → browser → coder → writer (browser and coder not ordered; both gave up after 1 attempt) | Apache-2.0, 0.135B, verified 3/3 | 4/4, ticked on the first check | 18 min |

- Run 4's "Not backed by the verified results" line is an honest "not accessible" sentence. The honesty filter did not know
  that wording then; it does now (`HONEST` in `team/specialists/writer.py`, test `test_saying_what_was_not_reached_is_never_flagged`).
- Writer step of run 3 replayed with the fix round (`run3_fresh_clone/REPORT_writer_replay.md`, final wording): the critic
  reported the miss and the writer got one fix round, but the report came back unchanged, so it stays ❌.
  The same fix ask with the writer's edit off, as a fresh call, or sent to the 4B brain, gave one sentence plus a table each
  time: the models read that as the summary; the 4B critic does not.
- The browser opened `huggingface.co/models/<id>` (not a model page) in runs 2 and 4. Not fixed here.

# Three prospective tasks for the saved-file budget change

The selected CSV edit succeeded after the second turn could use some of the remaining total allowance. Freeze three different task generators and one seed per kind before sampling the model. Include the task irrespective of error, success or whether the new branch activates. No further tasks, repetitions or prompt tuning are part of this comparison.

| Generator | Saved format | User also asks for |
|---|---|---|
| `h_tab_dates` | CSV | Total from rows inside a date interval |
| `h_tab_topn` | CSV | Name with the highest value |
| `h_txt_redact` | Plain text | Number of synthetic card patterns masked |

Use the first draw of each generator with seed `f3-borrow-confirm:2b084971f13f923c0bc8351be2cd7cffd0a77032:<kind>:0`, at its usual difficulty. The seed includes the frozen implementation's hash. The unchanged official graders examine each saved file and the worker's answer. Exact generated prompts, request hashes and filenames are registered together. Each task is outside the earlier `h_edit` kind and differs from every prompt in the official fixed panel and the 2,852 checked G55 training requests. [Registration](registration.json)

Both arms use an empty recent solved library, the same checked G55 task-text index, `HIVE_ASSERT_FIRST=1`, the default short G55-trunk instructions, and `HIVE_CUTOFF_CONTINUE=1`. Keep the earlier syntax repair, optional library recall and extra HTTP controls off. Only the treatment sets `HIVE_CUTOFF_CONTINUE_BORROW=1`. Both use the earlier SHA-pinned packed server, 8B base and G55 trunk, two CPU cores, greedy seed 8103, a nominal allowance of 192 tokens per turn, three turns, and a hard maximum of 576 generated tokens. Allow the treatment to spend at most 384 on its next call only if the existing worker confirms a full-length stop after the requested files were successfully saved with explicitly requested stdout still missing. Synthetic inputs are part of each prompt. No expected data or grader feedback enters the worker conversation.

Run control then treatment for each task. Reexecute the worker from an empty private directory in both arms. Reuse the control's native reply only for the same ordinal request on the same task with an identical complete payload, including messages and limit. A matching reply still counts toward that arm's calls and token budget. Always share the exact first reply. If all three requests are unchanged, require matching file bytes, printed answer and grade. This checks non-exposure without counting a duplicate generation as new work. Journal each genuine native response before the worker consumes it so forced checkpoints between training windows preserve complete request and response identity. Any restarted incomplete arm re-executes its earlier work.

Report official grades on all three, paired gains and losses, cases actually offered a larger allowance, and unchanged controls. Report token usage in each arm including shared replies. State the number of genuinely new server calls separately. A targeted recovery on the earlier CSV and a gain in this panel use different denominators. Neither contributes a grade to the official 30-task F3 comparison.

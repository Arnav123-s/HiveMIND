# The 16 development tasks with no model above 1.7B (2026-11-09/10)

Run: `AGENT_TEAM_SPAWN=0 AGENT_TEAM_BRAIN=fast AGENT_TEAM_GGUF_CODER=fast python training/hive_bench.py <tag>`.
Every role of the 4B (coordinator, researcher, plan reviewer, critic, editor, juror) and of the 7B coder went to
Qwen3-1.7B; the cells stayed as they are. The container restarted twice during the run, so the tasks ran in three
parts and the tool's own JSON report was not written; these lines are from its log. One run each, code at 9e7b2b6.
The normal hive scores 15 of 16 on these tasks (dev set, code 0147aa4).

| task | kind | result | seconds | what went wrong |
|---|---|---|---|---|
| lookup | facts from a source | pass | 213 | |
| arxiv | list from a source | FAIL | 529 | no arXiv papers listed in the answer |
| chart | numbers + chart | FAIL | 681 | no chart made (the right model was named) |
| quotes | operate a website | pass | 372 | |
| csv | scrape to a file | FAIL | 192 | CSV has 0 of the 3 cheapest prices |
| percent | arithmetic | pass | 76 | |
| days | dates | pass | 473 | |
| units | unit conversion | pass | 34 | |
| translate | translate given text | pass | 15 | |
| summary | summarise given text | FAIL | 89 | 3 sentences where 1 was ordered |
| grammar | fix given text | pass | 17 | |
| email | draft | pass | 69 | |
| fib | write and run code | FAIL | 598 | planned as research, not code; the value is missing |
| bugfix | fix code | FAIL | 980 | planned as research, not code; the value is missing |
| explain | explain from knowledge | pass | 555 | |
| sales | reason over given data | not finished | >540 | stopped after 9 minutes without an answer |

9 pass, 6 fail, 1 unfinished.

What breaks without the bigger models, by cause:
- **Planning** (fib, bugfix): the 1.7B coordinator sent code tasks to the researcher. The coordinator's job, not the
  coder's, failed first.
- **Writing programs** (chart, csv): the 1.7B as coder did not produce a working program.
- **Reading a list out of a source** (arxiv): the same weakness the chunk-reading test showed on short listings.
- **Keeping to an order** (summary): three sentences for "one sentence".
- **Time**: several passes took 6-9 minutes; retries after small-model mistakes cost more than the bigger model saved.

What holds: single look-ups, arithmetic, dates, units, translation, grammar, drafting, one browser task.

Next, in the order the failures suggest: a routing check on the plan (the route_step cell already scores 0.99 on
"which specialist takes a step" and was not consulted for the whole plan here), then the coder's job cut into
smaller pieces, then list extraction.

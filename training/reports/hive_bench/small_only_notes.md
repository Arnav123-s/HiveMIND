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

## Re-runs after the fixes (10 Nov 2026)

Small models only, tag `small3` (fib and sales, after the same-number rule and the lower second-opinion bar):

| task | result | seconds | plan |
|---|---|---|---|
| fib | pass | 113 | coder → writer (was planned as research, 598 s) |
| sales | pass | 57 | calculator → writer (was unfinished, then failed on "117.0, not 117") |

Small models only, best measured result per task over `small_only*`, `small2`, `small3`: 13 of 16 pass. Still
failing: csv and chart (the 1.5B coder's programs do not work) and arxiv (the small reader finds too few papers).
These three were not run again after `small2`; the 13 is put together from separate runs, not one clean run.

Normal hive, all 16 tasks, tag `normal_after`, to check the shared fixes did not break it: 15 of 16, the same count
as before. The fail is arxiv: the item jury rejected one of three papers as off topic, the critic had the writer
remove it, and the answer listed two papers where three were ordered. The hive had no spare paper to put in its
place. This task has failed the same way in earlier runs; one run cannot tell whether today's changes made it
more likely.

After the rule "fewer items than ordered: ask the researcher once for others" (same day):
- Normal hive, arxiv alone (`normal_arxiv`): pass, 482 s. The rule fired (one paper dropped as off topic, two left,
  retry) and the answer listed three mixture-of-experts papers. One run.
- Small only (`small4`): arxiv fail (0 papers; on the retry the 1.7B juror dropped on-topic papers, saying the
  source line "does not contain the three newest"; it judged one item against the whole order). csv fail (0 of the
  3 cheapest prices); this run started before the coder's same-program rule.
- Small only (`small5`), with the sort-direction check and the same-program rule: csv fail, but 2 of the 3
  cheapest prices where it had 0 (the check named the wrong-way sort and the coder fixed it; it read only the
  first of two pages). chart fail: the coder fetched the model page and found no number, and its retries, even
  sampled, ended in the same error.
- Small only (`small6`), with the next-page check and "use the team's values": csv fail (0 of 3: told to fix the
  sort and read every page, the 1.5B coder wrote a program that crashed and repeated it); chart fail (the research
  step had passed with a result that said the download numbers were "not provided", so the coder had nothing to
  chart). A research result that says it found nothing now fails its step; not measured in a run yet.
- Normal hive, the three code tasks (`normal_code`) after the coder changes: csv, chart and fib all pass.

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

## 2026-11-10, later: the first clean run of all 16 with nothing above 1.7B, and what its failures showed

`small7`, one run, all 16 tasks, the taught planner (school) holding the planning job: **11 of 16**. Every plan was
the right one. The five failures and their causes:
- lookup: the answer gave the parameter count and "The licence is not specified". The small reader had the line
  `params 0.135B | license apache-2.0 | ... | downloads 220473` in front of it and returned only parameter counts.
- chart: asked for download counts, with `downloads 3597908` in the part, the small reader returned parameter
  counts, once "Qwen/Qwen3-1.7B has 0.135B parameters" (it has 2.032B). **0.135B is the example value in the
  reader's own instruction.** The 1.7B copied the example instead of reading what the task asked for.
- fib: the first program was right (printed 832040, his examples held). The verifier failed it with a reason that
  itself said the program did what was asked. The retries made it worse; the last program failed his examples
  (fib(2) returned 2) and a jury of three small models passed it; the writer's number was struck.
- arxiv: the reader's facts did not survive the checks; the composer said the papers were "not found in the facts".
- csv: 2 of the 3 cheapest prices; told to fix the sort and read every page, the 1.5B coder broke the program.

Changed after it (all in code or instruction, all tested): the small reader's instruction has no example value; a
program that contradicts an example from his task fails whatever the jury says; "0.135B, not 135M" is no objection;
a research result that answers one part and says another is "not specified" is asked once for that part; rules that
ask once see the previous rejection (they did not: the step's task never carried it).

Two checks of the bench were wrong on right answers and were corrected: arxiv did not count papers listed by title
without a citation number (normal hive, `normal_reg`: first scored fail, the three papers and dates were right);
lookup wanted the text "0.135" and failed "135M" (`small8`: first scored fail).

Re-runs on the changed code:
- Normal hive (`normal_reg2`): lookup, arxiv, fib all pass.
- Small only (`small8`, before the reader's new instruction): lookup pass (after the check correction), fib pass
  (673 s; the example rule held the coder to fib(2) = 1), arxiv fail (no fact survived the checks).

The small reader with its new instruction, on the same 26 logged reading inputs as before (`training/chunk_read.py`):
28 of the 4B's 38 checked facts found (was 19), every fact of the 4B on 14 of 21 inputs (was 7), none on 1 (was 5),
62 checked facts in all (was 52), the same time.

Small only on that code (`small9`): lookup pass. chart fail, but further: the research step now found a download
count and passed; the claim for the other model named the quantity without its number, the composer wrote "0
downloads", and the 1.5B coder scraped a page element that does not exist instead of using the team's values. arxiv
not measured: arXiv's API timed out on every search of the run.
After it: a claim that names a quantity without its number takes its quote's words; a coder that fetches values the
team already found, in a step that names no page, is told before the run to write them in.

With those two rules (`small10`; the normal hive on the same code, `normal_reg3`: chart and lookup pass):
chart pass (442 s). arxiv fail: the 1.7B planner searched arXiv for "mixture of experts newest"; no paper has all
four words, the any-word search sorted by date gave six unrelated papers of that day, and the small composer said,
rightly, that none was about mixture of experts. csv fail (2 of the 3 cheapest): the first step attempt sorted the
wrong way and read one page; the second saved the CSV, but the file was there from the first attempt, was compared by
name only, counted as "saved none", and the step was given up.
After it: a search in a source the hive sorts by date keeps only the topic (the words that say how to sort or where to
look are dropped); a file written again counts as saved.

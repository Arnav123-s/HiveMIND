# Research hive vs one researcher (frozen c9e1448)

Four research questions in no bench and no training data, each run through the whole hive twice: with the research
hive (sub-questions, relevance, gap search, cross-checks, experiments) and with one researcher step. Numbers in
research_eval.md; this is what the reports actually said.

| question | research hive | one researcher |
|---|---|---|
| battery degradation | 42 min, 8 claims checked against 3 papers: the mechanisms (SEI growth, lithium plating, electrolyte decomposition, loss of active material) right and sourced; "what slows it" answered with factors that drive it, and ticked done | 18 min, 1 claim from 1 paper; four paragraphs on battery management systems and materials from the model's memory, "based on the verified results" |
| SQLite vs DuckDB | 15 min, nothing: the relevance rule dropped every result (and sqlite.org / duckdb.org are outside this cloud machine's allowed hosts) | 6.5 min, 1 claim |
| James Webb mirror | 40 min: gold-coated beryllium, gold for infrared reflectivity, sourced; "why beryllium" stated as not confirmed | 28 min: the same two facts; "why" ticked done |
| sorting experiment | 27 min: the experiment ran (built-in 0.0013 s vs merge sort 0.0147 s); the results lost which sort they measured and were flagged; "why" not explained | 6 min: also ran it (0.0012 s vs 0.0115 s) and explained why (C implementation vs interpreter overhead) |

What this showed, and what was fixed after it (each general, in code, with a test):
- Two cells that won on synthetic test data failed on real text: answers_q said "no" to all 15 real facts (3/15
  right; training/evals/answers_q_real.jsonl) and claims_agree called four rewordings conflicts. The researcher now
  judges which facts answer a sub-question; conflicts need two different values.
- The decomposer got the step's wrapper ("what Arnav asked: ...") and asked about Arnav; it called a battery question
  an experiment. Fixed: the question itself is split; only what a program here can test is an experiment.
- The relevance rule dropped results that name the question's subject: fixed.
- An experiment's RESULT lines now carry their METHOD.
- A report can no longer tick an instruction whose sub-question no source answered; sentences of a sourced report that
  share few words with the verified results are flagged.
- OpenAlex (scholarly papers) was rate-limited for this machine's IP all day; a spent daily budget is now skipped
  instead of waited for.

The research hive is slower (25 to 42 minutes a question) and gives more sourced claims; on this frozen code it lost
one question outright and over-claimed on two. It has not been measured again after the fixes.

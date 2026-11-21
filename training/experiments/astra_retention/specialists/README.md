# Choosing a previously verified specialist for a new request

A chooser trained on individually verified practice wins had **no usable history for either scheduled worker on all 235 later after-body jobs** that survived exact-overlap checks. Their first two positions contained 20 distinct workers, all born after the G50–52 training period. It therefore selected the first worker and tied its **176/235**. The normal multiworker delivery scored **180/235** on the same jobs. On the before bodies the chooser could compare two known specialists on 19 fully graded requests. Changing nine selections gained zero and lost zero. [Frozen protocol](protocol.md) · [Results](results.json)

| Cohort | Matched jobs | First worker | Second worker | Prior win count | Request-word chooser | Perfect choice between these two | Actual multiworker delivery |
|---|---:|---:|---:|---:|---:|---:|---:|
| G50–52 development, after | 187 | 148 | 154 | 148 | 148 | 159 | 151 |
| G50–52 development, before | 187 | 147 | 156 | 147 | 147 | 163 | 151 |
| G53–56 evaluation, after | 235 | 176 | 177 | 176 | 176 | 183 | 180 |
| G53–56 evaluation, before | 234 | 176 | 173 | 176 | 176 | 185 | 182 |

Simply selecting the second worker on every later after-body job gained seven correct answers and lost six. The corresponding before-body comparison gained nine and lost twelve. The oracle choosing after seeing both grades finds seven potential gains over the first worker on the after bodies. It provides an upper bound for these recorded outputs. The normal hive also has disagreement resolution, later seats and file checks, so it is a distinct comparison. [Individual grades and pre-request observations](records.json.gz)

### Evidence before the choice

We retrieved all 36 practice-work ZIPs from G50–52. Each training case had to be a single request with complete recorded answers, a seat-to-actor match, and individual grades identifying just one correct worker. Of 288 practice jobs, 144 were compound, 28 had fewer than two complete answers or a blank answer, 102 had multiple correct workers, five had no winner and **nine qualified**. These supplied one to three verified unique wins each for six named actors. Unique here means among the workers who answered that practice request. Other workers might also have solved it. Compound jobs were excluded under the predeclared single-request scope. [Practice archive IDs and SHA-256](practice-artifacts.json)

Each actor's profile is the average direction of its verified practice requests in a word-frequency representation. Rare words carry more weight. Before a worker runs, the hive logs its seating order. The chooser uses the new prompt and the first two names in that initial log. It selects the better-matching profile when both workers have one. Otherwise it keeps the first seat. The grade, task kind, worker's eventual answer, and the arrival of a later deciding seat cannot influence that choice. The comparator using practice win count has the same fallback on unknown actors. G50, G51 and G52 development gates use only practice up to their own generation. The G52 index stays frozen for every later gate. [Implementation](router.py)

### Coverage and transfer

Each later arm contained 256 fresh jobs. We excluded twelve normalized exact question texts that had appeared in earlier practice and nine more that had appeared in a G50–52 fresh gate. All 235 eligible after-body jobs had both first and second worker grades. In the before arm all 235 first workers had grades (176 correct), but one scheduled second candidate lacked a matching grade, leaving 234 common comparisons. The chooser selected the observable first worker on that omitted job. Across those 234, 19 had two profiles, 37 lacked the second profile and 178 lacked both. Three of the 15 distinct before-body actors had practice profiles. The 20 after-body actors had none. Before and after share prompts and are reported separately. Independently seeded questions can still share wording and structure. [Fresh-archive sources](../minority/artifacts.json)

This replay selects between recorded worker outputs. Seat one and seat two can have different sampling settings and execution order. Moving an adapter to a new position could produce a different answer. The archive supplies no outcome for unseated specialists, no comparison of attachment scale, and no repeated weight training. The observed bottleneck is that practice happens before the new children are trained. A direct test of those children's specialist profiles would require individually verified examples for them before the release gate. This study earned no fixed-exam credits.

### Reproduce

The ledger stores normalized prompt hashes, word counts keyed by hashed tokens, initial actor order, identified practice wins and a separate scoring section. Scoring from it needs only Python's standard library and no model.

```sh
python -m training.experiments.astra_retention.specialists.router --out /tmp/hive-specialists.json
```

To reconstruct the ledger, place the original practice and fresh-gate ZIPs in one or more directories using their artifact ID as the filename, followed by `.zip`. Use the repository's Python environment. The collector verifies SHA-256 and reads only the practice or fresh prefix for each requested run.

```sh
python -m training.experiments.astra_retention.specialists.router --archives /path/to/zips --ledger /tmp/specialist-records.json.gz --out /tmp/hive-specialists.json
```

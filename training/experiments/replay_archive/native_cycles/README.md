# What three small native replay updates retained

Three native T80 candidates each kept the same **3/5** complete requests as their exact G55 parent. They retained both old anchors and added **zero** complete target solutions. The predeclared gate rejected all three. Each successive fit therefore started from the original G55 checkpoint. The study trained three separate candidates and measured their actual programs against the same fixed requests. [Protocol fixed before inference](protocol.md) · [Per-case results and accept/drop decisions](results.json)

| Native candidate | Fresh training family | Fresh / replay answer tokens | Training time | Old anchors | Target requests | New passes / lost passes |
|---|---|---:|---:|---:|---:|---:|
| G55 incumbent | — | — | — | 2/2 | 1/3 | — |
| First | Normalize and sort names | 264 / 247 | 337.12 s | 2/2 | 1/3 | 0 / 0 |
| Second | Convert a Markdown table to CSV | 268 / 214 | 313.91 s | 2/2 | 1/3 | 0 / 0 |
| Third | Fill missing CSV readings | 358 / 193 | 337.02 s | 2/2 | 1/3 | 0 / 0 |

The incumbent and all three candidates correctly calculated the new price, identified the weekday, and wrote the completed readings file with the right count. None produced the requested normalized names file or the exact CSV table. The first candidate changed its generated Python for both failed tasks. In particular it still mishandled names with a middle initial or a multiword surname. The second and third candidates produced the incumbent's exact program on all five requests. The twenty native responses took 17.94 minutes in total, excluding server startup and WASI grading. [Original model outputs and sampling settings](native-calls.json.gz)

All nine optimizer inputs completed with zero memory skips. Each fit used two distinct new G56 teacher rows and one distinct archived G55 member row. The old row contributed 48.3%, 44.4% and 35.0% of each fit's target tokens. All 196 trainable tensors matched the exact parent before the first update. Each finished adapter differed in at least 33,947,647 of its 33,947,648 FP32 values. Training used 16.47 minutes in total across the three workers. Weight changes alone would have counted all three as progress. The functional gate found no capability gain.

Each evaluation question was absent from the cumulative training archive. All six new teacher programs passed when regenerated and executed against their own checks. For the three replay examples we matched the original program bytes and question to a named actor, exact member number and an independently passing checker outcome in the original GitHub practice job. All five known-correct grader controls passed, and all five unrelated controls failed. [Archived task and actor hashes](manifest.json) · [Teacher checks](teacher-checks.json) · [Grader controls](grader-controls.json) · [Run from the original artifacts](reproduce.md)

These five development requests measure first-program performance on a small panel of practiced families. Repeating two old anchors supplies two distinct retention cases. It cannot establish a sub-1% population regression rate. None of the candidates qualified to become an improved parent. In a subsequent matched comparison, replacing each replay row with a third verified fresh example produced the same five whole-task outcomes in every pair. The distinct example received only 5% of the nominal learning rate at the third optimizer step. [Fresh-only control results](fresh_only/README.md)

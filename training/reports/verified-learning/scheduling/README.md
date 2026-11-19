# A live scheduling cell on five PSPLIB projects

The G47 programming cell delivered **0 of 5 feasible schedules**. It wrote two Python programs after seeing a general scheduling contract and three tiny examples. Both tried to decode a Python dictionary as JSON text, so neither returned start times. A later deterministic fix exposed a second defect. The proposed schedule used four units of a resource when only two were available. All three classical scheduling policies produced feasible schedules for every project.

| Project | Native cell | Public-only input fix | Shortest duration first | Longest remaining path first | Best of 64 random priorities | Proven optimum |
|---|---|---|---:|---:|---:|---:|
| j301_1 | Withheld | Withheld | 57 | 46 | 45 | 43 |
| j301_2 | Withheld | Withheld | 57 | 48 | 51 | 47 |
| j301_3 | Withheld | Withheld | 50 | 51 | 47 | 47 |
| j301_4 | Withheld | Withheld | 71 | 63 | 62 | 62 |
| j301_5 | Withheld | Withheld | 42 | 47 | 42 | 39 |

Each number is the completion time of a schedule that satisfies every precedence constraint and stays within all four renewable resource capacities. Smaller is better. The five single-mode projects have 30 real tasks plus two zero-duration endpoints apiece. They are the same development cases used in the earlier pilot. The official archive and all five raw instance hashes matched that pilot. [PSPLIB data and reference schedules](https://www.om-db.wi.tum.de/psplib/getdata.php?mode=sm) · [Earlier pilot and fixed seeds](https://github.com/Arnav123-s/HiveMIND/tree/31be615c750876003bb56336662c047536b665ab/training/reports/hive-directions/scheduling)

## How the cell was tested

The task asked for one reusable algorithm, with short completion times as its objective. It defined the integer start-time vector, predecessor indices and resource demands explicitly. Each public example included one feasible answer. The checker accepted any feasible schedule, recounting cumulative usage whenever a task began or ended and verifying all precedence edges. The writer received no benchmark project, reference schedule or makespan. The five projects and their order, public selection rule and evaluator were frozen before the first generation.

The Ternary-Bonsai 8B base used its G47 code2 adapter on CPU, two inference threads, greedy decoding and seed 60631. The two allowed attempts had a ceiling of 640 output tokens each. The cell used 432 and 335 output tokens in 250.5 and 193.1 seconds respectively on the shared host. The second prompt included the original source, first public counterexample and the actual guest error. Each submission produced **zero feasible answers on three public examples**. The public gate therefore released no solver. After selection, all ten diagnostic executions of the two frozen programs on the five projects returned the same type error. A makespan is defined only for a feasible schedule.

A supplementary arm was frozen after observing the first public error and before any benchmark grades. It used the production repair selector with a budget of eight public candidate checks and zero additional model calls. The sole eligible candidate corrected the JSON input error and produced feasible makespans of 4 and 3 on the second and third examples. On the first it started three tasks together at time zero, with a combined demand of four units against capacity two. Resource capacity was read from the request but never used to place the tasks. The public checker withheld the candidate.

The classical comparison reran the first pilot's 330 schedules and reproduced the fifteen retained start vectors exactly. The deterministic priorities used one schedule per project and the random-priority search considered 64 per project. The random search matched two published optima. Its best schedules average 49.4 time units against a 47.6 optimum average. These five cases and one cell do not establish a population success rate.

## Reproduce the scores

Use the HiveMIND Python environment and the CPython WASI SDK. The evidence contains the exact prompts, both raw model replies and programs, public checks, all ten diagnostic benchmark executions, normalized projects, reference start vectors, data hashes and rescue candidates. The verifier re-executes both programs in the guest and independently checks every retained classical start vector.

```bash
python training/reports/verified-learning/scheduling/verify.py --checkout . --sdk /path/to/wasi
```

## Post-study scheduling command

After the native trial, the project added a deterministic scheduling command that constructs and checks several classical priority schedules. An integration replay launched a fresh CLI process for each of the five original projects. Each call received only its capacities and jobs through an anonymous file. The bank was disabled and no inference binary was available. The study checker independently scored the resulting starts.

| Project | CLI makespan | Proven optimum | Difference | Winning classical draw |
|---|---:|---:|---:|---:|
| j301_1 | 45 | 43 | +2 | 47 |
| j301_2 | 47 | 47 | 0 | 10 |
| j301_3 | 47 | 47 | 0 | 3 |
| j301_4 | 62 | 62 | 0 | 3 |
| j301_5 | 40 | 39 | +1 | 39 |

The CLI produced five feasible schedules and matched three published optima. Each of the five fresh CLI processes finished in 0.20–0.28 seconds on this host, including startup. The command used one fixed seed, 2808, across all projects. The earlier pilot used project-specific seeds 2808 through 2812 for its random reference policy. The CLI draws in this table are one-based. The native solver and its deterministic input fix remained withheld in the original trial. The five schedules in this integration replay came from the supplied classical algorithm. [Full CLI receipts](cli-results.json)

```bash
python training/reports/verified-learning/scheduling/cli_replay.py --checkout .
```

A separate CLI check generated 60 feasible projects, including 43 with zero-duration tasks and 54 with jobs listed out of dependency order. Independent precedence and resource checks passed for all 60. The ten smallest matched exhaustive scheduling of integer start times. All 16 malformed, cyclic or impossible inputs exited with an error and no plan. Two purpose-built bank fixtures exercised the optional WASI path on j301_1. The CLI accepted an independently found 43-unit witness over its 45-unit baseline and rejected an all-at-zero proposal that violated precedence. Those fixtures tested whether the serving path selects and rejects schedules correctly. [QA cases and receipts](qa-results.json) · [QA runner](qa.py)

## Try a community kitchen schedule

The example has two volunteers and one oven. Preparing ingredients takes one volunteer for 20 minutes. Cleaning the oven takes another volunteer and the oven for 10 minutes. Baking needs one volunteer and the oven for 30 minutes after both preparations finish. Packing the meals then takes both volunteers for 15 minutes. In the input, demands follow the capacity order of volunteers, then ovens. Each job lists its required predecessors by their zero-based indices. [Example order](example.json)

```bash
./hive schedule training/reports/verified-learning/scheduling/example.json
```

The returned starts are `[0, 0, 20, 50]`. The two volunteers begin preparation and oven cleaning together. Baking runs from minute 20 to 50, then packing finishes at minute 65. Preparation, baking, and packing must occur in that order, so their 65-minute total is also a lower bound.

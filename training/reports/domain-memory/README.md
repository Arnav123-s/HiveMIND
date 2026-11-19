# What the hive remembers and when it uses it

On this branch, ordinary chat and program work use the hive's default memory and subject signals. Coding, math, physical science, conversation, machine learning and computer engineering share the same base language model. The cells have the same size. Their small weight differences come from practicing different tasks. A worker with more practice on code can still check another worker's math. The branch incorporates the generation 50 record. That generation was dropped, so the recorded live body is generation 49.

## What happens when you ask

1. A saved, independently checked method gets first chance at a task it recognizes. A saved price-quote calculator can return the difference between the highest and lowest quotes without loading the language model.
2. On the language-model path, one small sender reads your latest message. A second reads your last user turn if available. A reader receives their short numeric signals. The project calls this exchange *telepathy*. A second text classifier must agree before the hive uses the subject suggestion. The ordinary chat-or-work decision still decides whether a calculation needs programs.
3. The suggestion can supply an otherwise unspecified specialist seat or a subject-specific instruction. Explicit requests for files, sources and other recognized work retain their existing routing. An explicit, narrowly recognized task or a named local convention can also select a checked edit when the subject channel withholds advice. A decision about a small part of a larger task goes to the first worker. The other worker independently attempts the task.
4. File checks, program results and disagreement handling run as before. Python callers of `team.talk.reply` can inspect `domain_signal`, `engram_advice` and `engrams` when present. The first records a subject suggestion, the second an attempted small decision and the third direct use of weight edits. A suggestion alone does not establish a better answer.

**Which weights actually answered?** The CPU engine can cache a computation built with the preceding edit. An adapter-equipped server now rebuilds that computation, resets prompt reuse when switching edits, and holds the switch through the reply so a second request cannot change the first request's weights. The release checks the weight file's hash and distinguishes a model suggestion from a separately verified result. [Serving implementation](../../../team/ternary.py) · [Native validation and controls](../domain-engrams/README.md)

## What each starter edit was taught

Each candidate changes only the output layer of the same 8B model. It learns to choose a short label for one decision. The fitted factors use 16-bit floating-point numbers. Each shipped weight file is about 1.25 MB. The release index identifies the candidates that qualified on a question for every label.

| Subject | Decision used in teaching | Default release |
| --- | --- | --- |
| Coding | Choose a Python operation to transform, filter or sum a collection | Shipped, 3/3 with and without the edit |
| Math | Choose length, area or volume for a geometry question | Shipped, 3/3 with and without the edit |
| Physical science | Identify the equilibrium phase of pure water at normal pressure | Revised edit shipped, 9/9 new cases |
| Conversation | Choose whether to ask for missing information, confirm an arrangement or thank someone | Shipped, 2/3 → 3/3 |
| Machine learning | Choose training, validation or test data for a model-development step | Shipped, 3/3 with and without the edit |
| Computer engineering | Choose nanoseconds, microseconds or milliseconds for a timing quantity | Withheld, 3/6 new cases |

The two corrected candidates each received 27 teaching questions. On nine independent water questions the base got four right, the first edit got six, and the revised edit got all nine. The ordinary model server independently returned all nine right plus three previously seen answers. On six independent timing questions the corresponding scores were two, two and three. The timing edit answered all three previously seen questions, which would have given a misleading picture of readiness on its own. Computer engineering still has subject routing, local learning and the checked cache-line method described below. [Native and serving results](../domain-engrams/README.md)

A person can ask an ordinary question. A broad subject match alone cannot apply one of these label-only edits to an unrestricted answer. The hive checks the task's wording and can consult a matching edit about a smaller decision. A direct request to choose from its labels can put the edit on the answer itself. [Training, qualification and native activation](../domain-engrams/README.md)

On twelve public examples written for these six decisions, ordinary generation 49 chat gave nine correct answers. Eight requests activated a starter weight, and every shipped weight activated at least once. Of six requests for a single label, five received the right content and three also got the requested format. In one Python question the specialist selected the requested built-in, `filter`, but the final answer recommended a list comprehension. Correct advice can still be lost when another cell writes the answer. [Serving examples and raw replies](../domain-engrams/README.md)

**Where factual verification still fails.** Two workers printed that pure water at 72 °C and one atmosphere was gas. Running both programs confirmed only that they printed the same thing. On a real repeat the specialist again produced an unusable token, and the added equilibrium check correctly returned “The water is liquid.” The check recognized a limited range of requests. On a separate test with four new phrasings, an injected wrong phase still reached the user on all four, through both chat and worker agreement. This was a test of whether a wrong answer gets caught, with no model inference. The nine correct one-token predictions in the water qualification and the delivered-answer checks measure different things. [Real failure and replay](current-body/water-replay/comparison.json) · [Independent conflict tests](../domain-engrams/water-v2/delivery-control/post-generation/README.md)

## How corrections survive

The normal practice loop can record what a member wrote when the task's own check confirms that exact submission. Fieldwork can collect the public input/output examples of a solver that passed separate checks. You can explicitly teach a local convention. Give different conventions distinct topic names.

```sh
./hive learn teach --domain machine_learning --topic "audit codes 2026" \
  --prompt "Under audit codes 2026, which label marks a split used for early stopping?" --answer validation
./hive learn status
./hive learn refresh --domain machine_learning
```

Run `./hive learn list` to see the verified weight edits actually available on this machine. Teaching one example records it. To qualify a native edit, the trainer needs at least two distinct short labels with fitting and reserved examples for each. It fits the edit on the installed 8B model and tests it on the reserved questions. A replacement must preserve every measured correct answer of its active predecessor. A contradictory label for the same prompt and topic suspends the affected local edit and keeps both records for inspection. Separate named topics let an older convention remain available on its own terms. Local examples and learned weights live under `runs/engram-learning` by default. On hosted practice, the workflow can cache generated lessons per training shard and archive them for recovery. Personal labels remain local. [Learning and restore instructions](growth/README.md) · [Learning code](../../../training/engram_growth.py)

## Use the original four-bit sensor pair

```sh
./hive --once 'Check sensor banks [1,2,-1,0] and [-2,1,1,0]'
```

For the project's sensor layout, the readings are 4 and −2. One is positive and their sum is positive. The saved four-bit pair gets the second decision wrong on this input. The ordinary command compares its estimates with the readings, returns both correct decisions and tells you what was corrected. This works in a clean checkout with standard Python. Across 4,384 fresh inputs, the served answers matched the exact calculation on every input, including 608 corrections to the learned pair. [Sensor layout, stress cases and archive parity](sensors/README.md)

## Why two workers agreeing can still be wrong

Two workers each printed 1 for a four-byte access starting at address 62 with 64-byte cache lines. Bytes 62 and 63 occupy the first line. Bytes 64 and 65 occupy the next. The checked method now returns **2** on the ordinary command line. It also guards against recording a matching wrong answer as verified when workers run directly. This is an engineering repair made after the original trial.

On 2,048 fresh numeric layouts, the method agreed with independently counting which line each byte occupied. In a separate blind prose test the normal command returned five of six eligible answers and passed one unrecognized question to normal work. It left all three out-of-scope questions alone. [Cache-line example and verification](cache-lines/README.md)

## A new machine-learning convention

A user-defined audit used X for data leakage and Y for class imbalance. The 8B model received four labeled training examples first. It still got one of two separate incidents right, so the hive rejected the edit. With ten training examples, the base model still answered X on all four reserved incidents. The learned edit answered all four correctly, including both incidents from the first round. A fresh CPU server reproduced all eight before-and-after answers from the saved file. Ordinary chat then received a named audit question and returned the correct single letter, X, with the learned edit active. The labels came from a person. This measures learning a local convention from feedback. [Inputs, saved weights and ordinary-chat response](growth/README.md)

## Independent measurements

| Test on the first released bank | Result |
| --- | --- |
| First-token answers across all six candidate topics | The base answered 14/18 and the adapted model answered 15/18. The conversation edit changed an incorrect thank-you into the requested appointment confirmation. Four edits qualified. |
| Actual answers to twelve broader practical questions | The previous system, subject signals alone and the first integrated bank each delivered the same 3/12 in the requested first-answer format. All three kept 4/4 elementary answers. |
| Broader content measure including clear answers in prose | 5/12 for the previous system, 4/12 with signals, 3/12 with the first bank. Across all sixteen requests the three runs reached the 150-second deadline three, four and five times. |

Each broad trial used the same base and five generation 47 member edits on the available CPU. Its twelve practical questions covered all six subjects. The raw traces show zero starter weight activations on this broader panel. The trials shared CPU resources with other work, which affects deadline comparisons. This study preceded the cache-count and integer-format repairs. [Exact prompts, scores, timings and replay](answers/README.md)

The later replay delivered five of the same twelve practical answers and retained all four elementary answers. The hive now returned `2` for the cache-boundary case and `60` for classifier recall. The third diagnosed case, venue capacity, still timed out. Across the other nine practical requests the score stayed at three. Four requests hit the time limit. No question activated a starter weight. Counting correct answers delivered in prose, the previous and final versions each scored 5/12. The panel had already been seen during development. [Replay protocol and per-case comparison](answers/README.md)

Two released generation 49 workers also tried a fresh repair-café task. Given seven envelopes of eighteen washers, with 23 reserved and 31 handed out, each independently wrote and ran a program that returned 72. The ordinary interface delivered `72`. A second ordinary question received `Helsinki` for Finland’s capital. Both requests together took 237 seconds on two shared CPU threads. [Current-body requests, programs and timings](current-body/README.md)

On the first 60 subject questions, the two senders alone referred 26 to specialists and got 23 of those referrals right. A simpler text classifier made more correct decisions overall. Requiring agreement with that classifier removed two wrong referrals and three correct ones. It still misclassified one question. On 30 fresh questions, the default agreement rule made seven suggestions and all seven were correct. It withheld advice on 17 of the 24 supported questions and on all six unsupported ones. This is a choice about how often to give advice. It has a real coverage cost. [Original audit](signals/README.md) · [Fresh confirmation](signals/consensus/README.md)

A separate study tested whether the chosen memory could answer the kind of question being asked. The first rule consulted a label edit for five of twelve related requests that needed a different kind of answer. The revised rule requires an actual request for the decision that edit learned. On twelve new requests using the same four released edits, inappropriate consultations fell from one of six to zero of six. Both rules reached three of six appropriate requests on every route and one further request on the direct-answer route. This measures selection, before generating an answer. [Microtask scope checks](scope/README.md)

The original sensor experiment solved both of its numerical decisions on 96.6% of fresh examples using two eight-bit signals. That experiment used disjoint sensor readings and synthetic data. The text senders in this branch learn new weights from example requests. The earlier t17 engram study found that short instructions explained the apparent advantage on its program tasks. Both results motivated separate measurements of actual answer quality on this branch. [Prior communication evidence](../rule_lab/hive-telepathy.md) · [Earlier engram and recall research](../rule_lab/engrams-and-bitnets.md) · [Paired 8B practical-answer study](answers/README.md)

The previous fast lookup for growing collections of memories is back on the ordinary recall path. On a synthetic catalogue of 1,024 records, 180 repeated lookups used 7.61 seconds of CPU time before the change and 0.52 seconds after it. The comparisons preserved the selected memories, their order and activation strengths, including after additions, deletions and retirement. The benchmark timed lookup against small files. [Reproduction and file-integrity checks](recall/README.md)

The current serving engine loads available compatible weight files into memory at startup and changes their activation per request. The measured hardware and panel sizes do not establish how many thousands of edits a single CPU server could serve. The next research questions concern partner compatibility, when to ask for a specialist, and how to detect loss of earlier skills. [Research and primary sources](research.md)

The six subjects identify areas where the hive can consult a specialist. Solving a hard unseen problem and preserving a skill after thousands of updates require separate evidence.

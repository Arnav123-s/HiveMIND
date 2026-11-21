# Prospective check on three new file tasks

Both settings scored **0/3**, with no gains or losses. None of the three workers reached the condition that lets it borrow tokens. Every case was generated and registered before inference, in a different task kind from the earlier successful CSV editing repair. The normal grader checked each file together with the worker’s printed answer. [Frozen requests](registration.json) · [Full native evidence](native.json)

| Registered task | What happened | Fixed | Borrowed | Tokens in each arm |
|---|---|---|---|---|
| Filter records by date and print their total | The worker never saved the output file. Its last program printed Python's description of a CSV reader. | Fail | Fail | 427 |
| Save the highest-ranked rows and name the winner | The worker saved ten rows where the task required eight and gave no answer. All three replies ended normally. | Fail | Fail | 529 |
| Mask synthetic card patterns in text and give the count | All three replies reached 192 tokens. The worker never saved the requested file. | Fail | Fail | 576 |

The fixed arm made nine genuine native model calls. For each task the treatment independently reran the worker and its grader from an empty directory. Every request, including the prompt and cap, matched its control, so it reused all nine native responses. Each arm consumed 1,532 output tokens when shared responses are charged. Ranking and redaction had exactly matching files, stdout and grades. The dates workers had matching file outcomes and grades, but the Python reader's printed process address differed. The preregistered byte-for-byte output criterion failed on that task.

Checkpointing exposed two measurement problems. Python syntax errors include the workspace's absolute path, so a new temporary name on restart would have altered the model's next request. The runner preserved the two existing native calls and recreated the same empty private workspace per task. It verified the entire next request before reusing a response. Later, exact responses to the dates task revealed the process-address difference. The recorder now preserves both raw answers and reports which equality checks fail, alongside the unchanged official grades. It reused all six previously recorded requests and responses for that case without another native sample. The receipt records both checkpoint migrations. [Initial protocol](protocol.md)

The earlier selected CSV edit is still a verified recovery. Its worker had already saved the correct file when a capped reply omitted the print statement. These three new tasks primarily failed earlier in the work. They offer no independent evidence of a broader score gain. [Matched successful case](../continue_budget/README.md)

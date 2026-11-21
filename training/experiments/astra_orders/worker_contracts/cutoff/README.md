# Recovering from an output limit

`HIVE_CUTOFF_REPAIR=1` helps a ternary worker distinguish a server-enforced output limit from a program that simply contains a syntax error. It acts when the server reports a length stop, the reported output equals the requested cap and the executed source fails to parse. The next request carries the syntax diagnosis and asks for shorter, complete code. Any larger per-turn allowance comes from the remaining total output budget.

## Cold-chain

The original inspect worker hit its 192-token limit three times, each time cutting off at the same unfinished file write. The repair worker generated the identical first reply byte for byte. With the new feedback it used 104 tokens on the next reply, which ran and exposed a closed-file error. On its final turn it used 86 tokens, printed the correct count of 3 and wrote a JSON array containing all three correct lot codes.

The array was ordered P4, J7, A6. The grader required A6, J7, P4. **Both arms failed the same whole-task grade.** The change recovered an executable program, the file, its requested element type and the count. Each arm had three calls and the same maximum of 576 generated tokens. The repair used 382 tokens in total and the original used 576. [Original turns and files](../native.json) · [Recovery turns and files](native.json)

## Fixed CSV edit

All three freshly generated replies matched the original inspect arm byte for byte. Each reached 192 tokens and ran successfully. They wrote the correct CSV but stopped after a comment, before printing the requested count. The syntax-repair condition therefore had no reason to fire. The file, conversational messages, empty answer and failed whole-task grade were identical. Across the two paired tasks the original and syntax-repair workers both scored 0/2. [Original native records](../native.json) · [Fresh recovery condition](native.json)

The 14 native generations in the original first-turn study and the 18 in the diverse-order follow-up all stopped normally below the 192-token cap. None would have activated this repair. The hosted F3 stock-versus-inspect exam keeps its original worker settings. [F3 conditions and capability measurements](../README.md)

To repeat the follow-up, use the [native worker command](../README.md) with a fresh output path and add `--cutoff-repair`. One completed arm can be checkpointed with `--arms-this-session 1`. Use `--resume` to continue a checkpoint with the same model, settings, number of CPUs and task order. [Protocol](protocol.md)

# The hive's life: jobs it noticed by itself, and who holds them

Written by `python -m team life` on 2026-11-09 21:47 from the members' logged calls.
A site is one member with one instruction. A job is a site whose replies are a few fixed values.

## Spawned cells

| cell | does a job of | labels (it may answer) | decisions | status | newest unseen decisions: answers / agrees | live: answered, audits, agreement |
|---|---|---|---|---|---|---|
| sp_verifier_75e567 | verifier | SUPPORTED / UNSUPPORTED (SUPPORTED, UNSUPPORTED) | 72 | candidate | not trained yet | 0, 0, no audits yet |

## Every call site in the logs

| member | calls | member time | a job? | why / status | instruction starts |
|---|---|---|---|---|---|
| researcher | 39 | 3168 s | no | 26 of 39 replies are not a small fixed value | You are the researcher on Arnav's team. Read the SOURCES and pull out  |
| condenser | 18 | 1378 s | no | 18 of 18 replies are not a small fixed value | You shorten a long source for a teammate. Keep only the lines that hel |
| researcher | 40 | 449 s | no | almost always the same reply ('none', 40 of 40) | You are the researcher on Arnav's team. Choose where to look for the i |
| verifier | 72 | 349 s | yes | a job: 72 decisions (new candidate) | You are the verifier on Arnav's team. Decide if the QUOTE, taken from  |
| juror_brain | 33 | 319 s | no | almost always the same reply ('PASS', 33 of 33) | You are the verifier on Arnav's team. Check one piece of work against  |
| juror_brain | 54 | 317 s | yes | 54 distinct decisions logged, 60 needed | Decide if ONE item meets every requirement of the task, using only its |
| juror_fast | 33 | 292 s | no | almost always the same reply ('PASS', 32 of 33) | You are the verifier on Arnav's team. Check one piece of work against  |
| verifier | 33 | 276 s | no | almost always the same reply ('PASS', 33 of 33) | You are the verifier on Arnav's team. Check one piece of work against  |
| critic | 7 | 204 s | no | two replies start with the same letter | You check a report before it goes to Arnav. Arnav's rule: everything h |
| coder | 1 | 121 s | no | 1 of 1 replies are not a small fixed value | You are the coder on Arnav's team. Write one complete Python 3 program |
| coordinator | 4 | 113 s | no | 4 of 4 replies are not a small fixed value | You coordinate a team of AI specialists working for Arnav. Break his t |
| writer | 5 | 96 s | no | 5 of 5 replies are not a small fixed value | You are the writer on Arnav's team. Write the finished deliverable in  |
| browser | 3 | 55 s | no | almost always the same reply ('goto', 1 of 3) | You are the browser operator on Arnav's team. You control a real web b |
| plan_reviewer | 2 | 24 s | no | almost always the same reply ('false', 2 of 2) | You review a plan for Arnav's task before the team starts. Arnav's rul |
| code_reviewer | 1 | 20 s | no | almost always the same reply ('true', 1 of 1) | You review a program a teammate wrote for Arnav, after it ran. Decide  |

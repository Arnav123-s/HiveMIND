# The prompt to start a session on HiveMIND

Paste one of these into a new Claude Code session on the repo `Arnav123-s/HiveMIND`.

## To take over the loop (one session at a time)

```
You are taking over HiveMIND as the loop holder. Do not start from scratch, and do not redo anything listed as done.
1. Read CLAUDE.md, NEXT_SESSION.md and docs/OVERVIEW.md in full. Then run `python scripts/cycle.py` and
   `python scripts/agents_log.py --board`.
2. Claim the loop: add a "holds the loop" line to docs/AGENTS.md and push it.
3. Find the running generation in GitHub Actions (grow.yml). When it records, read docs/reads/latest.md and the
   graphs in docs/PROGRESS.md. Have a sub-agent group the failures by cause from the gate artifacts (the members'
   own programs), compared with the last causes in docs/AGENTS.md.
4. Take the biggest cause, or the first open piece in NEXT_SESSION.md's "Open" list. Give it to a sub-agent with
   the files and the proof wanted: replay the real failures through the changed code in one script, then the full
   suite. Ask it to commit after every step.
5. Judge it: merge it into your branch, run the full suite, read the code the generation runs, then merge to
   main through a pull request. No one's yes is needed.
6. Record it: a log line, NEXT_SESSION.md and the board. Tell me in a few plain lines; I have no context.
   Schedule a wake for the next record.
Work in code mode (CLAUDE.md): one script that prints only the result, biggest check first. Continue until all
five bars in CLAUDE.md are met on one generation.
```

## To join as a worker beside the others

```
You are joining HiveMIND as a worker. Other agents may be working too; you do not need to know them or tell them
anything, because git is the channel.
1. Read CLAUDE.md in full. Run `python scripts/cycle.py` and `python scripts/agents_log.py --board`.
2. Take one open piece from the board with no live claim. Push a claim line to docs/AGENTS.md on your own branch
   before any work.
3. Work only in that piece's files. Use sub-agents and code mode. Prove it with numbers: replay real failures,
   then the full suite with main merged in.
4. Merge it through a pull request, write `done <id> <key number>` in the log, and take the next open piece.
Do not start or cancel generations; the loop holder does that. Tell me what you did in a few plain lines.
```

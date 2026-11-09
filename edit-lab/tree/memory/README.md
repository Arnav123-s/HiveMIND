# memory/

The team's long-term memory. Everything here except this file stays out of git (it is yours).

| file | what it is | who writes it |
|---|---|---|
| `profile.md` | how you like things done ("short answers", "prices in INR") | you, or `python -m team remember "..."` |
| `policy.json` | standing approvals: `{"spend": "ask", "delete": "ask", "send": "ask"}`; each can be `ask`, `allow` or `deny` | you |
| `lessons.jsonl` | one-line rules learned from verified failures | the team, while dreaming |
| `runs.jsonl` | every finished task: what you asked, step verdicts, start of the report | the team |
| `schedule.json` | recurring tasks for `serve`: `[{"task": "...", "every_hours": 24}]` | you |
| `dreams.jsonl` | what each dream cycle did (distilled examples, lessons, retrain before/after) | the team |

Credentials are NOT kept here. They go in `~/.agent-team/credentials.json` (see README).

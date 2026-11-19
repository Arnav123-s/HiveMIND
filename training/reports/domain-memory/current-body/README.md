# Generation 49 on the ordinary chat path

Two released G49 members wrote and ran separate programs for a repair café. Seven envelopes contained 18 washers each. The café reserved 23 and handed out 31. Both programs printed `72`, and the ordinary chat interface returned exactly `72`. The independent key was fixed before inference. The native server reported `g49trunk` at scale 1 for the first member and `g49code2` at scale 1 for the second. Each produced its program on the first turn and used a second turn to finish. The selected programs and their printed outputs are in the [receipt](receipt.json).

A separate direct question on the same installation asked for Finland’s capital. The reply was `Helsinki`. Both the routing call and the direct answer used the base T80 model with all edits at zero. The five qualified starter weights and the G49 data specialist were loaded and available throughout. The observed requests activated the trunk and code specialist only during the arithmetic task.

The full run took 237 seconds on two shared CPU threads, including 187 seconds for the arithmetic task and 48 seconds for direct chat. The server ran the pinned native binary with `--no-graph-reuse` and was stopped after the two requests. This single predeclared arithmetic case confirms the installed body launches and can produce a checked answer. The [broader paired answer study](../answers/README.md) used its own frozen setup and measures separate questions.

## Reproduce the requests

Use a checkout of `19992ca4ae4c46f6d5f79eb6dbc3f9fd47fc8d9e` with the T80 model and pinned native runtime installed. The [public release](https://github.com/Arnav123-s/HiveMIND/releases/tag/hive-grown) contains the three G49 files used here. These commands install them in a temporary directory under their runtime names. Their SHA-256 digests, release asset IDs and public URLs are in the receipt.

```sh
export HIVE_ADAPTERS_HOME="$(mktemp -d)"
for edit in g49trunk g49code2 g49data2; do
  curl --fail --location --silent --show-error \
    "https://github.com/Arnav123-s/HiveMIND/releases/download/hive-grown/t80.$edit.gguf" \
    -o "$HIVE_ADAPTERS_HOME/t80+$edit.gguf"
done
export HIVE_MEMBERS=t80+g49trunk,t80+g49code2,t80+g49data2
export AGENT_TEAM_THREADS=2 AGENT_TEAM_SOLO=2 HIVE_BANK=off
./hive --once 'A repair café received 7 envelopes with 18 washers each. It set aside 23 washers for Saturday and handed out another 31 today. How many washers are still available? Calculate it with a program and reply with just the integer.'
./hive --once 'What is the capital city of Finland? Reply with just the city name.'
```

The recorded test called `team.talk.reply` directly and observed the active native scales after each model call. It remapped the loopback port and used fresh private run and memory directories. The second worker used the normal sampling temperature of 0.7, so another run can generate different code. The active body manifest identified G49, and this check installed three of its released members. [Body manifest](../../../../cells/body.json) · [T80 base](https://huggingface.co/prism-ml/Ternary-Bonsai-8B-gguf/tree/c2aefbeb4b24469cd11579c3384b990404c17a30)

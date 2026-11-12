# Using the hive

One command, from this directory:

```sh
cd ~/workspace/edit-lab
```

Every call is audited at load: if any registered artifact's bytes
differ from its adoption record, the command refuses to serve
(fail-closed). Every answer names the artifact that produced it
and the held-out score that artifact earned.

## The six jobs

**Secret line** — is this line a hard-coded secret or benign?

```sh
python3 hive.py secret 'api_key = "sk-live-9f27ac41bd"'
# ANSWER: secret
# served by: secret-line-model-v3 (ternary, held-out 1.0)
```

**Error class** — which exception does this failure text show?

```sh
python3 hive.py error 'Traceback (most recent call last):
  File "app.py", line 14, in <module>
    print(user["email"])
KeyError: email'
# ANSWER: KeyError
# served by: error-class-model-v2 (ternary, held-out 0.9833)
```

**Commit type** — the conventional-commit type of a message:

```sh
python3 hive.py commit 'repair the broken cart total calculation'
# ANSWER: fix
# served by: commit-type-model-v2 (fp, held-out 0.9625)
```

**Contract judgment** — does this snippet break the house contract
(it must not mutate its input, and must be empty-safe and
none-safe)? Code goes in with `--file`:

```sh
python3 hive.py contract --file snippet.py
# ANSWER: no-empty-guard
# served by: contract-judgment-model-v2 (fp, held-out 1.0)
```

**Gap move** — what growth move does this failure/lesson call for?

```sh
python3 hive.py gap 'the model keeps failing on inputs it has never seen; we need broader training coverage'
# ANSWER: harvest
# served by: gap-move-model-v3 (ternary, held-out 0.9444)
```

**Bug pattern** — what defect does this function carry (or is it
clean)? Served through the waking-dream layer: candidate defects
must prove themselves by execution before they are believed, and
the output says whether verification fired:

```sh
python3 hive.py bug --file buggy.py
# ANSWER: swapped-operands
# served by: bug-pattern-composed (14 members) + waking-dream serving layer
# waking-dream: VERIFIED swapped-operands by execution (composer alone said clean)
```

## Extras

- `python3 hive.py jobs` — list every serving artifact, its
  substrate, held-out and battery scores, the fallback chain, and
  what is shadowed (adopted but never served).
- `--substrate ternary|fp` on any classify job names a substrate
  instead of the serving default (e.g. the secret-line founder
  ternary pack: `python3 hive.py secret --substrate ternary '...'`).
- Code-typed jobs (`contract`, `bug`) accept inline text too;
  `--file` is just easier for multi-line code.

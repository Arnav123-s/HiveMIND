# Hosted chat replay

The GitHub Issues chat can use the two checked methods shipped with this report before fetching the 8B model. A local replay ran the saved-method shell step from the workflow in four fresh work directories. It used the pinned CPython WASI 3.13.9 SDK already present on the machine and installed wasmtime 36.0.0 in the isolated environment when requested. The replay did not contact GitHub or run the model.

| Latest thread message | Result | Created a guest environment |
| --- | --- | --- |
| `Run quote_spread with {"quotes":[250,180,220]}` | 70 cents | Yes |
| `Run transit_tickets with {"minutes":[51,0,49,50]}` | 2 tickets | Yes |
| `Hello, could you tell me a story?` | Continued to the model job | No |
| `Run the saved method quote_spread with {"quotes":[80,65]}` with `HIVE_BANK=off` | Continued to the model job | No |

Both successful replies were written to `reply.md` and the workflow summary. The step emitted `answered=true`, which skips the body fetch, model setup and model reply. For the two other messages those three steps remained eligible to run. The quote method digest begins with `469bc88caa83` and the ticket method digest begins with `8af7b31d4a59`.

To rerun the checks from the repository root on Linux, activate a Python virtual environment containing the project's test dependencies, including pytest and PyYAML. The setup command installs the pinned guest and wasmtime into the active virtual environment. The test runs both checked methods in WASI, executes the workflow shell for the two fallback cases, and checks the model-step conditions.

```sh
export HIVE_FIELDWORK_SDK="$PWD/runs/fieldwork-assets/wasi"
python scripts/setup_fieldwork.py
HIVE_FIELDWORK_WASI="$HIVE_FIELDWORK_SDK" python -m pytest -q tests/test_talk_hosted_saved.py
```

[Hosted chat workflow](../../../.github/workflows/talk.yml) · [Workflow and CLI checks](../../../tests/test_talk_hosted_saved.py) · [Checked programs](live/example-bank)

## Run a method locally without writing JSON

From the repository root, point the CLI at the example bank and list its two checked methods. On an interactive terminal you can choose one by number. You can also name it directly and enter its inputs at the prompt.

```sh
export HIVE_BANK=training/reports/verified-learning/live/example-bank
./hive skills
printf '250, 180, 220\n' | ./hive skills quote_spread
```

The price request prints **70** cents and identifies the checked program that calculated it. The guided command can also collect named fields, and it asks for JSON when a saved method's input shape is unfamiliar. A name with several contracts can be selected by the `name@id` shown in the listing.

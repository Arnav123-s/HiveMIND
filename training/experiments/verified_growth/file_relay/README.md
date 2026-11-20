# Checking Python files a worker has already written

This proposal looks for a single Python module named in a user's request, literal examples for each named function, and a previous failed delivery. It removes top-level worker drivers, runs the retained declarations in the repository's WASI guest, and publishes a file only when all candidates passing the examples agree on the requested values. Its input is a user message and ungraded worker source. It receives no official checks. It handles literal calls to standalone functions; class construction, additional user files and instructions outside its recognized forms defer to the incumbent.

A small development exercise recovered `stock.py` and the value 22 from a worker driver. Five controls withheld, including one where two candidates passed the public examples and disagreed on the new input. On the 30 official fixed requests, its contract applied to zero requests for either G51 or G52. The earlier G52 duration result involved a taught task. This extension produced no gain on the fixed unseen exam. [Source and predeclared applicability](protocol.md) · [Controls](controls.json) · [Official outcomes](../release/README.md)

```sh
python -m training.experiments.verified_growth.file_relay.check --sdk /path/to/python-wasi-sdk --out /tmp/file-relay.json
```

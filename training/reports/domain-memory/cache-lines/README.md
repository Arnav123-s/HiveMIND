# Count the cache lines a load touches

A four-byte load from address 62 touches two aligned 64-byte lines. The first two bytes are in line 0 and the next two are in line 1. During the earlier CPU model panel two independently sampled workers both emitted `print(1)`, and the hive confirmed `1`. The current CLI returned `2` for that released question. This retrospective correction is recorded separately from the prospective scores below.

```sh
./hive --once 'With aligned 32-byte cache lines, a 6-byte read starts at address 0x3e. How many distinct lines does the access touch? Reply with just the integer.'
# 2
```

The local method interprets the line size, starting byte address and positive contiguous access width. It divides each inclusive endpoint by the line size using integer division, then counts the line indices between them. Addresses and their endpoints must fit in 64 unsigned bits. Saved user methods retain priority. The ordinary CLI can run this calculation without an 8B model. When workers are invoked through `solo` directly on a recognized request, two workers must each print the independently calculated count for the hive to confirm them. This is a handwritten method.

| Prospective check | Observed result |
| --- | --- |
| Six separately authored, answerable requests | 5 exact CLI answers, 1 eligible request declined |
| Three requests with an unknown start, two possible starts, or a question about cycles | All 3 declined by the local method |
| Wrong checked answers on the prose panel | 0 |
| Generated numerical layouts in one supported wording | All 2,048 matched byte-by-byte enumeration, including first and last line |

The missed request described line spacing and width in separate clauses. The method could not identify the explicit line size there. All nine cases remain in the report. A declined request goes to the established fallback. This check did not measure what a model would say on those four requests. The 2,048 calculations vary addresses, access widths and 16 line sizes. Their common sentence form tests arithmetic and boundary handling.

From the repository root, run `python training/reports/domain-memory/cache-lines/evaluate.py`. The script grades the nine predeclared requests and the seeded numeric sweep. Its claimed cases use the installed `./hive --once` entry point. The focused integrations can be rerun with `python -m pytest -q tests/test_cache_lines.py`.

[Independent protocol](protocol.md) · [Questions](cases.json) · [Scoring keys](keys.json) · [Results](results.json) · [Earlier panel](../answers/panel.json)

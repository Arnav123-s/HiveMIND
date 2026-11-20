# Blind literal-call intake panel

This small English panel checks a parser that extracts public examples and requested literal calls for a pair of functions in one Python file. It has eight fully specified requests and five requests for which a pure local call cannot meet the request. It uses no archive traces or model outputs. The panel author wrote the requests and expected data without inspecting the parser.

For each ID in questions.json, record the parser's first decision. Compare against expected.json after recording results. For extraction, require the expected filename, the full set of function names and public example pairs, and the ordered list of requested calls. Compare literal values including their types (a boolean differs from an integer). Treat whitespace and quote style in calls as equivalent. Ignore the order of examples and function declarations. A withheld positive is a missed extraction. An extracted negative is a false acceptance. Report both counts independently. This checks intake only. It does not grade generated function implementations, conversational quality, or broader unseen-task ability.

Check the freeze by running `sha256sum -c manifest.sha256` in this directory.

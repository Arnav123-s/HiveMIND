# Five-token speculative decoding on CPU

Use the same clean T80 target, greedy sampler, seed, conversation template, 512-token context, one slot, two target and two draft threads in each native server. Serve the base model without specialist adapters. Freeze the three requests in `panel.json` before starting a model. Run one two-token warm-up then the listed cases in order, with the HTTP prompt cache disabled. Use isolated fresh server processes in this fixed order.

1. Ordinary greedy T80.
2. Bonsai-2 4B PQ2 as a classic draft model, five proposals, minimum one, no probability cutoff. Keep any native load, translation or decoding failure.
3. Original Bonsai 1.7B PQ2 as a classic draft using identical parameters.
4. Native prompt lookup using exact three-token matches and at most five proposals.
5. Ordinary greedy T80 again to measure baseline drift.

Compare actual emitted target token IDs and user-visible content against the first ordinary arm, plus number of matching finishes. Inspect completeness against backend output counts. Measure per-request HTTP wall time, native process CPU seconds and server-reported decoded token counts and milliseconds. Report aggregate decode tokens/second, end-to-end wall time excluding server startup and warm-up, accepted/proposed tokens and both ordinary baselines. Timing ratios are meaningful only alongside equivalence and measurement drift. A fallback draft is a different experiment from a tiny neural draft. A matching short greedy response does not establish losslessness for all inputs or stochastic sampling. A 36-token cap can truncate delivery. No prompt or parameter tuning on outcomes. This is a microbenchmark, not a task-quality evaluation.

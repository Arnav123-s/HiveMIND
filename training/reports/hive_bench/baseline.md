# Hive bench: baseline

The hive at commit c8eab8a: this round's first fixes (planning, writer format, browser error pages, order cells), before
the calculator, writer-only tasks, triage, the browser's new edit and the fixes made from this run's failures.
Development tasks only (the held-out set was not run). Timing: `lookup` and `units` ran while another model job
competed for the CPU, so their times are inflated; the pass/fail results are not affected.

7/16 tasks pass; 124 min in all.

| task | kind | pass | time | model time | model calls | cell calls | plan | check |
|---|---|---|---|---|---|---|---|---|
| lookup | facts from a source | ✅ | 1460 s | 1415.7 s | 13 | 2 | researcher → writer | 2 sentences, 2 lines  |
| arxiv | list from a source | ❌ | 416 s | 408.0 s | 15 | 2 | researcher → writer | 3 items and an arXiv source  |
| chart | numbers + chart | ✅ | 710 s | 696.9 s | 20 | 2 | researcher → coder → writer | chart: yes, names the most downloaded (Qwen/Qwen3-1.7B): True  |
| quotes | operate a website | ❌ | 1219 s | 1194.5 s | 45 | 6 | browser → browser → writer | 1/3 of the first three quotes  |
| csv | scrape to a file | ❌ | 709 s | 688.3 s | 24 | 4 | researcher → coder → writer | CSV has 0/3 of the cheapest prices ['10.69', '11.84', '12.29']  |
| percent | arithmetic | ✅ | 135 s | 122.0 s | 9 | 2 | coder → writer | 1 sentences, 5 lines  |
| days | dates | ❌ | 271 s | 257.8 s | 17 | 5 | researcher → coder → writer | missing ['45']; 1 sentences, 9 lines  |
| units | unit conversion | ❌ | 1124 s | 1084.8 s | 33 | 12 | researcher → coder → writer | missing ['22.2']; 1 sentences, 1 lines  |
| translate | translate given text | ❌ | 85 s | 66.2 s | 6 | 2 | writer | missing ['vendredi']; 1 sentences, 1 lines  |
| summary | summarise given text | ❌ | 107 s | 96.7 s | 6 | 4 | researcher → writer | missing ['bridge', 'eight months or 8 months or 4.2']; 1 sentences, 1 lines  |
| grammar | fix given text | ✅ | 85 s | 78.2 s | 8 | 4 | writer | 1 sentences, 1 lines  |
| email | draft | ✅ | 87 s | 61.0 s | 4 | 2 | writer | 3 sentences, 10 lines  |
| fib | write and run code | ✅ | 265 s | 256.8 s | 16 | 3 | coder → coder → writer | 3 sentences, 13 lines  |
| bugfix | fix code | ✅ | 298 s | 288.5 s | 14 | 3 | researcher → coder → writer | 5 sentences, 10 lines  |
| explain | explain from knowledge | ❌ | 216 s | 206.2 s | 11 | 2 | researcher → writer | missing ['expert', 'router or routing or gate or gating']; 1 sentences, 1 lines  |
| sales | reason over given data | ❌ | 224 s | 216.3 s | 9 | 3 | researcher → writer | missing ['117', 'Mar or March']; 1 sentences, 5 lines  |

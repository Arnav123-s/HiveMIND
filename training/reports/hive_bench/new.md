# Hive bench: new

9/16 tasks pass; 91 min in all.

| task | kind | pass | time | model time | model calls | cell calls | plan | check |
|---|---|---|---|---|---|---|---|---|
| lookup | facts from a source | ✅ | 548 s | 540.6 s | 16 | 3 | researcher → writer | 2 sentences, 2 lines  |
| arxiv | list from a source | ✅ | 401 s | 392.6 s | 14 | 4 | researcher → writer | 3 items and an arXiv source  |
| chart | numbers + chart | ✅ | 730 s | 715.5 s | 22 | 4 | researcher → coder → writer | chart: yes, names the most downloaded (Qwen/Qwen3-1.7B): True  |
| quotes | operate a website | ❌ | 689 s | 674.7 s | 26 | 4 | browser → writer | 0/3 of the first three quotes  |
| csv | scrape to a file | ❌ | 1784 s | 1771.3 s | 19 | 7 | coder → writer | no CSV made  |
| percent | arithmetic | ✅ | 44 s | 37.0 s | 4 | 3 | calculator → writer | 1 sentences, 5 lines  |
| days | dates | ✅ | 61 s | 54.2 s | 4 | 3 | calculator → writer | 1 sentences, 6 lines  |
| units | unit conversion | ✅ | 55 s | 48.1 s | 4 | 3 | calculator → writer | 1 sentences, 5 lines  |
| translate | translate given text | ✅ | 30 s | 23.8 s | 2 | 3 | writer | 2 sentences, 3 lines  |
| summary | summarise given text | ✅ | 40 s | 34.3 s | 2 | 3 | writer | 1 sentences, 1 lines  |
| grammar | fix given text | ❌ | 50 s | 43.9 s | 2 | 3 | writer | 4 sentences, 4 lines  |
| email | draft | ❌ | 46 s | 40.0 s | 2 | 3 | writer | 7 sentences, 13 lines  |
| fib | write and run code | ❌ | 292 s | 270.0 s | 15 | 4 | coder → calculator → writer | missing ['832040']; 2 sentences, 12 lines  |
| bugfix | fix code | ❌ | 311 s | 300.3 s | 17 | 7 | coder → writer | missing ['30']; 2 sentences, 7 lines  |
| explain | explain from knowledge | ❌ | 293 s | 284.2 s | 17 | 4 | researcher → writer | missing ['router or routing or gate or gating']; 3 sentences, 1 lines  |
| sales | reason over given data | ✅ | 84 s | 76.6 s | 4 | 3 | calculator → writer | 2 sentences, 1 lines  |

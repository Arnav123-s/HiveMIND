# Hive bench: normal_after

15/16 tasks pass; 76 min in all.

| task | kind | pass | time | model time | model calls | cell calls | plan | check |
|---|---|---|---|---|---|---|---|---|
| lookup | facts from a source | ✅ | 412 s | 404.3 s | 19 | 3 | researcher → writer | 1 sentences, 1 lines  |
| arxiv | list from a source | ❌ | 288 s | 281.0 s | 18 | 4 | researcher → writer | 2 arXiv papers listed in the answer  |
| chart | numbers + chart | ✅ | 1601 s | 1567.9 s | 28 | 3 | browser → coder → writer | chart: yes, names the most downloaded (Qwen/Qwen3-1.7B): True  |
| quotes | operate a website | ✅ | 249 s | 238.1 s | 10 | 3 | browser → writer | 3/3 of the first three quotes  |
| csv | scrape to a file | ✅ | 337 s | 324.8 s | 10 | 3 | coder → writer | CSV has 3/3 of the cheapest prices ['10.69', '11.84', '12.29']  |
| percent | arithmetic | ✅ | 46 s | 40.0 s | 4 | 3 | calculator → writer | 1 sentences, 4 lines  |
| days | dates | ✅ | 410 s | 403.8 s | 8 | 3 | calculator → writer | 1 sentences, 7 lines  |
| units | unit conversion | ✅ | 55 s | 48.1 s | 5 | 3 | calculator → writer | 1 sentences, 4 lines  |
| translate | translate given text | ✅ | 26 s | 19.5 s | 2 | 3 | writer | 2 sentences, 1 lines  |
| summary | summarise given text | ✅ | 65 s | 59.2 s | 4 | 4 | writer | 1 sentences, 1 lines  |
| grammar | fix given text | ✅ | 29 s | 23.1 s | 2 | 3 | writer | 1 sentences, 1 lines  |
| email | draft | ✅ | 39 s | 33.1 s | 3 | 3 | writer | 3 sentences, 4 lines  |
| fib | write and run code | ✅ | 144 s | 137.4 s | 7 | 4 | coder → writer | 3 sentences, 21 lines  |
| bugfix | fix code | ✅ | 297 s | 288.6 s | 16 | 6 | researcher → coder → calculator → writer | 9 sentences, 29 lines  |
| explain | explain from knowledge | ✅ | 468 s | 456.5 s | 16 | 3 | researcher → writer | 3 sentences, 1 lines  |
| sales | reason over given data | ✅ | 71 s | 64.5 s | 4 | 2 | calculator → writer | 1 sentences, 9 lines  |

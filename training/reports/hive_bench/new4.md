# Hive bench: new4

15/16 tasks pass; 78 min in all.

| task | kind | pass | time | model time | model calls | cell calls | plan | check |
|---|---|---|---|---|---|---|---|---|
| lookup | facts from a source | ✅ | 585 s | 576.4 s | 13 | 3 | researcher → writer | 2 sentences, 2 lines  |
| arxiv | list from a source | ✅ | 462 s | 432.4 s | 16 | 3 | researcher → writer | 3 mixture-of-experts papers with their dates  |
| chart | numbers + chart | ✅ | 924 s | 912.0 s | 19 | 3 | researcher → coder → writer | chart: yes, names the most downloaded (Qwen/Qwen3-1.7B): True  |
| quotes | operate a website | ✅ | 148 s | 129.7 s | 8 | 3 | browser → writer | 3/3 of the first three quotes  |
| csv | scrape to a file | ❌ | 803 s | 753.9 s | 12 | 5 | coder → writer | CSV has 0/3 of the cheapest prices ['10.69', '11.84', '12.29']  |
| percent | arithmetic | ✅ | 40 s | 32.2 s | 4 | 3 | calculator → writer | 1 sentences, 5 lines  |
| days | dates | ✅ | 413 s | 404.0 s | 8 | 3 | calculator → writer | 1 sentences, 7 lines  |
| units | unit conversion | ✅ | 37 s | 30.2 s | 4 | 3 | calculator → writer | 1 sentences, 4 lines  |
| translate | translate given text | ✅ | 23 s | 16.6 s | 2 | 3 | writer | 2 sentences, 1 lines  |
| summary | summarise given text | ✅ | 61 s | 54.8 s | 4 | 3 | writer | 1 sentences, 1 lines  |
| grammar | fix given text | ✅ | 28 s | 21.2 s | 2 | 3 | writer | 1 sentences, 1 lines  |
| email | draft | ✅ | 33 s | 26.0 s | 2 | 3 | writer | 3 sentences, 4 lines  |
| fib | write and run code | ✅ | 182 s | 174.5 s | 11 | 3 | coder → calculator → writer | 1 sentences, 11 lines  |
| bugfix | fix code | ✅ | 352 s | 342.3 s | 18 | 5 | researcher → coder → writer | 2 sentences, 8 lines  |
| explain | explain from knowledge | ✅ | 435 s | 423.6 s | 13 | 4 | researcher → writer | 3 sentences, 1 lines  |
| sales | reason over given data | ✅ | 125 s | 118.6 s | 8 | 3 | calculator → calculator → writer | 1 sentences, 6 lines  |

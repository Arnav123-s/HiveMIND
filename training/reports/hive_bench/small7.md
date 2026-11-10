# Hive bench: small7

11/16 tasks pass; 69 min in all.

| task | kind | pass | time | model time | model calls | cell calls | plan | check |
|---|---|---|---|---|---|---|---|---|
| lookup | facts from a source | ❌ | 637 s | 627.4 s | 54 | 6 | researcher → writer | missing ['apache']; 2 sentences, 1 lines  |
| arxiv | list from a source | ❌ | 274 s | 264.6 s | 25 | 6 | researcher → writer | 0 arXiv papers listed in the answer  |
| chart | numbers + chart | ❌ | 1122 s | 1093.5 s | 46 | 10 | researcher → coder → writer | chart: yes, names the most downloaded (Qwen/Qwen3-1.7B): False  |
| quotes | operate a website | ✅ | 180 s | 166.3 s | 8 | 3 | browser → writer | 3/3 of the first three quotes  |
| csv | scrape to a file | ❌ | 310 s | 294.9 s | 9 | 5 | coder → writer | CSV has 2/3 of the cheapest prices ['10.69', '11.84', '12.29']  |
| percent | arithmetic | ✅ | 47 s | 40.8 s | 4 | 3 | calculator → writer | 1 sentences, 4 lines  |
| days | dates | ✅ | 158 s | 152.0 s | 4 | 3 | calculator → writer | 1 sentences, 9 lines  |
| units | unit conversion | ✅ | 48 s | 41.8 s | 5 | 3 | calculator → writer | 1 sentences, 4 lines  |
| translate | translate given text | ✅ | 18 s | 11.6 s | 2 | 3 | writer | 1 sentences, 1 lines  |
| summary | summarise given text | ✅ | 55 s | 48.6 s | 4 | 4 | writer | 1 sentences, 1 lines  |
| grammar | fix given text | ✅ | 19 s | 12.6 s | 2 | 3 | writer | 1 sentences, 1 lines  |
| email | draft | ✅ | 72 s | 66.4 s | 8 | 3 | writer | 3 sentences, 4 lines  |
| fib | write and run code | ❌ | 210 s | 199.7 s | 21 | 6 | coder → writer | missing ['832040']; 2 sentences, 11 lines  |
| bugfix | fix code | ✅ | 94 s | 87.2 s | 9 | 4 | coder → writer | 3 sentences, 2 lines  |
| explain | explain from knowledge | ✅ | 811 s | 798.0 s | 39 | 7 | researcher → writer | 3 sentences, 1 lines  |
| sales | reason over given data | ✅ | 57 s | 51.1 s | 4 | 2 | calculator → writer | 1 sentences, 9 lines  |

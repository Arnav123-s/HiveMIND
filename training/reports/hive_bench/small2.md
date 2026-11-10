# Hive bench: small2

2/7 tasks pass; 66 min in all.

| task | kind | pass | time | model time | model calls | cell calls | plan | check |
|---|---|---|---|---|---|---|---|---|
| arxiv | list from a source | ❌ | 714 s | 697.4 s | 38 | 7 | researcher → writer | 0 arXiv papers listed in the answer  |
| chart | numbers + chart | ❌ | 847 s | 824.2 s | 45 | 8 | researcher → coder → writer | chart: no, names the most downloaded (Qwen/Qwen3-1.7B): True  |
| csv | scrape to a file | ❌ | 145 s | 135.2 s | 8 | 3 | coder → writer | CSV has 0/3 of the cheapest prices ['10.69', '11.84', '12.29']  |
| summary | summarise given text | ✅ | 56 s | 49.3 s | 4 | 4 | writer | 1 sentences, 1 lines  |
| fib | write and run code | ❌ | 607 s | 593.5 s | 22 | 7 | researcher → writer | missing ['832040']; 2 sentences, 1 lines  |
| bugfix | fix code | ✅ | 743 s | 729.3 s | 31 | 9 | researcher → writer | 2 sentences, 2 lines  |
| sales | reason over given data | ❌ | 831 s | 815.5 s | 33 | 7 | calculator → writer | missing ['117', 'Mar or March']; 0 sentences, 0 lines  |

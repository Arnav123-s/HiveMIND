# Hive bench: new2

12/16 tasks pass; 63 min in all.

| task | kind | pass | time | model time | model calls | cell calls | plan | check |
|---|---|---|---|---|---|---|---|---|
| lookup | facts from a source | ✅ | 528 s | 520.0 s | 16 | 3 | researcher → writer | 2 sentences, 2 lines  |
| arxiv | list from a source | ❌ | 363 s | 355.3 s | 18 | 3 | researcher → writer | 2 arXiv papers listed in the answer  |
| chart | numbers + chart | ✅ | 711 s | 701.6 s | 18 | 3 | researcher → coder → writer | chart: yes, names the most downloaded (Qwen/Qwen3-1.7B): True  |
| quotes | operate a website | ❌ | 228 s | 216.6 s | 6 | 4 | browser → writer | 0/3 of the first three quotes exit 1: ImportError: cannot import name 'LEARNED' from 'team.cells.skills' (/home/user/hivemind/team/cells/skills.py) |
| csv | scrape to a file | ❌ | 294 s | 285.4 s | 7 | 3 | coder → writer | CSV has 2/3 of the cheapest prices ['10.69', '11.84', '12.29']  |
| percent | arithmetic | ✅ | 49 s | 42.3 s | 4 | 3 | calculator → writer | 1 sentences, 5 lines  |
| days | dates | ✅ | 173 s | 166.9 s | 8 | 3 | calculator → writer | 1 sentences, 3 lines  |
| units | unit conversion | ❌ | 78 s | 71.7 s | 8 | 3 | calculator → writer | missing ['22.2']; 1 sentences, 1 lines  |
| translate | translate given text | ✅ | 23 s | 16.9 s | 2 | 3 | writer | 1 sentences, 1 lines  |
| summary | summarise given text | ✅ | 27 s | 21.3 s | 2 | 3 | writer | 1 sentences, 1 lines  |
| grammar | fix given text | ✅ | 26 s | 19.2 s | 2 | 3 | writer | 1 sentences, 1 lines  |
| email | draft | ✅ | 29 s | 23.3 s | 2 | 3 | writer | 2 sentences, 1 lines  |
| fib | write and run code | ✅ | 182 s | 174.9 s | 11 | 3 | coder → calculator → writer | 1 sentences, 12 lines  |
| bugfix | fix code | ✅ | 209 s | 199.5 s | 11 | 3 | coder → writer | 3 sentences, 13 lines  |
| explain | explain from knowledge | ✅ | 775 s | 752.1 s | 20 | 3 | researcher → writer | 3 sentences, 1 lines  |
| sales | reason over given data | ✅ | 63 s | 56.7 s | 4 | 3 | calculator → writer | 2 sentences, 1 lines  |

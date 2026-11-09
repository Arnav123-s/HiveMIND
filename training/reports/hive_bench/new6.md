# Hive bench: new6

15/16 tasks pass; 64 min in all.

| task | kind | pass | time | model time | model calls | cell calls | plan | check |
|---|---|---|---|---|---|---|---|---|
| lookup | facts from a source | ✅ | 292 s | 285.1 s | 13 | 3 | researcher → writer | 2 sentences, 2 lines  |
| arxiv | list from a source | ✅ | 528 s | 520.2 s | 19 | 4 | researcher → writer | 3 mixture-of-experts papers with their dates  |
| chart | numbers + chart | ✅ | 592 s | 582.0 s | 23 | 3 | researcher → coder → writer | chart: yes, names the most downloaded (Qwen/Qwen3-1.7B): True  |
| quotes | operate a website | ✅ | 365 s | 354.6 s | 12 | 3 | browser → writer | 3/3 of the first three quotes  |
| csv | scrape to a file | ❌ | 252 s | 242.8 s | 9 | 3 | coder → writer | CSV has 2/3 of the cheapest prices ['10.69', '11.84', '12.29']  |
| percent | arithmetic | ✅ | 52 s | 44.9 s | 4 | 3 | calculator → writer | 1 sentences, 4 lines  |
| days | dates | ✅ | 209 s | 191.8 s | 4 | 3 | calculator → writer | 11 sentences, 27 lines  |
| units | unit conversion | ✅ | 59 s | 52.5 s | 4 | 3 | calculator → writer | 1 sentences, 4 lines  |
| translate | translate given text | ✅ | 26 s | 20.0 s | 2 | 3 | writer | 2 sentences, 1 lines  |
| summary | summarise given text | ✅ | 66 s | 59.6 s | 4 | 3 | writer | 1 sentences, 1 lines  |
| grammar | fix given text | ✅ | 29 s | 22.6 s | 2 | 3 | writer | 1 sentences, 1 lines  |
| email | draft | ✅ | 35 s | 28.3 s | 2 | 3 | writer | 3 sentences, 4 lines  |
| fib | write and run code | ✅ | 202 s | 195.2 s | 11 | 3 | coder → calculator → writer | 1 sentences, 11 lines  |
| bugfix | fix code | ✅ | 349 s | 341.1 s | 18 | 5 | researcher → coder → writer | 4 sentences, 9 lines  |
| explain | explain from knowledge | ✅ | 470 s | 459.0 s | 16 | 3 | researcher → writer | 3 sentences, 1 lines  |
| sales | reason over given data | ✅ | 306 s | 295.2 s | 18 | 6 | calculator → writer | 3 sentences, 2 lines  |

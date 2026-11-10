# Hive bench: new3

7/9 tasks pass; 42 min in all.

| task | kind | pass | time | model time | model calls | cell calls | plan | check |
|---|---|---|---|---|---|---|---|---|
| arxiv | list from a source | ✅ | 318 s | 310.1 s | 16 | 3 | researcher → writer | 3 mixture-of-experts papers with their dates  |
| quotes | operate a website | ✅ | 134 s | 122.5 s | 8 | 3 | browser → writer | 3/3 of the first three quotes  |
| csv | scrape to a file | ❌ | 618 s | 606.0 s | 11 | 3 | coder → writer | CSV has 2/3 of the cheapest prices ['10.69', '11.84', '12.29']  |
| percent | arithmetic | ✅ | 41 s | 34.0 s | 4 | 3 | calculator → writer | 1 sentences, 4 lines  |
| units | unit conversion | ✅ | 127 s | 119.7 s | 8 | 3 | calculator → writer | 1 sentences, 4 lines  |
| fib | write and run code | ✅ | 192 s | 183.9 s | 11 | 3 | coder → calculator → writer | 2 sentences, 14 lines  |
| bugfix | fix code | ✅ | 355 s | 345.9 s | 18 | 5 | researcher → coder → writer | 2 sentences, 8 lines  |
| explain | explain from knowledge | ✅ | 529 s | 517.7 s | 16 | 3 | researcher → writer | 3 sentences, 1 lines  |
| sales | reason over given data | ❌ | 212 s | 203.9 s | 16 | 8 | researcher → researcher → writer | missing ['117', 'Mar or March']; 0 sentences, 0 lines  |

# Hive bench: normal_reg2

3/3 tasks pass; 15 min in all.

| task | kind | pass | time | model time | model calls | cell calls | plan | check |
|---|---|---|---|---|---|---|---|---|
| lookup | facts from a source | ✅ | 381 s | 373.2 s | 19 | 3 | researcher → writer | 1 sentences, 1 lines  |
| arxiv | list from a source | ✅ | 265 s | 256.9 s | 16 | 4 | researcher → writer | 3 mixture-of-experts papers with their dates  |
| fib | write and run code | ✅ | 280 s | 273.2 s | 7 | 4 | coder → writer | 3 sentences, 21 lines  |

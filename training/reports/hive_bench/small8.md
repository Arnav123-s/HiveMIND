# Hive bench: small8

2/3 tasks pass; 23 min in all.

| task | kind | pass | time | model time | model calls | cell calls | plan | check |
|---|---|---|---|---|---|---|---|---|
| lookup | facts from a source | ✅ | 341 s | 333.2 s | 26 | 3 | researcher → writer | 1 sentences, 1 lines  |
| arxiv | list from a source | ❌ | 363 s | 353.4 s | 30 | 6 | researcher → writer | 0 arXiv papers listed in the answer  |
| fib | write and run code | ✅ | 673 s | 657.9 s | 38 | 7 | coder → writer | 2 sentences, 12 lines  |

# Hive bench: small9

1/3 tasks pass; 22 min in all.

| task | kind | pass | time | model time | model calls | cell calls | plan | check |
|---|---|---|---|---|---|---|---|---|
| lookup | facts from a source | ✅ | 324 s | 316.5 s | 26 | 3 | researcher → writer | 1 sentences, 1 lines  |
| arxiv | list from a source | ❌ | 325 s | 152.1 s | 11 | 6 | researcher → writer | 0 arXiv papers listed in the answer  |
| chart | numbers + chart | ❌ | 682 s | 667.3 s | 46 | 9 | researcher → coder → writer | chart: no, names the most downloaded (Qwen/Qwen3-1.7B): True  |

# Hive bench: normal_reg

3/3 tasks pass; 19 min in all.

| task | kind | pass | time | model time | model calls | cell calls | plan | check |
|---|---|---|---|---|---|---|---|---|
| lookup | facts from a source | ✅ | 423 s | 414.6 s | 19 | 3 | researcher → writer | 1 sentences, 1 lines  |
| arxiv | list from a source | ✅ | 263 s | 256.3 s | 16 | 4 | researcher → writer | 3 mixture-of-experts papers with their dates  |
| explain | explain from knowledge | ✅ | 454 s | 443.0 s | 16 | 3 | researcher → writer | 3 sentences, 1 lines  |

# Hive bench: small10

1/3 tasks pass; 20 min in all.

| task | kind | pass | time | model time | model calls | cell calls | plan | check |
|---|---|---|---|---|---|---|---|---|
| arxiv | list from a source | ❌ | 389 s | 380.5 s | 30 | 6 | researcher → writer | 0 arXiv papers listed in the answer  |
| chart | numbers + chart | ✅ | 442 s | 430.8 s | 22 | 7 | researcher → coder → writer | chart: yes, names the most downloaded (Qwen/Qwen3-1.7B): True  |
| csv | scrape to a file | ❌ | 355 s | 337.9 s | 10 | 5 | coder → writer | CSV has 2/3 of the cheapest prices ['10.69', '11.84', '12.29']  |

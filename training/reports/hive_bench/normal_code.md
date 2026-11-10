# Hive bench: normal_code

3/3 tasks pass; 42 min in all.

| task | kind | pass | time | model time | model calls | cell calls | plan | check |
|---|---|---|---|---|---|---|---|---|
| chart | numbers + chart | ✅ | 1861 s | 1826.8 s | 33 | 3 | browser → coder → writer | chart: yes, names the most downloaded (Qwen/Qwen3-1.7B): True  |
| csv | scrape to a file | ✅ | 499 s | 486.3 s | 12 | 3 | coder → writer | CSV has 3/3 of the cheapest prices ['10.69', '11.84', '12.29']  |
| fib | write and run code | ✅ | 156 s | 147.9 s | 7 | 4 | coder → writer | 3 sentences, 21 lines  |

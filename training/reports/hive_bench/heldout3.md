# Hive bench: heldout3

13/16 tasks pass; 35 min in all.

| task | kind | pass | time | model time | model calls | cell calls | plan | check |
|---|---|---|---|---|---|---|---|---|
| h3_licence | facts from a source | ✅ | 262 s | 252.1 s | 13 | 3 | researcher → writer | licence mit in the answer  |
| h3_pypi | facts from a source | ✅ | 120 s | 100.3 s | 9 | 3 | researcher → writer | latest tqdm 4.70.1 in the answer  |
| h3_chart | numbers + chart | ✅ | 412 s | 401.4 s | 18 | 3 | researcher → coder → writer | chart: True, names t5-small: True  |
| h3_born | operate a website | ❌ | 45 s | 29.6 s | 2 | 4 | browser → writer | born March 04, 1965: in the report False  |
| h3_business_csv | scrape to a file | ✅ | 490 s | 471.9 s | 20 | 3 | browser → browser → coder → writer | CSV has 12/12 prices of the Business page  |
| h3_rise | arithmetic | ✅ | 56 s | 49.4 s | 4 | 3 | calculator → writer | 2 sentences, 4 lines  |
| h3_days | dates | ✅ | 76 s | 69.6 s | 4 | 3 | calculator → writer | 1 sentences, 8 lines  |
| h3_temp | unit conversion | ✅ | 44 s | 37.1 s | 4 | 3 | calculator → writer | 1 sentences, 4 lines  |
| h3_italian | translate given text | ✅ | 24 s | 18.3 s | 2 | 3 | writer | bakery, seven and Sunday in Italian: True  |
| h3_park | summarise given text | ✅ | 55 s | 49.0 s | 4 | 3 | writer | 1 sentences, 1 lines  |
| h3_formal | fix given text | ❌ | 39 s | 33.1 s | 2 | 3 | writer | missing ['please or could or would']; 1 sentences, 1 lines  |
| h3_colleague | draft | ✅ | 104 s | 98.0 s | 6 | 3 | writer | 2 sentences, 2 lines  |
| h3_vowels | write and run code | ✅ | 92 s | 85.6 s | 7 | 3 | coder → writer | 2 sentences, 8 lines  |
| h3_average | fix code | ✅ | 136 s | 129.9 s | 9 | 3 | coder → writer | 5 sentences, 20 lines  |
| h3_queue | explain from knowledge | ❌ | 63 s | 57.1 s | 4 | 3 | writer | 4 sentences, 2 lines  |
| h3_water | reason over given data | ✅ | 106 s | 99.7 s | 4 | 2 | calculator → writer | 3 sentences, 11 lines  |

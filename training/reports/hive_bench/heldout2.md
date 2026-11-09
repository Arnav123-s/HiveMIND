# Hive bench: heldout2

11/16 tasks pass; 71 min in all.

| task | kind | pass | time | model time | model calls | cell calls | plan | check |
|---|---|---|---|---|---|---|---|---|
| h2_licence | facts from a source | ✅ | 241 s | 233.8 s | 13 | 3 | researcher → writer | licence apache-2.0 (apache + 2.0) in the answer  |
| h2_pypi | facts from a source | ✅ | 102 s | 95.7 s | 10 | 3 | researcher → writer | latest numpy 2.5.4 in the answer  |
| h2_chart | numbers + chart | ✅ | 585 s | 575.9 s | 22 | 2 | researcher → coder → writer | chart: True, names gpt2: True  |
| h2_born | operate a website | ❌ | 129 s | 116.0 s | 8 | 3 | browser → writer | born February 11, 1847: in the report False  |
| h2_food_csv | scrape to a file | ❌ | 921 s | 869.5 s | 13 | 7 | coder → writer | no CSV made  |
| h2_tip | arithmetic | ❌ | 56 s | 48.8 s | 4 | 3 | calculator → writer | missing ['161']; 1 sentences, 3 lines  |
| h2_days | dates | ✅ | 236 s | 226.3 s | 8 | 3 | calculator → writer | 1 sentences, 7 lines  |
| h2_kg | unit conversion | ✅ | 54 s | 47.2 s | 4 | 3 | calculator → writer | 1 sentences, 5 lines  |
| h2_german | translate given text | ❌ | 24 s | 18.2 s | 2 | 3 | writer | missing ['neun']; 2 sentences, 1 lines  |
| h2_garden | summarise given text | ✅ | 65 s | 58.4 s | 4 | 3 | writer | 1 sentences, 1 lines  |
| h2_spelling | fix given text | ✅ | 31 s | 24.3 s | 3 | 3 | writer | 1 sentences, 1 lines  |
| h2_landlord | draft | ✅ | 36 s | 29.7 s | 2 | 3 | writer | 3 sentences, 2 lines  |
| h2_factorial | write and run code | ✅ | 89 s | 82.8 s | 7 | 3 | coder → writer | 2 sentences, 17 lines  |
| h2_evensum | fix code | ✅ | 222 s | 215.1 s | 13 | 3 | coder → writer | 5 sentences, 3 lines  |
| h2_bsearch | explain from knowledge | ✅ | 125 s | 119.5 s | 9 | 3 | coder → writer | 2 sentences, 1 lines  |
| h2_rain | reason over given data | ❌ | 1359 s | 1131.5 s | 34 | 12 | researcher → coder → researcher → writer | missing ['Apr', '64.25 or 64.3']; 0 sentences, 0 lines  |

# Hive bench: heldout

9/16 tasks pass; 38 min in all.

| task | kind | pass | time | model time | model calls | cell calls | plan | check |
|---|---|---|---|---|---|---|---|---|
| ho_lookup | facts from a source | ✅ | 318 s | 310.1 s | 14 | 4 | researcher → writer | licence apache and 1.485B parameters in the report: True  |
| ho_pypi | facts from a source | ✅ | 80 s | 73.2 s | 9 | 3 | researcher → writer | latest requests 2.34.2 in the answer  |
| ho_chart | numbers + chart | ❌ | 383 s | 373.5 s | 18 | 3 | researcher → coder → writer | chart: False, names bert-base-uncased  |
| ho_book | operate a website | ✅ | 170 s | 154.2 s | 9 | 3 | browser → writer | UPC 6be3beb0793a53e7 of the first Philosophy book in the report: True  |
| ho_quotes_csv | scrape to a file | ❌ | 233 s | 223.6 s | 8 | 3 | coder → writer | CSV has 0/8 authors of page 1  |
| ho_discount | arithmetic | ✅ | 47 s | 40.3 s | 4 | 3 | calculator → writer | 2 sentences, 5 lines  |
| ho_weekday | dates | ❌ | 48 s | 41.2 s | 4 | 3 | calculator → writer | missing ['Sunday']; 1 sentences, 2 lines  |
| ho_miles | unit conversion | ❌ | 40 s | 34.1 s | 4 | 3 | calculator → writer | missing ['42.2']; 1 sentences, 4 lines  |
| ho_spanish | translate given text | ❌ | 22 s | 15.7 s | 2 | 3 | writer | missing ['biblioteca', 'ocho']; 1 sentences, 1 lines  |
| ho_office | summarise given text | ✅ | 72 s | 65.5 s | 4 | 3 | writer | 1 sentences, 1 lines  |
| ho_polite | fix given text | ❌ | 31 s | 25.1 s | 2 | 3 | writer | missing ['please']; 1 sentences, 1 lines  |
| ho_notice | draft | ✅ | 28 s | 20.9 s | 2 | 3 | writer | 3 sentences, 1 lines  |
| ho_palindrome | write and run code | ✅ | 119 s | 111.6 s | 7 | 3 | coder → writer | 1 sentences, 6 lines  |
| ho_bugmax | fix code | ✅ | 150 s | 142.1 s | 11 | 3 | coder → writer | 3 sentences, 7 lines  |
| ho_explain | explain from knowledge | ❌ | 481 s | 467.8 s | 14 | 9 | researcher → writer | missing ['key', 'hash']; 2 sentences, 1 lines  |
| ho_scores | reason over given data | ✅ | 52 s | 44.9 s | 4 | 3 | calculator → writer | 1 sentences, 8 lines  |

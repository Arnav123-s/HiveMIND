# Hive bench: heldout_after

13/16 tasks pass; 70 min in all.

| task | kind | pass | time | model time | model calls | cell calls | plan | check |
|---|---|---|---|---|---|---|---|---|
| ho_lookup | facts from a source | ✅ | 327 s | 319.4 s | 14 | 4 | researcher → writer | licence apache and 1.485B parameters in the report: True  |
| ho_pypi | facts from a source | ✅ | 82 s | 74.7 s | 9 | 3 | researcher → writer | latest requests 2.34.2 in the answer  |
| ho_chart | numbers + chart | ✅ | 400 s | 389.9 s | 18 | 3 | researcher → coder → writer | chart: True, names bert-base-uncased  |
| ho_book | operate a website | ✅ | 141 s | 125.4 s | 9 | 3 | browser → writer | UPC 6be3beb0793a53e7 of the first Philosophy book in the report: True  |
| ho_quotes_csv | scrape to a file | ❌ | 1148 s | 1126.0 s | 18 | 6 | coder → writer | CSV has 0/8 authors of page 1  |
| ho_discount | arithmetic | ✅ | 54 s | 46.1 s | 4 | 3 | calculator → writer | 2 sentences, 5 lines  |
| ho_weekday | dates | ❌ | 1056 s | 1031.7 s | 19 | 8 | calculator → writer | missing ['Sunday']; 2 sentences, 1 lines  |
| ho_miles | unit conversion | ✅ | 104 s | 97.2 s | 4 | 3 | calculator → writer | 1 sentences, 4 lines  |
| ho_spanish | translate given text | ✅ | 25 s | 18.2 s | 2 | 3 | writer | 2 sentences, 1 lines  |
| ho_office | summarise given text | ✅ | 67 s | 60.1 s | 4 | 3 | writer | 1 sentences, 1 lines  |
| ho_polite | fix given text | ❌ | 50 s | 42.5 s | 4 | 3 | writer | missing ['please']; 3 sentences, 3 lines  |
| ho_notice | draft | ✅ | 46 s | 39.9 s | 2 | 3 | writer | 3 sentences, 3 lines  |
| ho_palindrome | write and run code | ✅ | 185 s | 135.2 s | 7 | 3 | coder → writer | 1 sentences, 6 lines  |
| ho_bugmax | fix code | ✅ | 163 s | 156.0 s | 11 | 3 | coder → writer | 3 sentences, 7 lines  |
| ho_explain | explain from knowledge | ✅ | 282 s | 273.1 s | 14 | 3 | researcher → writer | 2 sentences, 1 lines  |
| ho_scores | reason over given data | ✅ | 44 s | 37.1 s | 4 | 3 | calculator → writer | 1 sentences, 1 lines  |

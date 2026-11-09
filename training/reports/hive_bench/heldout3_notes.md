# Held-out set 3: 13/16 on frozen code

Sixteen fresh tasks of the same kinds, written and contamination-checked before any run, run **once** on the frozen
copy at commit 0147aa4 (every fix of the day up to the translation routing). No check was changed after the run.

| held-out set | code | score |
|---|---|---|
| set 1 | 00e1555 (morning) | 9/16 |
| set 2 | d45bc04 (midday) | 11/16 (10/16 as first scored; one check corrected) |
| **set 3** | **0147aa4** | **13/16** |

Each set is new tasks the fixes before it had never seen, so the rise is generalisation, not tuning to the set.

| task | result | note |
|---|---|---|
| h3_licence, h3_pypi | pass | from the live Hugging Face and PyPI APIs |
| h3_chart | pass | the image saved; t5-small named as the more downloaded |
| h3_business_csv | pass | 12/12 prices: the first held-out "scrape to a file" task to pass in any set |
| h3_rise, h3_days, h3_temp | pass | 851, 74, 37.0 |
| h3_italian | pass | "La pasticceria apre alle sette di domenica.", written by the 4B (the measured translator) |
| h3_park, h3_colleague, h3_vowels, h3_average, h3_water | pass | |
| h3_born | **fail** | Khaled Hosseini is not on the first page of quotes.toscrape.com; the browser gave up there without following a link, and the values check (meant for answers) failed the page's lines on "10,000". Fixed after: no give-up while a next page is unread; the check skips page dumps (47613a2) |
| h3_formal | **fail** | "Send the report as soon as possible.": more formal, but his question became a command ("Could you please send ..." keeps the request) |
| h3_queue | **fail** | the right explanation (first in, first out), given twice: four sentences for two. Fixed after: repeated paragraphs dropped, the ordered sentence count checked in code (ead19bc) |

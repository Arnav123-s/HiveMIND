# Hive bench "new3": the changed development tasks on frozen code

Run from a frozen copy of the code at commit 00e1555 (with the cleaned cells), so no edit could reach it mid-run:
the 9 development tasks that fixes touched since "new2". **7/9 pass.** With the 7 tasks that passed in "new2" and
were not touched since, the development set stands at **14/16**.

| task | result | what it showed |
|---|---|---|
| arxiv | pass | three real mixture-of-experts papers with their dates (the stricter check asks arXiv) |
| quotes | pass | the right three quotes, checked line by line on the page |
| csv | fail | the coder now follows the listing's next links but built them by joining strings (.../index.html/page-2.html), so it read one page: 2 of the 3 cheapest. Fixed after the freeze (e9374b4: urljoin, and the reviewer checks it) |
| percent | pass | the first clean pass: the leaked prompt example is gone |
| units | pass | the leak had caused its failure |
| fib | pass | his definition travels with the step, his examples run as checks |
| bugfix | pass | the jury sees the program beside its output |
| explain | pass | from Wikipedia's article; its sources were credited to two search snippets (fixed after the freeze, b7573aa) |
| sales | fail | the retrained triage cell was unsure, the coordinator sent two researchers to search the web for given data, and the writer guessed the average. Fixed after the freeze (0699421: given data is computed on) |

The held-out set ran once, right after this, on the same frozen copy (heldout.md).

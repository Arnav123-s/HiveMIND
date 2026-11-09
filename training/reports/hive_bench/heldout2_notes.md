# Held-out set 2: 11/16 on frozen code (10/16 as first scored)

Sixteen fresh tasks of the same kinds as the development set, written and checked for contamination before any run
(training/contamination_check.py), run **once** on the frozen copy at commit d45bc04. Each is checked in code against
the live answer where there is one.

**As run: 10/16** (heldout2_asrun.md). One check was wrong, not the hive: h2_licence wanted the id form "apache-2.0"
and the answer said "Apache License 2.0", the same licence. The check was corrected to accept the licence by its name
(as the first held-out set's licence check did) and the saved runs were scored again: **11/16** (heldout2.md). No
other check was changed and no task was run again.

For comparison: the first held-out set scored 9/16 on the code of that time (frozen 00e1555).

| task | result | cause |
|---|---|---|
| h2_licence | pass (after the check fix) | "Apache License 2.0" from the model's own page |
| h2_pypi, h2_chart, h2_days, h2_kg, h2_garden, h2_spelling, h2_landlord, h2_factorial, h2_evensum | pass | |
| h2_bsearch | pass | the explanation was sent to the coder (the triage cell said code) and still came out right |
| h2_born | **fail** | the browser stopped on a tag page and answered "born on 1847-02-04" with evidence that holds no date ("by Thomas A. Edison (about)"); the jury passed it. He was born on 11 February 1847 |
| h2_food_csv | **fail** | the listing's next link was joined to the site's home page (404) and the 404 hint did not change the 7B coder's program; the task had asked for the first page only, and the preview told the coder to follow every next link |
| h2_tip | **fail** | the calculator printed 161.0 (right); the writer wrote $161.00 and the report's number check struck it, as the strings differed |
| h2_german | **fail** | "Der Zug fährt um 9 Uhr in der Morgens." (a grammar error by the 1.7B writer) |
| h2_rain | **fail** | the triage cell was unsure (plan 0.62); the coordinator sent researchers to search the web for the rainfall he gave and a coder to an invented URL; the data check skipped a plan with a coder in it |

## Fixed after this run (general, checked in code, tested; none changes the score above)

- A browser answer's dates, prices and numbers must be in the evidence it copied (6d2c7a2).
- On a 404 the hive finds where the link really leads and tells the coder; "the first page" means the first page only
  (c1441ea).
- A report's number counts by its value: $161.00 is 161.0 (1f32345).
- Handed-over data with a question goes to the calculator before the triage cell is asked; the data check covers coder
  steps (2e47b45).
- German: a translator specialist (a surgical edit of the 1.7B on professional translations, WMT24++) is being trained
  and is used only if it beats the writer and the 4B on 120 held-out sentences (training/translator.py).

Four of the six failures were the hive's own checks letting a wrong result through or striking a right one, not a
specialist unable to do its part. A third held-out set is needed to measure these fixes cleanly.

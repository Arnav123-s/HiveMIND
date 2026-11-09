# Held-out set: 9/16 on frozen code

The held-out tasks were written before any of the fixes they could reveal, and ran **once**, on the frozen copy at
commit 00e1555 (the same copy the "new3" development run used; heldout.md is its report). **9 of 16 pass.** On the
same code the development set stands at 14/16. The gap is the measurement: fixes made on development tasks carried
over to fresh tasks of the same kinds far less than the development score suggested. Two of the seven failures were
caused by my own edits on the development set (see miles and quotes below).

| task | result | why |
|---|---|---|
| ho_lookup | pass | licence and parameter count from the model's page |
| ho_pypi | pass | the latest version from PyPI's own API |
| ho_chart | **fail** | the coder drew the bar chart with plt.show(), which saves nothing; no image was made, and the jury passed the step on what the program printed |
| ho_book | pass | (the browser stood on the right page and gave up, because the UPC line was not in what it was shown; the jury got the page's lines and the writer found it) |
| ho_quotes_csv | **fail** | the preview showed the author in `<small class="author">`; the program looked for a span, crashed, and its fix wrote "Unknown" in all 10 rows. The fix hint for data errors had said "check for missing values before using them". Three jurors passed the CSV |
| ho_discount | pass | |
| ho_weekday | **fail** | the calculator printed `weekday()` = 6; the writer guessed "Saturday"; the weekday check struck that line, leaving the bare "6" |
| ho_miles | **fail** | "One decimal place" printed 42.16: the calculator prompt's example said `round(answer, 2)`, which I wrote when the bench values were purged from it |
| ho_spanish | **fail** | the writer handed the English sentence back; the critic ticked it done |
| ho_office | pass | |
| ho_polite | **fail** | the same: "Send me the file now." came back unchanged, ticked done |
| ho_notice | pass | |
| ho_palindrome | pass | |
| ho_bugmax | pass | |
| ho_explain | **fail** | the reader put every link of the Wikipedia article on its own line ("computer science , a"), so the researcher's exact quotes were never found; every item was then dropped for "not giving the two-sentence explanation" (a format order judged against a source line), and the step was rerouted to the coder, which wrote invalid Python |
| ho_scores | pass | the given scores were computed on (the "sales" fix carried over) |

## What changed after it (general fixes; none of them changes the score above)

- A program that draws a chart but saves no image is sent back with the savefig hint and never passes; a step that
  orders a file and got none fails; programs run with a non-window plotting backend.
- A CSV/TSV column holding one placeholder in every row is a broken file (the coder loop sends it back; the verifier
  fails it before any juror); the data hint and the coder prompt say to take each value from where the preview
  shows it, never a placeholder.
- The calculator prompt no longer shows 2 decimals; it says to round to exactly the places asked and to print names
  as names. The calculator checks the answer's form in code (decimal places, a weekday by name) and gets one fix.
- A wrong weekday next to a date is corrected from the calendar instead of struck.
- Work on his own text (translate, rewrite, fix, summarise, draft) has its own writer prompt; a report that repeats
  his text is marked not done in code, which sends it to the writer's fix and then the editor.
- The page reader keeps links inside their sentences (one line per block); quotes are matched on their words in
  order, without punctuation spacing or footnote marks.
- The browser's page view: "UPC." is looked for as "upc", and the most specific lines get the budget first.
- A one-word line of the instruction splitter joins the instruction it was cut from.

The held-out set was then run again on code with these fixes ("heldout_after"). That run is **not** a clean held-out
number: these tasks informed the fixes. A clean number needs new tasks the fixes have never seen.

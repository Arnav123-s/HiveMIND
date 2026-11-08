# Hive bench "new": notes

The development tasks, run on 2026-11-08 from commit 0c3bd5e: the code after the baseline's fixes, with the
calculator, writer-only tasks, triage on and the browser's new weight edit. **9/16 pass** under the checks of that
time; the baseline at c8eab8a passed 7/16.

The run itself took 91 minutes. Fixes made from its failures were committed while it ran, so its later tasks ran on
newer code than its first ones. A full re-run on the code with every fix is `new2`.

What each failure showed, and the general fix (the commit message has the details):

| task | what went wrong | fix |
|---|---|---|
| arxiv (counted as a pass) | `all:mixture of experts` matches any of the words: newest-first gave unrelated papers; the verifier rejected them, the step was dropped after 1 of 3 attempts, and the writer listed the rejected papers (one title invented) with today's date | phrase-then-words arXiv queries; a reroute with nobody to take it retries; nothing verified means no made-up answer; **the bench's arxiv check was too weak** and now checks each paper's topic and date on arXiv (this report fails it) |
| chart (pass) | the jury rejected the saved chart (it saw only the printed numbers), 3,905,849 was struck against a source's 3905849, the image linked to an API page | the jury sees saved files; numbers compared without thousands separators; image links show saved files only |
| quotes | the browser had the right three quotes, but its answer passed its 160-token limit and was re-asked with the same limit until it ran out of actions | a reply cut off inside its JSON is asked again with twice the room; browser limit 600 |
| csv | 12 runs of the coder used http:// (only HTTPS goes through this machine's proxy) and the same error each time; no preview of a site named without a scheme | named sites are previewed as https:// with the links the task names; the coder stops when a fix changes nothing; model-written code no longer sees tokens or keys |
| days (pass) | the critic added an instruction he never gave; the report's unasked table called 15 January 2026 a Monday | checklist = his instructions as written; weekday-date pairs checked against the calendar |
| grammar | 'the table' inside the sentence to correct made the writer add a table; 'give me only the corrected sentence' was not read | layout orders read from his words only; 'only the X' |
| email | 'two-sentence email' not read as a layout; a Details list and a table repeated the email | N-sentence orders cover drafts; a draft is only the draft |
| fib | the plan's calculator step lost his 'fib(1) = 1' and counted from 0 (514229); the coder's program printed nothing | his whole task travels with code and calculator steps; a silent program goes back to the coder |
| bugfix | the coder's fix was right (printed 30) but the jury saw only '30' and rejected it | the jury sees the program beside its output |
| explain | the researcher looked for a concept on Hugging Face and arXiv | concepts from Wikipedia's article |

Fixed after the run (data after a label is material): in `sales` the given data ('Jan 120, Feb 95, ...') became checklist lines, because 'Monthly sales:' has
no verb that marks handed-over material. They were ticked, so nothing failed, but they are noise in the report.

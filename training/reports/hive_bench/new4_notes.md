# Hive bench "new4": the whole development set again, after the held-out fixes

Run from a frozen copy at commit 2574473: the fixes for the held-out failures (saved charts, placeholder columns,
answer form, weekday correction, work on his own text, the block-aware page reader, prompts fitted to the window,
research questions kept off the shortcut). **15/16 pass**, against 14/16 in "new3". This run is the regression check:
those fixes touched the coder, calculator, writer, verifier and the reader every researcher uses, and nothing that
passed before broke.

| task | result | note |
|---|---|---|
| csv | fail | the program joined the listing's next link to the site's home page (/page-2.html, a 404); the retry carried the error and the coder's preview took the URL in it, so it lost the Mystery listing; its last attempt matched "Mystery" in titles across the whole catalogue and the reviewer passed it. Fixed after the freeze (4269152): a retry previews only his task's pages, a 404 has its own hint, the reviewer checks where items come from |
| days | pass | the writer's draft gave both dates the wrong weekday; the calendar check corrected them in the report (the new behaviour, listed under "Corrected") |
| explain, translate, summary, grammar, email | pass | the page reader and the prompt for work on his own text carried over |
| chart | pass | 924 s against 711 s in new2, same plan and no extra rounds: slower model calls while tests shared the CPU |

Fixes made after this freeze (item check without layout orders, OpenAlex, reroute guard, the csv fixes) are not in it.

# Hive bench "new6": the development set on the final frozen copy (0147aa4)

The same frozen copy as held-out set 3 (13/16). **15/16 pass.**

| task | result | note |
|---|---|---|
| csv | fail | the listing's next link joined to the home page; this time the fetch did not raise, so the program parsed a 404 page as an empty listing and finished with two of the three cheapest. Fixed after (233bcf1): every program reports its requests that came back as errors, and a run that read missing pages goes back to the coder with where the link really leads |
| days | pass, report junk | the right answer 45, then the 1.7B writer looped "Wait, this is not correct. Let's recalculate." Fixed after (fefdae1): self-talk lines and empty labels leave the report |
| translate | pass | written by the 4B, as measured |
| the other 13 | pass | |

Fixed after this freeze and not measured on whole tasks yet: the browser's give-up while a next page is unread, the
values check skipping page dumps, repeated paragraphs and the ordered sentence count, HTTP errors from programs, and
self-talk in reports (each has a test).

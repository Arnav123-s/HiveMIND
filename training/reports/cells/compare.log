# Cells: measured

Each cell = SmolLM2-135M (shared, frozen) + its own weight delta. Scores are on the TEST split (other words, frames, sites than training). Variant columns are the PyTorch test scores of each candidate edit; the winner is chosen on dev. `cell` = the winner served by llama.cpp. The five orders_* cells take the job only together, judged as the guard uses them (the organizer table below), so one of them can lose alone and still say yes here.

| skill | hive part | base | locator pick (r8) | pick r8 + r2 elsewhere | r2 everywhere | random K (r8) | r8 everywhere | winner | params changed | cell (llama.cpp) | ms/call | incumbent | incumbent score | ms/call | takes the job |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| route_step | coordinator: which specialist takes a plan step | 0.19 | 0.99 (263K) | 0.97 (808K) | 0.99 (611K) | - | - | all_r2 | 610,560 | 0.99 | 87 | coordinator = brain4b | 0.9746 | 7094.6 | yes |
| next_move | hive loop: what to do after a failed step | 0.25 | 0.95 (387K) | 0.97 (901K) | 0.88 (611K) | - | - | mlp_r2 | 380,160 | 0.90 | 75 | coordinator = brain4b | 0.5667 | 6449.4 | yes |
| orders_spend | guard: is a 'spend' action ORDERED | 0.31 | 0.89 (304K) | 0.97 (839K) | 0.97 (611K) | - | - | all_r2 | 610,560 | 0.97 | 76 | order_reader = fast+order_reader | 0.918 | 1162.3 | yes |
| split_orders | coordinator: the instruction checklist | 0.01 | 0.81 (209K) | 0.90 (767K) | 0.83 (611K) | - | - | thin | 767,232 | 0.91 | 148 | coordinator = brain4b | 0.28 | 11057.9 | yes |
| json_repair | engine: repair a member's broken JSON | 0.36 | 1.00 (226K) | 1.00 (780K) | 1.00 (611K) | - | - | all_r2 | 610,560 | 1.00 | 155 | code:parse_json | 0.4933 | 0.0 | yes |
| family_topic | guard: does a step touch family/relationships | 0.50 | 0.85 (313K) | 0.75 (846K) | 0.79 (611K) | - | - | all_r2 | 610,560 | 0.80 | 63 | code:guard.FAMILY | 0.875 | 0.0 | yes |
| orders_send | guard: is a 'send' action ORDERED | 0.21 | 0.89 (306K) | 0.89 (840K) | 0.93 (611K) | - | - | thin | 839,808 | 0.89 | 71 | order_reader = fast+order_reader | 0.918 | 0.0 | yes |
| quote_pick | researcher: which sentence is the evidence | 0.17 | 0.62 (319K) | 0.98 (850K) | 0.99 (611K) | 0.67 (290K) | 0.99 (2442K) | thin | 850,176 | 0.97 | 115 | researcher = brain4b | 0.9333 | 7313.7 | yes |
| orders_delete | guard: is a 'delete' action ORDERED | 0.33 | 0.87 (253K) | 0.90 (801K) | 0.95 (611K) | - | - | all_r2 | 610,560 | 0.95 | 77 | order_reader = fast+order_reader | 0.8852 | 0.0 | yes |
| claim_support | verifier: does a quote support a claim | 0.49 | 0.59 (252K) | 0.80 (799K) | 0.83 (611K) | 0.67 (249K) | 0.81 (2442K) | thin | 799,488 | 0.83 | 128 | verifier = fast+verifier | 0.88 | 10270.6 | no |
| orders_login | guard: is a 'login' action ORDERED | 0.15 | 0.93 (280K) | 0.98 (820K) | 0.98 (611K) | - | - | all_r2 | 610,560 | 0.98 | 74 | order_reader = fast+order_reader | 1.0 | 0.0 | yes |
| pick_source | researcher: which search source to query | 0.12 | 0.93 (412K) | 0.88 (919K) | 0.88 (611K) | - | - | pick | 411,648 | 0.93 | 54 | researcher = brain4b | 0.7027 | 6362.5 | yes |
| pick_element | browser: which element to act on | 0.00 | 0.47 (313K) | 0.89 (846K) | 0.93 (611K) | - | - | all_r2 | 610,560 | 0.93 | 116 | browser = fast+browser | 0.88 | 2314.3 | yes |
| orders_signup | guard: is a 'signup' action ORDERED | 0.25 | 0.84 (315K) | 0.93 (847K) | 1.00 (611K) | - | - | thin | 846,720 | 0.92 | 82 | order_reader = fast+order_reader | 0.9836 | 0.0 | yes |
| licence_open | verifier: is a licence open for any use | 0.44 | - | - | - | - | - | clone_orders_spend | 610,560 | 0.74 | 62 | juror_brain = brain4b | 0.9333 | 5087.4 | no |
| gate | the router: which cell (or group of cells) handles an input | 0.11 | 0.91 (281K) | 0.89 (821K) | 0.93 (611K) | - | - | all_r2 | 610,560 | 0.94 | 87 | - | - | - | no |
| orders_any | guard: is ANY risky action ordered (new skill made by the factory) | 0.67 | - | - | - | - | - | clone_route_step | 610,560 | 0.97 | 81 | - | - | - | no |
| element_match | browser: does this one element reach the goal (pick_element's organizer asks it per element) | 0.50 | 0.87 (295K) | 0.99 (832K) | 0.98 (611K) | - | - | thin | 831,744 | 0.99 | 61 | - | - | - | yes |

family_topic as the guard uses it (the rule OR the cell; the cell only adds blocks): 0.875 vs the rule alone 0.875 -> on.

## pick_element split into a smaller cell plus an organizer

`element_match` answers one question per element (does this element reach the goal?); the organizer asks it about every element on the page and acts on the most likely yes (`runtime.pick_element`).

| reader | test (exact id) | ms per page |
|---|---|---|
| one cell reads the whole list (pick_element) | 0.9267 | 116.5 |
| organizer over element_match | 1.0 | 182.2 |
| incumbent (browser = fast+browser) | 0.88 | - |

## The five order cells as one organizer (as the guard uses them, 63 held-out tasks)

| reader | exact | false approvals | missed orders |
|---|---|---|---|
| order cells alone | 0.73 | 12 | 6 |
| parser AND order cells | 0.905 | 0 | 6 |
| order reader member (Qwen3-1.7B + edit) alone | 0.73 | 12 | 8 |
| parser AND order reader member | 0.873 | 0 | 8 |

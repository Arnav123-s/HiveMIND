# The smallest specialist for translations: a German grammar cell

Instead of one model that translates German best, the smallest job a tiny cell can do: say whether a German sentence
is grammatical (ok / error). The 1.7B translates, the cell checks, only a sentence it calls an error goes to the 4B.

**Data.** Grammatical: professional German from the WMT news test sets (2016-2017 to train, 2014 to test, no sentence
in both). Errors: one thing broken in code per sentence (a subordinate clause's verb moved, "am Morgen" -> "in der
Morgen", the dative after mit/von/zu turned accusative, an article swapped, an adjective ending changed).

| judge | test (150 sentences, half with an error) |
|---|---|
| nothing (every sentence ok, as today) | 0.500 |
| bare SmolLM2-135M | 0.467 |
| **cell on SmolLM2-135M** (every module, rank 2, 300 steps) | 0.573 (0.567 served) |
| **cell on Qwen2.5-0.5B**, the next smallest base that knows German (same recipe) | 0.640 (torch; not served: the disk was full) |

The 135M base has too little German to sharpen: it calls "Der Zug fährt um 9 Uhr in der Morgens." ok (0.96). The
0.5B learned more, then memorised its 600 examples (training loss 0.009, test 0.640).

**The chain** (training/reports/translator_chain_de.json, 160 held-out sentences, chrF / seconds per sentence):

| | chrF | s |
|---|---|---|
| writer (1.7B) alone | 46.4 | 4.4 |
| 4B always | 50.2 | 5.4 |
| chain with the 135M cell | 46.4 | 6.3 (58 to the 4B) |
| chain with a perfect judge | 53.0 | 7.8 (100 to the 4B) |

**Decision: translations stay with the 4B; the cell is not called by the hive.** Two reasons, both measured: the
cells judge little better than chance on this job; and on short translations the 4B is barely slower than the 1.7B
(prompt reading dominates), so a chain pays the 1.7B plus the 4B for every flagged sentence. To beat the 4B alone on
time a judge would have to flag fewer than 1 sentence in 6, and a grammar judge cannot pass a sentence the 4B would
have worded better. A smaller specialist pays where its job replaces a long call of a big model, not where the big
model is nearly as fast.

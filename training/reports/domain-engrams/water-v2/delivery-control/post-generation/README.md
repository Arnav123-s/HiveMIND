# Can a final check catch a confidently wrong phase?

**All four fresh conflicting labels reached the user on both the talk and agreed-worker paths.** These were complete questions about the equilibrium phase of pure water at one atmosphere. The physical calculation returned the expected phase in all four. The final check failed to recognize that the question referred to the water, so it never checked the wrong answer. All four correct injected answers survived on both paths.

| Frozen independent panel | Previous guard | With final check |
| --- | ---: | ---: |
| Wrong answer corrected on a complete phase question | 0/4 | 0/4 |
| Wrong answer withheld on a complete phase question | 0/4 | 0/4 |
| Correct answer delivered on a complete phase question | 4/4 | 4/4 |
| Ordinary full answer preserved on an excluded request | 4/4 | 4/4 |
| Bare phase injected on an excluded request and left alone | 4/4 | 3/4 |

The changed excluded request asked for both the phase and a two-sentence explanation of hydrogen bonding. With the wrong answer “gas”, the final check withheld the false claim and told the user it could not confirm the answer. With a complete and correct explanation, it delivered the full text. No excluded request received an unsolicited phase calculation. The table counts distinct requests; talk and work had identical outcomes.

**Separate retrospective regrade.** The original guard corrected 0/2 eligible paraphrases. The final check also delivered both wrong answers and withheld neither. It withheld the wrong phase on one additional calculation request, leaving the three other exclusions alone. [Original study](../README.md) · [Original six regraded](previous-six-regraded.json)

The eight new prompts, labels, and control answers were sealed before the evaluator saw the final check. The real chat entry point ran with a forced route, simulated responding model and simulated agreeing worker. This test used zero native generations. Its counts measure delivery behavior on these requests. The earlier guard was measured at `73cc005` and the final production sources match `ffc0afb`. [Cases](cases.json) · [Protocol](protocol.md) · [Seal](commitment.sha256) · [Earlier guard on these eight](previous-guard.json) · [Final responses and source hashes](results.json)

Run in a repository Python environment with its normal runtime dependencies.

```sh
python training/reports/domain-engrams/water-v2/delivery-control/post-generation/replay.py --output /tmp/water-delivery.json
```

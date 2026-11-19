# Domain advice on unseen requests

This study tests which specialist should handle an utterance across coding, mathematics, physical science, conversation, machine learning and computer engineering. It measures the advisory signal in the public runtime. Answer quality, specialist execution and memory retention need separate tests.

**The learned router got 34 of 60 decisions right.** It routed 23 of the 48 supported requests correctly, sent two to the wrong specialist and abstained on 23. It correctly abstained on 11 of the 12 open-set requests. The public-data centroid got 38 decisions right and still led at 37 when restricted to the same history as the learned sender. The router passed 4 of 10 predeclared checks, including both sender-intervention checks. This panel supports an advisory signal and falls short of the threshold for authoritative routing. [Measured results](results.json)

| Method | Correct / 60 | Correct among emitted advice | Correctly advised on 48 supported | Spurious advice on 12 open-set |
| --- | ---: | ---: | ---: | ---: |
| Legacy no-advice interface | 12 | 0 emitted | 0 | 0 |
| Keywords, no history | 27 | 17/22 | 17 | 2 |
| Keywords, recent two turns | 33 | 23/29 | 23 | 2 |
| TF–IDF centroid, recent two turns | **38** | 27/34 | 27 | 1 |
| TF–IDF centroid, latest prior user | 37 | 26/34 | 26 | 1 |
| Learned request and context senders | **34** | **23/26** | 23 | 1 |

Relative to the full-history centroid, the learned router won four individual cases and lost eight. The two approaches agreed in correctness on the remaining 48. Relative to keywords it won nine and lost eight. The production sender reads the latest prior user turn. A secondary check, added after the primary comparison, limits both conventional baselines to that same text. The matched-view lexical score is 29/60 and the matched-view centroid score is 37/60. All original learned decisions, confidences, traces and gates reproduced exactly in that check. [Initial paired outputs](first-pass.json.gz)

| Request group | Learned | Keywords | TF–IDF centroid |
| --- | ---: | ---: | ---: |
| Ordinary direct requests | 9/12 | 10/12 | 9/12 |
| Difficult direct requests | 5/12 | 1/12 | 2/12 |
| Follow-ups requiring prior context | 3/12 | 6/12 | 10/12 |
| Clear request after irrelevant history | 4/6 | 5/6 | 4/6 |
| Explicit topic corrections | 2/6 | 1/6 | 2/6 |
| Missing referent | 2/2 | 2/2 | 2/2 |
| Outside-domain lookups | 5/6 | 5/6 | 5/6 |
| Ambiguous domain | 4/4 | 3/4 | 4/4 |

The learned router's domain scores out of eight were coding 2, mathematics 6, physical science 3, conversation 5, machine learning 2 and computer engineering 5. It recognized the difficult prompt about a bicycle wheel braking as physical science. It selected conversation for a request about calibrating churn scores and physical science when the user explicitly switched from a fluid simulation to an FPGA timing report. It sent a 1954 film-director lookup to mathematics at confidence 0.808. That was the only error among 24 predictions at confidence 0.8 or higher. The panel is too small to establish general calibration.

The later [agreement audit](consensus/README.md) tested requiring the learned router and a same-view centroid to agree. On 30 new requests it retained 7/8 correct suggestions and prevented zero wrong suggestions.

## Causal checks

| Reader input | Correct / 60 | Direct ordinary + difficult / 24 | Context-dependent / 12 |
| --- | ---: | ---: | ---: |
| Intact frames | 34 | 14 | 3 |
| Valid zero-context payload | 31 | 14 | 0 |
| Shuffled context payload | 31 | 14 | 0 |
| Valid empty-request payload | 12 | 0 | 0 |
| Shuffled request payload | 11 | 2 | 2 |
| Missing either frame, or both | 12 | 0 | 0 |

Context carried information for three follow-ups. Shuffled history also sent seven supported requests to a wrong domain, compared with two under intact history and zero under empty history. The shuffle changed 23 of 24 eligible context payloads and 58 of 60 request payloads. A transport-level missing frame caused universal abstention. The valid-payload interventions isolate signal content while preserving frame validity. Sixty warm calls to the public API took about 26 ms in aggregate on this CPU. No reasoning model was invoked.

## Study design

An evaluator who had the six domain names and the runtime signature authored 60 held-out requests before inspecting the trainer, model or any training phrases. The training agent received corpus hashes and counts and did not receive examples or targets before the artifact freeze. None of the evaluated messages or history turns matched a public seed utterance or topic phrase after case and punctuation normalization. The scorer supplies the API only the current message and ordered history. It opens the independent key after predictions. Results include abstentions, false advice, wrong domains and matched cases.

Of the 60 requests, 48 call for one of six specialists. Each specialist has eight requests. Twelve additional requests should yield no specialist advice. These include unrelated lookups and requests without enough information to identify a task. This is a deliberately composed English panel. The six duplicated clean/noisy requests and repeated follow-up phrases support controlled comparisons and reduce independence between rows. [Protocol](protocol.md) · [Requests](cases.json) · [Keys and explanations](keys.json)

The simple lexical control uses fixed domain terminology and referring expressions. The public-data control fits TF–IDF class centroids using word and character terms. It uses the first 32 utterances from each public section and all ten topic phrases for each domain, selecting rejection thresholds on a deterministic 20% of those public examples. The sender also has derived lexical anchors and recombinations for training its reader. The centroid uses the same public source material and has its own representation. The previous router chose talk or work and emitted no six-way advice. Its abstain-on-every-row control measures the effect of adding advice at that interface without inventing a mapping from talk/work to six domains. [Lexical baseline](keywords.py) · [Public-data baseline](centroid.py) · [Baseline protocol](centroid-protocol.md)

Each causal intervention goes through the same reader. Removing a frame tests the transport contract. Replacing only its payload with one encoded from empty input tests the information the sender contributed. A deterministic single-cycle shuffle transfers the sender payload from another row and preserves the destination task, role, sender and bundle metadata. Context payloads are shuffled among rows with actual history, leaving originally empty histories alone. The scorer also checks that the intact frame reader and normal public API agree on every request.

## Reproduce

From this repository root, run the study on the bundled CPU signal model.

```sh
p=training/reports/domain-memory/signals
python "$p/evaluate.py" --checkout . --output signal-results.json
```

The report records each predicted route, confidence, decoded signals, frame payloads, shuffled donor IDs and paired disagreements. Its `metadata.sources` identifies the exact imported code and public training files. Bundle SHA-256 is `5b4dae6310c3cb144d4f477199f426cbfaf0cc272a1869379060322512d75350`. Shared-machine timings vary. The centroid and lexical baselines use Python's standard library. Rebuilding the trained artifact uses the trainer's own dependencies. Corpus SHA-256 is `566a530032ab75138fd81807b3fb81e57c025d0c06723998152f2f60a375b7d7`. The independent key SHA-256 is `05544d445bb2794df2d3f64d80f4b42fc52ce38a8240be6221cf06d9893c01e6`. [Evaluator](evaluate.py)

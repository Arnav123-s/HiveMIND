# Learned request and history signals

A request sender sees only the current message. A separately fitted context sender sees only the latest user turn among the last eight history entries. Each sends a small vector of integers from 0 to 31 to a matched reader. The reader suggests one of six specialist domains or abstains. It sees the two vectors without seeing the words in the conversation. Normal inference uses the Python standard library and the single 81,836-byte local asset in `team/assets/`.

In an independent 60-case evaluation, the pair correctly referred **23 requests**, incorrectly referred **3**, and abstained on **34**. Eleven of its abstentions were correct, giving **34/60** overall. A frozen lexical rule scored 33/60 and a TF–IDF centroid trained on the public material scored 38/60. Real context solved 3 of 12 follow-ups, compared with zero using shuffled or absent context. This is one small evaluation. A reader confidence is its own score, which can be high on a mistaken suggestion. For example, “Please look up the closest pharmacy” was confidently misrouted as conversation in a separate manual check.

## Training and input separation

The public corpus has 38 authored requests in each of the six domains, plus referential follow-ups and unrelated requests. Within each section, the first 32 are used for fitting and the final six for selecting abstention thresholds. Ten additional groups of topical terms per domain give the senders vocabulary anchors. Full groups and their individual terms are included. The reader fits direct requests, requests paired with a different preceding topic, referential turns with each preceding domain, and cases that should abstain. It trains on 704 pairs and two reproducible softened copies per pair. These are combinations of the original utterances.

Both text senders are fitted multinomial linear models over weighted word unigrams, bigrams, character trigrams and a numeric-expression feature. Their coefficient matrices are stored as signed eight-bit integers. The request sender estimates six domains, a follow-up and an unrelated class. The context sender estimates six domains and an unrelated class. Each probability is rounded to one of 32 levels. A sender with a predicted domain also needs a training term associated with that domain. The reader fits a final multinomial classifier over the two quantized vectors and interactions between current intent and context. The shipped code requires agreement between the eligible sender and the reader before referring the request. No language model or network is invoked by this decision.

The 48 reserved development utterances produced 132 combinations. The channel made 81 correct referrals and zero wrong referrals there, including zero referrals for the 24 unsupported combinations. Those scores were used to select the thresholds. The independent cases were kept from the trainer until the corpus, weights and inference implementation were frozen. The training runner reproduced the compressed bytes and fit report exactly on Python 3.12.14 with NumPy 2.3.5, SciPy 1.17.0 and scikit-learn 1.8.0. [Public requests](requests.txt) · [Topic anchors](topics.txt) · [Fit counts and digests](fit.json)

## Reproduce training

From the repository root in an environment with NumPy, SciPy and scikit-learn, run:

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python training/signals/train.py --out /tmp/hive-signals.json.gz --report /tmp/hive-signals-fit.json
```

The compressed bundle SHA-256 is `5b4dae6310c3cb144d4f477199f426cbfaf0cc272a1869379060322512d75350`. The serving module checks this exact identity, the task name, version, domain order and code resolution before using the weights. A frame includes the task identifier derived from the bounded current and prior text, its sender and role, protocol version, paired bundle identity, and quantized payload. The reader accepts identical repeated frames in either order and declines missing, stale, conflicting or incompatible pairs. These checks identify matching messages within the local application. No authenticated network transport is implemented here.

```python
from team.signals import frames, read_frames, read_request

previous = [{"role": "user", "content": "How does a CPU cache work?"}]
advice = read_request("Could you explain that again?", previous)
task, request, context = frames("Could you explain that again?", previous)
assert read_frames(task, [context, request]) == advice
```

The frozen serving source digest for the independent evaluation is `51d769ee1c5e2dfa40c5820c17e8b0107d8536a7640aaadfd57f801eab44a626`. The earlier sensor study provides the matched-sender design and its original protocol experiments. [Earlier study](../reports/rule_lab/hive-telepathy.md)

## Operational agreement check

An independent public-data classifier can veto a referral. `team.domain_consensus.read_consensus(message, history, decision)` keeps the original pair's decision only if the TF–IDF centroid classifier names that very domain. Both see the current message and at most the same most recent prior user message. A missing or incompatible local classifier makes the gate abstain. For the pharmacy lookup that fooled the pair, the centroid abstains and the operational gate withholds the referral.

The centroid uses 316 public texts, drawn from the first 32 rows per request class plus the 60 domain vocabulary lines. Its original calibration procedure used 67 public texts to choose the cosine cutoff of 0.12 and a zero margin, then refit the centroids to all 316. The shipped binary64 weights reproduce the original class centers exactly. The reader and the independent centroid share the underlying public vocabulary, so agreement can still endorse a shared mistake. An agreement-only rule also withholds some valid suggestions.

```sh
python training/signals/fit_centroid.py --out /tmp/hive-domain-centroid.json.gz
```

The packed centroid SHA-256 is `1bdef5f3dffdb8e5edfe756d02cb762782a9c4fa3497e0eabae88659d57e83a3`. The agreement policy was selected after inspecting the original 60-case study. Its original-panel figures are exploratory. [Evaluation and baselines](../reports/domain-memory/signals/README.md)

The packed runtime matched the original centroid implementation for 728 public query/history combinations, and the independent evaluator confirmed identical agreement decisions on all 90 held-out inputs. In the original 60-case panel the gate issued 21 referrals, 20 correct. It filtered two wrong referrals and withheld three correct ones. In a new panel frozen before the gate was graded, the pair issued eight correct referrals on 30 cases. Agreement kept seven. Both approaches abstained on all six unsupported requests and issued zero wrong referrals in that sample. The seven-way score was 13/30 for agreement and 14/30 for the pair alone.

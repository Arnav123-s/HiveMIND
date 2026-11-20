"""Prepare the independent six-order challenge. No imports from the project."""
import json
from pathlib import Path

ROOT = Path(__file__).parent
stream, keys, witnesses = {}, {}, {}


def row(name, group, description, source, key, public, validation, private, witness, oracle):
    def examples(items):
        return [{'input': {key: item}, 'output': oracle(item)} for item in items]

    sets = [public, validation, private, witness]
    serial = [json.dumps(v) for vs in sets for v in vs]
    assert len(set(serial)) == len(serial), name
    entry = {'id': name, 'phase': 'challenge_confirmation', 'group': group,
             'prompt': 'Write solve(x). ' + description, 'source': source.strip(),
             'public': examples(public), 'validation': examples(validation)}
    stream[name] = entry
    keys[name] = {'private': examples(private)}
    witnesses[name] = examples(witness)


row('after_hours_log', 'correct_control',
    'A branch closes 480 minutes after its opening time. Count the logged departures strictly after closing. A departure at 480 is on time. '
    'x["minutes"] lists nonnegative integer minutes since opening.',
    """
def solve(x):
    return sum(minute > 480 for minute in x['minutes'])
""", 'minutes',
    [[], [480], [350, 482], [500, 500, 475]],
    [[480, 480], [479, 480, 481], [333], [481, 590]],
    [[480, 520], [600], [3, 150, 470], [481, 481, 479], [480, 480, 480], [520, 471, 500, 480]],
    [], lambda times: len([v for v in times if v >= 481]))

row('printed_shelf_labels', 'correct_control',
    'A shop has a list of numeric shelf label identifiers in x["labels"]. Each list entry represents one printed label. '
    'Repeated identifiers count as separate printed labels. Return the number printed.',
    """
def solve(x):
    labels = x['labels']
    return len(labels)
""", 'labels',
    [[], [88], [14, 14], [3, 20, 49]],
    [[9000], [10, 11], [1, 1, 1], [57, 12, 44, 57]],
    [[4], [3, 3], [81, 909, 21], [0, 0, 0, 0], [8, 8, 8, 8, 8], [0, 305]],
    [], lambda labels: sum(1 for _ in labels))

row('clinic_break_credit', 'wrong_primary_observable',
    'A shift earns one break credit for each break lasting at least 30 full minutes, including exactly 30. '
    'x["breaks"] gives each duration in nonnegative whole minutes. Return the number of credits.',
    """
def solve(x):
    return sum(duration > 30 for duration in x['breaks'])
""", 'breaks',
    [[], [29], [35, 14], [41, 31, 20]],
    [[0, 19], [28, 33], [31, 45, 65], [12, 27, 38, 14]],
    [[30], [30, 30], [29, 45], [28, 30, 45], [40, 35, 15], [60, 0, 30, 0]],
    [], lambda durations: len([d for d in durations if d >= 30]))

row('food_bank_cart_count', 'correct_primary_observable',
    'Each loaded food-bank cart has at least one box. x["boxes"] lists the positive number of boxes on each cart. '
    'The dispatch desk needs the number of carts, one numbered loading slot per cart.',
    """
def solve(x):
    carts = x['boxes']
    return len(carts)
""", 'boxes',
    [[], [1], [1, 1], [1] * 3],
    [[1] * n for n in (4, 5, 6, 7)],
    [[2], [3, 1], [1, 2, 1], [4, 4], [1] * 8, [1, 1, 3, 1, 1]],
    [], lambda carts: sum(1 for _ in carts))

row('meal_voucher_total', 'job_agreement_but_not_equivalent',
    'x["vouchers"] gives how many meal vouchers each reception desk issued (nonnegative whole numbers). '
    'Return the total number of vouchers issued by all the desks.',
    """
def solve(x):
    issued = x['vouchers']
    return len(issued)
""", 'vouchers',
    [[], [1], [0, 2], [1, 0, 2]],
    [[2, 0], [1, 2, 0], [3, 0, 1, 0], [0, 0, 3]],
    [[2, 1, 0], [0, 3, 0], [0, 0, 2, 2], [0, 0, 0, 4], [1, 1, 0, 1, 2], [1, 1, 1, 1, 1, 1]],
    [[1, 4, 0]], lambda counts: sum(counts))

row('stationery_envelopes', 'shared_error_outside_taught_edits',
    'A print shop mails every proof with a quality score strictly above 70. Each envelope fits four proofs. '
    'Use as few envelopes as possible, counting the last partially filled envelope. '
    'x["scores"] gives one integer per proof. Return the number of envelopes used.',
    """
def solve(x):
    scores = x['scores']
    accepted = [score for score in scores if score > 70]
    return (len(accepted) + 2) // 4
""", 'scores',
    [[], [8, 9], [80, 81], [81, 85, 92, 98]],
    [[72, 73, 74], [78, 11, 82], [82, 82, 82, 82, 82, 82], [29, 68, 12]],
    [[71], [71, 29], [99, 99, 99, 99, 99], [28, 15], [92, 82, 72], [78, 80, 82, 84, 86, 88, 90, 92, 94]],
    [[70, 70, 70]], lambda scores: len(range(0, sum(v >= 71 for v in scores), 4)))


for name, obj in [('stream', stream), ('keys', keys), ('witnesses', witnesses)]:
    (ROOT / (name + '.json')).write_text(json.dumps(obj, sort_keys=True, indent=2) + '\n')

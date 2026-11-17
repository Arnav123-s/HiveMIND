"""The kind h_txt_redact: card numbers of one shape masked in a text, every other number left as it is (hard: text).

A kind of task in one file (training/kinds/, docs/KINDS.md): its maker draws the task and its check from a seed. It is
held out: never practised or taught, so what the hive scores on it is what carries over from the kinds it was taught.
"""
from training import hive_bench as B
from training.kinds._common import _file, _says, HARD_NAMES as NAMES

KIND = "h_txt_redact"
FAMILY = "hard: text"
HARD = True
ORDER = 450
HELD_OUT = True


def _digits(r, n):
    return "".join(str(r.randrange(10)) for _ in range(n))


def h_txt_redact(r):
    pieces, want, cards = [], [], 0
    kinds = ["card", "card", "card", "three", "five", "plain", "mixed", "phone", "date", "amount"]
    for kind in r.sample(kinds, r.randrange(6, 10)):
        who = r.choice(NAMES)
        if kind == "card":  # four groups of four digits, by '-' or by single spaces: masked, the last four kept
            sep = r.choice(["-", " "])
            groups = [_digits(r, 4) for _ in range(4)]
            raw, masked = sep.join(groups), sep.join(["****"] * 3 + [groups[3]])
            cards += 1
        elif kind == "three":
            raw = masked = "-".join(_digits(r, 4) for _ in range(3))
        elif kind == "five":
            raw = masked = "-".join(_digits(r, 4) for _ in range(5))
        elif kind == "plain":
            raw = masked = _digits(r, 16)
        elif kind == "mixed":
            raw = masked = f"{_digits(r, 4)}-{_digits(r, 4)} {_digits(r, 4)}-{_digits(r, 4)}"
        elif kind == "phone":
            raw = masked = f"{r.randrange(200, 999)}-{r.randrange(200, 999)}-{_digits(r, 4)}"
        elif kind == "date":
            raw = masked = f"2026-{r.randrange(1, 13):02d}-{r.randrange(1, 29):02d}"
        else:
            raw = masked = f"{r.randrange(100, 9999)}.{_digits(r, 2)}"
        say = r.choice(["{w} gave the number {x}.", "Reference {x} belongs to {w}.", "{w} wrote: {x}, then left.", "On file for {w}: {x}!"])
        pieces.append(say.format(w=who, x=raw))
        want.append(say.format(w=who, x=masked))
    if not cards:  # at least one card to mask
        groups = [_digits(r, 4) for _ in range(4)]
        pieces.append(f"The card was {'-'.join(groups)}.")
        want.append(f"The card was {'-'.join(['****'] * 3 + [groups[3]])}.")
        cards = 1
    text, done = " ".join(pieces), " ".join(want)

    def check(run, report):
        f = _file(run, "redacted.txt")
        if not f:
            return False, "no redacted.txt saved"
        got = " ".join(f.read_text().split())
        ok = got == done and _says(B._body(report), cards, 0.1)
        return ok, f"redacted.txt {'is' if got == done else 'is not'} the text masked as asked; {cards} cards said"
    return ("hard: text", "card numbers masked in a text", "Here is a text:\n" + text + "\nA card number is exactly four groups of "
            "four digits, the groups joined all by '-' or all by single spaces, with no other digit or group right before or after "
            "it. Replace every digit of a card number except its last four with '*', keeping the separators, and leave every other "
            "number exactly as it is (dates, amounts, phone numbers, numbers of three or five groups, sixteen digits in one run, "
            "mixed separators). Save the whole text so changed in redacted.txt and tell me how many card numbers you masked.", check)


make = h_txt_redact
lesson = None

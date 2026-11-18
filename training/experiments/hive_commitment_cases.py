"""Paired conversation fixtures. Expected states are evaluated outside the worker."""
import random

from training.experiments.hive_commitments import DAYS
DOMAINS = {
    "meeting": (("Meridian", "Lumen", "Aster", "Tern"), ("Cedar", "Birch", "Elm", "Maple", "Ash", "Pine")),
    "pickup": (("Indigo", "Saffron", "Pearl", "Coral"), ("North", "South", "Harbor", "Hill", "Vale", "Park")),
}

# Four positions describe the two complete rows after the instruction. Lower-case
# letters are original values, uppercase are the first edit, and x/y are fresh alternatives.
# a/b = original day/site for the first-edited item; c/d = other original day/site.
FORMS = (
    (
        ("plain", "Move {other} to {x}.", "ABxd"),
        ("plain", "Put {src} at {y}.", "Aycd"),
        ("tentative", "We talked about {other} at {y}; that was a possibility, not a decision. File what we already have.", "ABcd"),
        ("withdraw", "Scratch my last request altogether. Both entries should look the way they did when we started.", "abcd"),
        ("recipient", "Wrong label on my last request. It was for {other} instead of {src}. Please fix that mix-up.", "abAB"),
        ("copy", "Actually {other} needs the exact same day and site too. Keep {src}'s change.", "ABAB"),
        ("partial", "I still want the new day for {src}, but please put it back at its original site.", "Abcd"),
        ("split", "Only the change of day was meant for {other}, not {src}. The change of site for {src} stands.", "aBAd"),
        ("replace", "Forget the earlier plan for {src}. Instead make {other} happen on {x}, where it already was.", "abxd"),
        ("two_edits", "One more correction. {src} goes on {x}; {other} should use {y}. Keep everything else in the draft.", "xBcy"),
        ("relative", "Move {other} to the day after {src}'s drafted day. Leave both sites alone.", "ABnd"),
        ("swap", "Swap the sites of the two entries as they stand in the draft. Keep the days.", "AdcB"),
        ("ambiguous", "I need one of these two entries at {y}. I'll specify which if you ask.", "Aycd"),
        ("ambiguous", "I need one of these two entries at {y}. I'll specify which if you ask.", "ABcy"),
    ),
    (
        ("plain", "Please move {src} to {x}.", "xBcd"),
        ("plain", "Switch {other} to {y}.", "ABcy"),
        ("tentative", "A colleague suggested {x} for {src}. I haven't approved that suggestion. Use the draft on file.", "ABcd"),
        ("withdraw", "I've changed my mind about both adjustments. Restore the opening plan in full.", "abcd"),
        ("recipient", "I named the wrong item earlier. {other} was supposed to get those two adjustments. Restore {src}.", "abAB"),
        ("copy", "Give {other} that combination as well. I want both items to match the revised one.", "ABAB"),
        ("partial", "Leave {src} at the place you just selected. For its day, go back to the one in the opening record.", "aBcd"),
        ("split", "The site change belongs on {other}. Restore the site for {src}, and keep its new day.", "AbcB"),
        ("replace", "Drop the edits to {src}. The only change from the opening records should be {other} at {y}.", "abcy"),
        ("two_edits", "Build on the pending plan. Give {other} the day {x} and put {src} at {y}.", "Ayxd"),
        ("relative", "For {other}, use the weekday immediately following the day now penciled in for {src}. Keep its site.", "ABnd"),
        ("swap", "Each entry should use the other's current location. Preserve their respective days in the pending plan.", "AdcB"),
        ("ambiguous", "One of the two should run on {x}. I haven't said which one yet.", "xBcd"),
        ("ambiguous", "One of the two should run on {x}. I haven't said which one yet.", "ABxd"),
    ),
)


def cases(groups=FORMS, offset=0):
    for cohort, forms in enumerate(groups, start=offset):
        for i, (kind, text, signature) in enumerate(forms):
            # The last two cases have byte-identical public information and different user intentions.
            pair = min(i, len(forms) - 2)
            rng = random.Random(59000 + cohort * 100 + pair)
            domain = ("meeting", "pickup")[(cohort + pair) % 2]
            names, sites = DOMAINS[domain]
            src, other = rng.sample(names, 2)
            a, c, new_day, x = rng.sample(DAYS, 4)
            b, d, new_site, y = rng.sample(sites, 4)
            values = {"a": a, "b": b, "c": c, "d": d, "A": new_day, "B": new_site, "x": x, "y": y,
                      "n": DAYS[(DAYS.index(new_day) + 1) % 7]}
            names = sorted((src, other))
            opening = {src: [a, b], other: [c, d]}
            first = f"Move {src} to {new_day} at {new_site}."
            last = text.format(src=src, other=other, x=x, y=y)
            gold = [values[k] for k in signature]
            answer = ""
            if kind == "ambiguous":
                chosen = src if i == len(forms) - 2 else other
                answer = f"I mean {chosen}."
            yield {"case": f"{cohort + 1}-{i + 1:02}", "cohort": cohort + 1, "kind": kind,
                   "public": {"domain": domain, "names": names, "sites": list(sites), "opening": opening,
                              "first": first, "last": last}, "clarification": answer,
                   "expected": {src: gold[:2], other: gold[2:]}}

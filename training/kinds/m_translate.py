"""The kind m_translate: a sentence to translate (languages).

A kind of task in one file (training/kinds/, docs/KINDS.md): its maker draws the task and its check from a seed, and
it has no lesson: the hive is never shown it done.
"""
from training import hive_bench as B

KIND = "m_translate"
FAMILY = "languages"
HARD = False
ORDER = 140


TONGUES = {"German": ({"library": "bibliothek", "bakery": ("bäckerei", "backerei"), "museum": "museum", "pharmacy": "apotheke"},
                      {"seven": ("sieben", "7"), "nine": ("neun", "9"), "ten": ("zehn", "10")}, {"Mondays": "montag", "Sundays": "sonntag", "Fridays": "freitag"}),
           "French": ({"library": ("bibliothèque", "bibliotheque"), "bakery": "boulangerie", "museum": ("musée", "musee"), "pharmacy": "pharmacie"},
                      {"seven": ("sept", "7"), "nine": ("neuf", "9"), "ten": ("dix", "10")}, {"Mondays": "lundi", "Sundays": "dimanche", "Fridays": "vendredi"}),
           "Spanish": ({"library": "biblioteca", "bakery": ("panadería", "panaderia"), "museum": "museo", "pharmacy": "farmacia"},
                       {"seven": ("siete", "7"), "nine": ("nueve", "9"), "ten": ("diez", "10")}, {"Mondays": "lunes", "Sundays": "domingo", "Fridays": "viernes"}),
           "Italian": ({"library": "biblioteca", "bakery": ("panetteria", "panificio", "forno"), "museum": "museo", "pharmacy": "farmacia"},
                       {"seven": ("sette", "7"), "nine": ("nove", "9"), "ten": ("dieci", "10")}, {"Mondays": ("lunedì", "lunedi"), "Sundays": "domenic", "Fridays": ("venerdì", "venerdi")})}


def m_translate(r):
    lang = r.choice(sorted(TONGUES))
    places, hours, days = TONGUES[lang]
    place, hour, day = r.choice(sorted(places)), r.choice(sorted(hours)), r.choice(sorted(days))
    verb = r.choice(["opens", "closes"])
    tup = lambda v: v if isinstance(v, tuple) else (v,)  # noqa: E731

    def check(run, report):
        low = B._body(report).lower()
        hits = [any(w in low for w in tup(v)) for v in (places[place], hours[hour], days[day])]
        # 'museum' is German too: a word that is the same in both languages is not an English word left in
        left = place in low and place not in tup(places[place])
        return all(hits) and not left, f"place, hour and day in {lang}: {hits}; the English word left in: {left}"
    return "languages", "translate a sentence", f"Translate into {lang}: 'The {place} {verb} at {hour} on {day}.'", check


make = m_translate
lesson = None

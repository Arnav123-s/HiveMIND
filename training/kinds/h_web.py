"""The kind h_web: a fact found on the open web, checked against what Wikidata records (hard: open web).

A kind of task in one file (training/kinds/, docs/KINDS.md): its maker draws the task and its check from a seed, and
its lesson writes the right program for a task of it (training/lessons.py teaches it).
"""
import random
import re

from training import hive_bench as B
from training.kinds._common import _fill, _nums

KIND = "h_web"
FAMILY = "hard: open web"
HARD = True
ORDER = 130
LESSON_ORDER = 230
NETWORK = True


WEB = [  # (class, property, how many Wikipedia languages at least, what is asked, unit factors to the unit asked, tolerance)
    ("Q515", "P1082", 40, "the population of {name}{where}", {"Q199": 1.0}, 0.005, "people"),          # city: population
    ("Q8502", "P2044", 25, "the height above sea level of {name}{where}, in metres", {"Q11573": 1.0, "Q3710": 0.3048}, 0.01, "m"),
    ("Q4022", "P2043", 30, "the length of the river {name}{where}, in kilometres", {"Q828224": 1.0, "Q11573": 0.001, "Q253276": 1.609344}, 0.02, "km"),
]


WEB_FALLBACK = {"Q515": ["Q90", "Q64", "Q1490", "Q1486", "Q60"], "Q8502": ["Q513", "Q1286", "Q178167"], "Q4022": ["Q3392", "Q584", "Q1471"]}


_UA = {"User-Agent": "hive-exam/1.0"}


def _web_pick(cls, prop, links, seed):
    """One item of the class, with the property, known in at least `links` Wikipedias, chosen by the seed: (id, name,
    country). The open web is the hive's endless supply of tasks it has never seen; Wikidata says what is true."""
    import requests
    q = (f'SELECT ?item ?label ?ctry WHERE {{ ?item wdt:P31 wd:{cls}; wdt:{prop} ?v; wikibase:sitelinks ?sl. FILTER(?sl > {links}) '
         f'?item rdfs:label ?label FILTER(lang(?label) = "en") OPTIONAL {{ ?item wdt:P17 ?c. ?c rdfs:label ?ctry FILTER(lang(?ctry) = "en") }} }} '
         f'ORDER BY MD5(CONCAT(STR(?item), "{seed}")) LIMIT 1')
    try:
        b = requests.get("https://query.wikidata.org/sparql", params={"query": q}, headers=_UA | {"Accept": "application/sparql-results+json"},
                         timeout=55).json()["results"]["bindings"][0]
        return b["item"]["value"].rsplit("/", 1)[1], b["label"]["value"], b.get("ctry", {}).get("value", "")
    except Exception:  # noqa: BLE001 - the query service is busy at times: a known item instead
        import random
        qid = random.Random(seed).choice(WEB_FALLBACK[cls])
        return qid, _web_label(qid), ""


def _web_claims(qid):
    import requests
    return requests.get(f"https://www.wikidata.org/wiki/Special:EntityData/{qid}.json", headers=_UA, timeout=30).json()["entities"][qid]


def _web_label(qid):
    return _web_claims(qid)["labels"]["en"]["value"]


def _web_values(qid, prop, units):
    out = []
    for c in _web_claims(qid).get("claims", {}).get(prop, []):
        v = c.get("mainsnak", {}).get("datavalue", {}).get("value")
        if isinstance(v, dict) and "amount" in v:
            unit = v.get("unit", "").rsplit("/", 1)[-1]
            unit = "Q199" if unit in ("", "1") else unit  # a count has no unit ("1")
            if unit in units:
                out.append(float(v["amount"]) * units[unit])
    return out


def h_web(r, pick=None):
    cls, prop, links, what, units, tol, unit = r.choice(WEB)
    qid, name, ctry = (pick or _web_pick)(cls, prop, links, f"{r.random():.12f}")
    where = f" ({ctry})" if ctry and ctry != name else ""

    def check(run, report):
        vals = _web_values(qid, prop, units)
        ok = any(abs(g - v) <= max(tol * abs(v), 0.5) for g in _nums(B._body(report)) for v in vals)
        return ok, f"{name} ({qid}): Wikidata records {', '.join(f'{v:g}' for v in vals[:6])} {unit}; one of them in the answer: {ok}"
    return ("hard: open web", "a fact found on the open web", f"Find {what.format(name=name, where=where)}, as Wikidata records it "
            f"(Wikidata item {qid}). Answer with the number.", check)


WIKIDATA = {  # what is asked -> (the property, its units in the unit asked for)
    "population": ("P1082", {"Q199": 1.0}),
    "height above sea level": ("P2044", {"Q11573": 1.0, "Q3710": 0.3048}),
    "length of the river": ("P2043", {"Q828224": 1.0, "Q11573": 0.001, "Q253276": 1.609344}),
}


def wikidata(task):
    m = re.search(r"Wikidata item (Q\d+)", task)
    what = next((k for k in WIKIDATA if k in task), None)
    if not (m and what):
        return None
    prop, units = WIKIDATA[what]
    return _fill('''import requests

qid, prop = __QID__, __PROP__
units = __UNITS__  # the unit's item on Wikidata -> how many of the unit asked for it is
data = requests.get(f"https://www.wikidata.org/wiki/Special:EntityData/{qid}.json", headers={"User-Agent": "hive/1.0"}, timeout=30).json()
claims = data["entities"][qid]["claims"][prop]
best = [c for c in claims if c["rank"] == "preferred"] or [c for c in claims if c["rank"] == "normal"]
value = best[0]["mainsnak"]["datavalue"]["value"]
unit = value.get("unit", "").rsplit("/", 1)[-1]
print(round(float(value["amount"]) * units.get(unit, 1.0), 2))
''', qid=m.group(1), prop=prop, units=units)


make = h_web
lesson = wikidata


def sample():
    """A task of this kind without the network: a known item stands in for the one Wikidata would draw."""
    return h_web(random.Random("sample:h_web"), pick=lambda cls, prop, links, seed: ("Q90", "Paris", "France"))

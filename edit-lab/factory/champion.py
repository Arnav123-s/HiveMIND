"""Muse's work — written by Muse, on Muse's side. Fable's
HiveMIND was read read-only; nothing on Fable's side was touched.

The persistent CHAMPION RECIPE (Fable-study Build 1, 2026-11-12).

Fable's principle (FABLE-STUDY-2026-11-11 §2.8 / Build 1): the
hive finds its own recipe; every founding is a one-gene
experiment; the recipe, not the body, is what gets selected. Our
cycle-3 head-to-head picks a recipe per target per cycle and then
forgets it. This module carries the winner ACROSS cycles:

  * The champion is a training recipe — the same knobs the
    head-to-head already varies (init source, fmode, hidden,
    lr_scale, full-budget epochs) — stored as versioned data in
    factory/champion_recipe.json.
  * Each growth cycle, ONE designated target trains two extra
    candidates at full budget: the champion as it stands, and a
    challenger that mutates exactly ONE gene of the champion.
  * The challenger becomes the new champion only if BOTH hold:
      - the challenger candidate is the attempt's BORN child
        (it passed the unchanged dual pristine gate — the
        champion machinery never judges births), and
      - its DEV-split accuracy beats the champion candidate's
        dev accuracy on the same target, same budget (positive
        dev margin). Held slices never select anything here;
        dev is the only selection surface, exactly as in the
        existing head-to-head.
  * The crown is applied by the cycle runner ONLY after the
    cycle's serving verification passes and births are kept —
    a rolled-back birth can never crown a recipe.
  * Every crown (and the seed) is appended to the record's
    history; the version increments per crown. Provenance also
    lands in the cycle JSON under attempts[].methods.champion
    and cycle["champion"].

Nothing in this module trains, judges, or serves. It is the
record and the rules for changing it — bookkeeping with a gate,
in the study's own words.
"""
from __future__ import annotations

import json
import os
import random
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

FACTORY_DIR = Path(__file__).parent
RECORD_PATH = FACTORY_DIR / "champion_recipe.json"

# The gene space: exactly the knobs today's recipe head-to-head
# varies (factory/growth.py recipes + the init grid), at the
# values those arms already use. epochs is the FULL-budget value
# the candidate retrains at, as in the head-to-head's winner.
GENES: Dict[str, List[Any]] = {
    "init_source": ["scratch", "parent"],
    "fmode": ["text", "code"],
    "hidden": [0, 4, 8],
    "lr_scale": [0.3, 1.0],
    "epochs": [300, 800],
}

# The seed champion: the head-to-head's most consistent dev
# winner on record — init-lr10, picked on the dev split for BOTH
# targets in cycle 4 (dev 0.8515 / 0.9828). fmode/hidden are
# carried genes; while init_source is "parent" they are inert
# (a parent-initialized candidate keeps the parent's own
# architecture), exactly as in the existing init recipes.
SEED_RECIPE: Dict[str, Any] = {"init_source": "parent",
                               "fmode": "text",
                               "hidden": 4,
                               "lr_scale": 1.0,
                               "epochs": 800}
SEED_ORIGIN = ("seeded 2026-11-12 from the cycle-4 recipe "
               "head-to-head winner init-lr10 (dev-picked for "
               "both targets); enters the same one-gene "
               "competition as any crowned champion")


def validate_recipe(recipe: Dict[str, Any]) -> Dict[str, Any]:
    """Fail-closed shape check: exactly the known genes, each
    with an allowed value. Returns the recipe unchanged."""
    if set(recipe) != set(GENES):
        raise ValueError(
            f"champion recipe genes {sorted(recipe)} != "
            f"{sorted(GENES)}")
    for gene, allowed in GENES.items():
        if recipe[gene] not in allowed:
            raise ValueError(
                f"champion gene {gene}={recipe[gene]!r} not in "
                f"{allowed}")
    return recipe


def seed_record() -> Dict[str, Any]:
    return {"kind": "champion_recipe",
            "version": 1,
            "recipe": dict(SEED_RECIPE),
            "origin": SEED_ORIGIN,
            "history": [{"version": 1, "event": "seeded",
                         "cycle_id": None,
                         "recipe": dict(SEED_RECIPE),
                         "origin": SEED_ORIGIN}],
            "stats": {"crowns": 0}}


def load_record(path: Optional[Path] = None) -> Dict[str, Any]:
    """The stored champion, or the seed record if none exists
    yet (loading never writes)."""
    path = Path(path) if path is not None else RECORD_PATH
    if path.exists():
        rec = json.loads(Path(path).read_text())
        if rec.get("kind") != "champion_recipe":
            raise ValueError(f"{path} is not a champion record")
        validate_recipe(rec["recipe"])
        return rec
    return seed_record()


def save_record(record: Dict[str, Any],
                path: Optional[Path] = None) -> None:
    """Atomic whole-record write (tmp + fsync + replace), the
    factory's whole-or-not-at-all discipline."""
    validate_recipe(record["recipe"])
    path = Path(path) if path is not None else RECORD_PATH
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w") as fh:
        json.dump(record, fh, indent=1, sort_keys=True)
        fh.write("\n")
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


def ensure_record(path: Optional[Path] = None) -> Dict[str, Any]:
    """Load the champion, writing the seed record first if the
    factory has none. Called by the cycle runner so the record
    exists as data from the first champion cycle on."""
    path = Path(path) if path is not None else RECORD_PATH
    if path.exists():
        return load_record(path)
    rec = seed_record()
    save_record(rec, path)
    return rec


def mutate(recipe: Dict[str, Any],
           rng: random.Random) -> Tuple[Dict[str, Any],
                                        Dict[str, Any]]:
    """One-gene mutation: exactly one gene changes, to a
    different allowed value. Deterministic in (recipe, rng)."""
    validate_recipe(recipe)
    gene = rng.choice(sorted(GENES))
    choices = [v for v in GENES[gene] if v != recipe[gene]]
    new_value = rng.choice(choices)
    mutant = dict(recipe)
    mutant[gene] = new_value
    return mutant, {"gene": gene, "from": recipe[gene],
                    "to": new_value}


def train_kwargs(recipe: Dict[str, Any], parent) -> Tuple[Dict[str, Any], str]:
    """Translate a recipe into (train_candidate kwargs, diet
    kind) in the head-to-head's own terms:
      init_source "parent"  -> init diet, init_from=parent,
                               lr_scale gene (fmode/hidden inert)
      init_source "scratch" -> child diet, fmode/hidden genes
                               (lr_scale inert, as in the
                               head-to-head's scratch recipe)"""
    validate_recipe(recipe)
    if recipe["init_source"] == "parent":
        return ({"init_from": parent,
                 "lr_scale": recipe["lr_scale"],
                 "epochs": int(recipe["epochs"])}, "init")
    return ({"fmode": recipe["fmode"],
             "hidden": int(recipe["hidden"]),
             "epochs": int(recipe["epochs"])}, "child")


def should_crown(*, mutant_born: bool,
                 dev_margin: Optional[float]) -> bool:
    """The crown rule, and nothing else: the mutant must be the
    born child of its attempt AND beat the champion candidate
    on the dev split (strictly positive margin)."""
    return bool(mutant_born) and dev_margin is not None \
        and dev_margin > 0


def crown(record: Dict[str, Any], *, cycle_id: str, target: str,
          mutant_recipe: Dict[str, Any],
          mutation: Dict[str, Any], dev_margin: float,
          champ_dev_acc: Optional[float],
          mutant_dev_acc: Optional[float]) -> Dict[str, Any]:
    """Return the record with the mutant crowned: version + 1,
    recipe replaced, history appended. Pure — the caller saves.
    The caller must already have applied should_crown()."""
    validate_recipe(mutant_recipe)
    rec = json.loads(json.dumps(record))
    rec["version"] = int(rec["version"]) + 1
    rec["recipe"] = dict(mutant_recipe)
    rec.setdefault("stats", {"crowns": 0})
    rec["stats"]["crowns"] = int(rec["stats"].get("crowns", 0)) + 1
    rec.setdefault("history", []).append(
        {"version": rec["version"], "event": "crowned",
         "cycle_id": cycle_id, "target": target,
         "mutation": mutation,
         "dev_margin": dev_margin,
         "champ_dev_acc": champ_dev_acc,
         "mutant_dev_acc": mutant_dev_acc,
         "recipe": dict(mutant_recipe)})
    return rec

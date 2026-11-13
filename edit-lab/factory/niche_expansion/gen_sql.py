"""Generator for the sql-statement subject (niche-expansion pick #3).

Muse's side, Hive growth department. Three DISJOINT template
partitions (train / screen=held-A / confirm=held-B): different
table/column pools AND different keyword casing per partition
(train shouts, screen title-cases, confirm whispers), crossed with
bands 1-3 (plain frame -> clause mixes -> case/whitespace and
tail variation).

Labels are PROVED at generation: coding/swarm/field2.py's
sql_statement_classifier must agree with the constructed label AND
the statement must EXPLAIN-compile against an in-memory sqlite3
database pre-seeded with every frame table. Items failing either
check are dropped with reasons counted, never fixed by hand.

Honest caveat (plan pick #3): the leading verb is a near-deterministic
signal, so this subject is expected to saturate; its value is niche
coverage and a served routing primitive, not difficulty.
"""
from __future__ import annotations

import random
import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

LAB_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(LAB_ROOT / "coding"))

from swarm import field2 as F2  # noqa: E402

CLASSES = ["select", "insert", "update", "delete", "create", "alter",
           "drop"]

# table -> columns, per partition (pools never cross over)
_POOLS = {
    "train": {
        "tables": {
            "users": ["id", "name", "age", "city"],
            "orders": ["id", "user_id", "total", "status"],
            "books": ["id", "title", "author", "year"],
        },
        "new_table": "loan_records",
        "new_col": "due_back",
        "rename_to": "users_archive",
        "case": "upper",
        "vals": ["'ada'", "'reno'", "'open'", "'dune'"],
        "nums": ["3", "7", "12", "40"],
    },
    "screen": {
        "tables": {
            "products": ["sku", "label", "price", "stock"],
            "tickets": ["code", "route", "fare", "gate"],
            "sensors": ["code", "reading", "unit", "station"],
        },
        "new_table": "repair_log",
        "new_col": "technician",
        "rename_to": "products_old",
        "case": "title",
        "vals": ["'anvil'", "'north'", "'grams'", "'pier'"],
        "nums": ["5", "9", "21", "63"],
    },
    "confirm": {
        "tables": {
            "trails": ["code", "title", "length_km", "surface"],
            "members": ["id", "nickname", "joined", "plan"],
            "vessels": ["name", "harbor", "berths", "kind"],
        },
        "new_table": "visit_notes",
        "new_col": "guide_name",
        "rename_to": "trails_backup",
        "case": "lower",
        "vals": ["'ridge'", "'mesa'", "'basic'", "'skiff'"],
        "nums": ["2", "8", "15", "30"],
    },
}

_ALL_TABLES: Dict[str, List[str]] = {}
for _p in _POOLS.values():
    _ALL_TABLES.update(_p["tables"])


def _seeded_db() -> sqlite3.Connection:
    con = sqlite3.connect(":memory:")
    for table, cols in _ALL_TABLES.items():
        con.execute(f"CREATE TABLE {table} ({', '.join(cols)})")
    return con


def _kw(pool, word: str) -> str:
    case = pool["case"]
    if case == "upper":
        return word.upper()
    if case == "title":
        return word.capitalize()
    return word.lower()


def _body(pool, cls, band, rng, variant):
    tables = list(pool["tables"].items())
    tname, cols = tables[variant % len(tables)]
    c = lambda i: cols[(variant + i) % len(cols)]  # noqa: E731
    val = pool["vals"][variant % len(pool["vals"])]
    num = pool["nums"][variant % len(pool["nums"])]
    K = lambda w: _kw(pool, w)  # noqa: E731

    if cls == "select":
        if band == 1:
            return f"{K('select')} {c(0)}, {c(1)} {K('from')} {tname} " \
                   f"{K('where')} {c(2)} = {val}"
        if band == 2:
            opts = [
                f"{K('select')} {c(0)}, {K('count')}(*) {K('from')} {tname} "
                f"{K('group by')} {c(0)}",
                f"{K('select')} * {K('from')} {tname} {K('order by')} "
                f"{c(1)} {K('limit')} {num}",
                f"{K('select distinct')} {c(3)} {K('from')} {tname}",
            ]
            return opts[variant % len(opts)]
        opts = [
            f"{K('select')} {c(1)} {K('from')} {tname} {K('where')} "
            f"{c(2)} {K('in')} ({val}, {pool['vals'][(variant + 1) % 4]}) "
            f"{K('order by')} {c(1)} {K('limit')} 5",
            f"{K('select')} {c(0)} {K('from')} {tname} {K('where')} "
            f"{c(1)} {K('is not null')}",
            f"{K('select')}  {c(0)} ,  {c(2)}   {K('from')}   {tname}",
        ]
        return opts[variant % len(opts)]

    if cls == "insert":
        if band == 1:
            return f"{K('insert into')} {tname} ({c(0)}, {c(1)}) " \
                   f"{K('values')} ({num}, {val})"
        if band == 2:
            return f"{K('insert into')} {tname} ({c(0)}, {c(1)}, {c(2)}) " \
                   f"{K('values')} ({num}, {val}, {num}), " \
                   f"({int(num) + 1}, {val}, {num})"
        return f"{K('insert into')} {tname} {K('values')} " \
               f"({num}, {val}, {num}, {val})"

    if cls == "update":
        if band == 1:
            return f"{K('update')} {tname} {K('set')} {c(1)} = {val} " \
                   f"{K('where')} {c(0)} = {num}"
        if band == 2:
            opts = [
                f"{K('update')} {tname} {K('set')} {c(1)} = {val}, "
                f"{c(2)} = {num} {K('where')} {c(0)} = {num}",
                f"{K('update')} {tname} {K('set')} {c(3)} = {val}",
            ]
            return opts[variant % len(opts)]
        return f"{K('update')} {tname} {K('set')} {c(2)} = {num} " \
               f"{K('where')} {c(1)} {K('in')} ({val})"

    if cls == "delete":
        if band == 1:
            return f"{K('delete from')} {tname} {K('where')} {c(0)} = {num}"
        if band == 2:
            opts = [
                f"{K('delete from')} {tname} {K('where')} {c(1)} = {val}",
                f"{K('delete from')} {tname}",
            ]
            return opts[variant % len(opts)]
        return f"{K('delete from')} {tname} {K('where')} {c(2)} " \
               f"{K('between')} {num} {K('and')} {int(num) + 10}"

    if cls == "create":
        nt = pool["new_table"]
        if band == 1:
            return f"{K('create table')} {nt} ({c(0)} {K('integer')}, " \
                   f"{c(1)} {K('text')})"
        if band == 2:
            return f"{K('create table if not exists')} {nt} " \
                   f"({c(0)} {K('integer primary key')}, {c(1)} {K('text')}, " \
                   f"{c(2)} {K('integer')})"
        return f"{K('create table')} {nt} ({c(1)} {K('text')}, " \
               f"{c(2)} {K('integer default')} 0, {c(3)} {K('text')})"

    if cls == "alter":
        nc = pool["new_col"]
        if band == 1:
            return f"{K('alter table')} {tname} {K('add column')} {nc} " \
                   f"{K('text')}"
        if band == 2:
            return f"{K('alter table')} {tname} {K('rename to')} " \
                   f"{pool['rename_to']}"
        return f"{K('alter table')} {tname} {K('add column')} {nc} " \
               f"{K('integer default')} 1"

    # drop
    if band == 1:
        return f"{K('drop table')} {tname}"
    if band == 2:
        return f"{K('drop table if exists')} {tname}"
    return f"{K('drop table')}  {tname} ;".replace(" ;", ";")


# ------------------------------------------------------------ oracle
def verify_item(text: str, label: str) -> Optional[str]:
    """None to keep, else the drop reason."""
    cls = F2.sql_statement_classifier({"sql": text})
    if not cls.get("ok") or str(cls.get("output")).lower() != label:
        return f"classifier_says_{cls.get('output')}_want_{label}"
    con = _seeded_db()
    try:
        con.execute("EXPLAIN " + text)
    except Exception as e:  # noqa: BLE001
        return f"explain_failed_{type(e).__name__}"
    finally:
        con.close()
    return None


# ------------------------------------------------------------ pools
def _pool(partition: str, band_counts: Dict[int, int], seed: int,
          group_prefix: str):
    pool = _POOLS[partition]
    items: List[Dict[str, Any]] = []
    stats: Dict[str, Any] = {"families": 0, "drops": {}}
    rng = random.Random(seed)
    for band in (1, 2, 3):
        count = band_counts.get(band, 0)
        for cls in CLASSES:
            for i in range(count):
                variant = i + (band - 1) * 5 + CLASSES.index(cls)
                text = _body(pool, cls, band, rng, variant)
                stats["families"] += 1
                gid = f"{group_prefix}:{partition}-b{band}-{cls}-{i}"
                reason = verify_item(text, cls)
                if reason is not None:
                    key = reason.rsplit("_want_", 1)[0]
                    stats["drops"][key] = stats["drops"].get(key, 0) + 1
                    continue
                items.append({"text": text, "label": cls, "group": gid,
                              "band": band, "family": cls})
    stats["items"] = len(items)
    return items, stats


def gen_pool(band_counts, seed, group_prefix="train"):
    return _pool("train", band_counts, seed, group_prefix)


def gen_screen_pool(band_counts, seed, group_prefix="screen"):
    return _pool("screen", band_counts, seed, group_prefix)


def gen_confirm_pool(band_counts, seed, group_prefix="confirm"):
    return _pool("confirm", band_counts, seed, group_prefix)


DEFAULT_TRAIN_BANDS = {1: 14, 2: 14, 3: 12}
DEFAULT_HELD_BANDS = {1: 6, 2: 6, 3: 6}


def gen_train(seed: int = 301):
    return gen_pool(DEFAULT_TRAIN_BANDS, seed, "train")


def gen_held_a(seed: int = 302):
    return gen_screen_pool(DEFAULT_HELD_BANDS, seed, "screen")


def gen_held_b(seed: int = 303):
    return gen_confirm_pool(DEFAULT_HELD_BANDS, seed, "confirm")

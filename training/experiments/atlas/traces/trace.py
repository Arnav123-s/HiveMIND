"""Opt-in experiment compiling repeated kilogram-to-depot side exits into one checked WASI program."""
import contextlib
import hashlib
import json
import re
import sqlite3
import time
from pathlib import Path

from team import saved, skill_inputs
from training.experiments.fieldwork import work

MASS = r"(?:0|[1-9][0-9]{0,3})(?:\.[0-9]{1,3})?"
ITEM = rf"{MASS} kg"
REQUEST = re.compile(rf"Calculate the depot shipping fee for (?P<items>{ITEM}(?: and {ITEM}){{0,15}})"
                     r"(?: using (?P<mode>per-parcel|pooled) rounding)?[?.]?", re.I | re.ASCII)
BRANCH = "depot_kg_trace"


def serial(x):
    return json.dumps(x, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(x):
    return hashlib.sha256(serial(x).encode()).hexdigest()


def grams(items):
    if type(items) is not list or not 1 <= len(items) <= 16:
        raise ValueError("expected one to sixteen decimal kilogram strings")
    values = []
    for item in items:
        if type(item) is not str or not re.fullmatch(MASS, item, re.ASCII):
            raise ValueError("expected positive, plain decimal kilograms at whole-gram precision")
        whole, _, fraction = item.partition(".")
        value = int(whole) * 1000 + int(fraction.ljust(3, "0"))
        if not 1 <= value <= 1_000_000:
            raise ValueError("parcel mass out of range")
        values.append(value)
    return values


def bind(message):
    if not isinstance(message, str) or len(message) > 32768:
        return None
    matched = REQUEST.fullmatch(message.strip())
    if not matched:
        return None
    items = [v.split()[0] for v in matched['items'].lower().split(' and ')]
    try:
        values = grams(items)
    except ValueError:
        return None
    return items, values, (matched['mode'] or '').lower()


def canonical(values, mode):
    request = 'Calculate the depot shipping fee for ' + ' and '.join(f'{v} g' for v in values)
    return request + (f' using {mode} rounding' if mode else '')


def sibling(parent):
    # The parent is copied verbatim and executed only within CPython WASI. The residual
    # validates its own boundary even if called directly through the sibling's JSON API.
    return parent['source'] + f'''

_trace_parent = solve
import re as _trace_re

def solve(x):
    if type(x) is not dict or set(x) != {{'kg'}} or type(x['kg']) is not list or not 1 <= len(x['kg']) <= 16:
        raise ValueError('expected bounded kilogram list')
    values = []
    for mass in x['kg']:
        if type(mass) is not str or not _trace_re.fullmatch({MASS!r}, mass, _trace_re.ASCII):
            raise ValueError('invalid kilogram value')
        whole, _, fraction = mass.partition('.')
        value = int(whole + fraction.ljust(3, '0'))
        if not 1 <= value <= 1000000:
            raise ValueError('kilogram value outside supported range')
        values.append(value)
    return _trace_parent({{'grams': values}})
'''


class MeasuredGuest:
    def __init__(self, guest):
        self.guest = guest
        self.calls = self.inputs = self.fuel = 0

    def run(self, source, inputs, **kwargs):
        self.calls += 1
        self.inputs += len(inputs)
        results, fuel, seconds = self.guest.run(source, inputs, **kwargs)
        self.fuel += fuel
        return results, fuel, seconds


class GuardedTrace:
    def __init__(self, *, sibling_bank, bank=None, guest=None):
        self.bank = saved.bank_path() if bank is None else Path(bank)
        self.shelf = Path(sibling_bank)
        self.guest = MeasuredGuest(guest if guest is not None else saved.guest())
        if self.guest.guest is None:
            raise ValueError('this experiment requires the real fieldwork WASI runner')
        self.shelf.mkdir(parents=True, exist_ok=True)
        self.last = {}

    @contextlib.contextmanager
    def ledger(self):
        with contextlib.closing(sqlite3.connect(self.shelf/'exits.sqlite3', timeout=30)) as db, db:
            db.execute('CREATE TABLE IF NOT EXISTS exits(slot TEXT, sample TEXT, receipt TEXT, PRIMARY KEY(slot,sample))')
            yield db

    def _parent(self, mode):
        rows = [r for r in work.load_bank(self.bank) if r['task'] == saved.SHIPPING[0]]
        if len(rows) != 1 or rows[0]['description'] != saved.SHIPPING[1]:
            return None, None
        row, = rows
        return row, digest(['depot-kg-v1', row, mode])

    def _sibling(self, parent, slot):
        candidate = work.fingerprint(sibling(parent))
        return next((r for r in work.load_bank(self.shelf) if r['task'] == BRANCH and r.get('slot') == slot
                     and r['digest'] == candidate and r.get('parent') == parent['digest'] and r['validation'] >= 4
                     and r.get('gate') and r.get('exits') == 3), None)

    def answer(self, message, *, mode='guarded'):
        if mode not in {'stock','handwritten','guarded'}:
            raise ValueError('unknown comparison arm')
        start = time.perf_counter()
        calls, inputs, fuel = self.guest.calls, self.guest.inputs, self.guest.fuel
        path = 'stock'
        try:
            original = saved.answer(message, bank=self.bank, runner=self.guest)
            parsed = bind(message) if mode != 'stock' and original is None else None
            if parsed is None:
                return original
            items, values, convention = parsed
            parent, slot = self._parent(convention)
            checked = self._sibling(parent, slot) if parent and mode == 'guarded' else None
            if checked:
                _, invalid = saved._json_input(serial({'grams':values}), [parent], saved.SHIPPING)
                if not invalid:
                    call = f"run {BRANCH}@{work.contract_id(checked)}: " + serial({'kg':items})
                    result = saved.answer(call, bank=self.shelf, runner=self.guest)
                    if result and result.get('status') == 'answered' and self._parent(convention)[1] == slot:
                        path = 'sibling'
                        return result
            path = 'handwritten' if mode == 'handwritten' else 'side_exit'
            receipt = saved.answer(canonical(values,convention), bank=self.bank, runner=self.guest)
            if (mode == 'guarded' and parent and receipt and receipt.get('status') == 'answered'
                    and receipt.get('methods') == [parent['digest']] and self._parent(convention)[1] == slot):
                out = {'input': values, 'value': receipt['value'], 'parent': parent['digest'], 'convention':convention}
                with self.ledger() as db:
                    db.execute('INSERT OR IGNORE INTO exits SELECT ?,?,? WHERE (SELECT count(*) FROM exits WHERE slot=?) < 3',
                               (slot, digest(values), serial(out), slot))
            return receipt
        finally:
            self.last = dict(path=path, calls=self.guest.calls-calls, guest_inputs=self.guest.inputs-inputs,
                             fuel=self.guest.fuel-fuel, seconds=time.perf_counter()-start, model_calls=0)

    def qualify(self, message, examples):
        """An outside checker supplies reserved outputs. Never derive these labels from the parent or fit."""
        parsed = bind(message)
        if not parsed:
            return {'status':'unsupported'}
        parent, slot = self._parent(parsed[2])
        if not parent:
            return {'status':'unresolved_parent'}
        with self.ledger() as db:
            exits = dict(db.execute('SELECT sample, receipt FROM exits WHERE slot=?', (slot,)))
        if len(exits) < 3:
            return {'status':'collecting','distinct_exits':len(exits)}
        try:
            if not isinstance(examples, list) or not 4 <= len(examples) <= 256 or any(type(r['output']) is not int for r in examples):
                raise ValueError()
            keys = [digest(grams(r['input'])) for r in examples]
        except (KeyError, TypeError, ValueError):
            return {'status':'invalid_gate'}
        if set(keys) & set(exits) or len(set(keys)) != len(keys):
            return {'status':'overlapping_gate'}
        probes = [dict(input={'kg':r['input']}, output=r['output']) for r in examples]
        source = sibling(parent)
        passed, _ = work.check(self.guest, source, probes, explain=False)
        if passed != len(probes) or self._parent(parsed[2])[1] != slot:
            return {'status':'unqualified','passed':passed,'count':len(probes)}
        row = dict(task=BRANCH, description=f'Guarded kilogram input for saved depot contract {slot}.',
                   source=source, digest=work.fingerprint(source), validation=passed, parent=parent['digest'], slot=slot,
                   gate=digest(probes), exits=3, exit_receipts=[json.loads(exits[k]) for k in sorted(exits)],
                   input_contract=skill_inputs.infer_contract([r['input'] for r in probes]))
        work.admit(self.shelf, row)
        return {'status':'published','count':passed,'digest':row['digest'],'parent':row['parent'],'gate':row['gate']}

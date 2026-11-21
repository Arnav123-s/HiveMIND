import json
from pathlib import Path

import pytest

from training import exam, grow, hint_dream as hd
from training.experiments.hint_dream.independent import streaming


def test_independent_streaming_implementation_matches_each_sealed_oracle():
    specs = list(hd.draw(5757, 16))
    assert {(s.form, s.rule) for s in specs} == {(f, r) for f in hd.FORMATS for r in hd.RULES}
    assert specs == list(hd.draw(5757, 16)) and specs != list(hd.draw(5758, 16))
    for spec in specs:
        for suite in ('visible', 'check', 'audit'):
            for data, answer in hd.examples(spec, suite):
                assert streaming(spec, data) == answer


class ReplayGuest:
    def __init__(self, spec):
        self.spec = spec

    def run(self, program, data):
        # Replay only fixture verdicts. Native integration uses the isolated WASI Guest.
        return [{'value': streaming(self.spec, x) if 'checked' in program else None} for x in data], 0, 0


@pytest.mark.parametrize('blind,hinted,want,calls', [(False, True, True, 2), (True, False, False, 1), (False, False, False, 2)])
def test_admits_only_blind_failures_and_removes_private_context(blind, hinted, want, calls):
    spec = next(hd.draw(54, 1))
    prompt, hint = hd.instructions(spec)
    asked = []
    def ask(member, ms, **kwargs):
        asked.append(ms)
        return 'def solve(x): return ' + ('"checked"' if (blind, hinted)[len(asked) - 1] else 'None')
    row, audit = hd.trial(spec, 'test', ask, ReplayGuest(spec))
    assert len(asked) == calls and bool(row) == want
    if want:
        assert audit['hinted']['matched'] == 24 and row['messages'] == hd.messages(prompt)
        assert hint not in json.dumps(row) and 'audit' not in row


def test_enabled_entrypoint_reaches_gather_and_accounts_for_one_slot(tmp_path, monkeypatch):
    monkeypatch.setenv('HIVE_SPADE_DREAM', '1')
    monkeypatch.setattr(exam, 'RUNS', tmp_path / 'receipts')
    spec = next(hd.draw(4, 1))
    def fake_paired_process(command, **kwargs):
        assert command[2:4] == ['training.hint_dream', '4'] and kwargs['timeout'] <= 600
        replies = iter(['def solve(x): return None', 'def solve(x): return "checked"'])
        row, audit = hd.trial(spec, 'fixture', lambda *a, **k: next(replies), ReplayGuest(spec))
        Path(command[-1]).write_text(json.dumps({'status':'checked', 'calls':2, 'audit':audit, 'row':row}))
    monkeypatch.setattr(hd.subprocess, 'run', fake_paired_process)
    out = tmp_path / 'new' / 'rows.jsonl'
    result = grow.dream(4, 3, tmp_path / 'absent.jsonl', out)
    assert result['tasks'] == result['rows'] == result['right'] == 1
    assert result['generated']['model_calls'] == 2
    combined = tmp_path / 'joined.jsonl'
    assert grow.gather(combined, 'g58', new=[out, out]) == (0, 1)
    got = json.loads(combined.read_text())
    assert got['gen'] == 'g58' and hd.instructions(spec)[1] not in json.dumps(got)
    assert json.loads(next((tmp_path / 'receipts').rglob('hint-regret.json')).read_text())['admitted']


def test_deadline_and_unavailable_guest_do_not_admit(tmp_path, monkeypatch):
    from team import saved, ternary
    monkeypatch.setattr(saved, 'guest', lambda: None)
    monkeypatch.setattr(ternary, 'roster', lambda: [])
    out = tmp_path / 'child.json'
    hd._attempt(7, out)
    assert json.loads(out.read_text())['status'] == 'unavailable'
    summary = hd.run_slot(7, tmp_path / 'rows.jsonl', tmp_path / 'report.json', 1)
    assert summary['rows'] == summary['model_calls'] == 0
    assert not (tmp_path / 'rows.jsonl').exists()


def test_desktop_dream_uses_same_gate_and_preserves_remaining_rehearsals(tmp_path, monkeypatch):
    from team import dream as local
    monkeypatch.setenv('HIVE_SPADE_DREAM', '1')
    monkeypatch.setattr(grow, 'GROW', tmp_path / 'grow')
    monkeypatch.setattr(exam, 'RUNS', tmp_path / 'runs')
    monkeypatch.setattr(local, 'distil', lambda log: None)
    monkeypatch.setattr(local, 'lessons', lambda log: None)
    monkeypatch.setattr(local.memory, 'log_dream', lambda log: None)
    rehearsed = []
    monkeypatch.setattr(local, 'rehearse', lambda log, n: rehearsed.append(n))
    monkeypatch.setattr(hd, 'run_slot', lambda seed, out, receipt, end: {'tasks':1, 'rows':0})
    report = local.dream(train=False, rehearse_n=2)
    assert rehearsed == [1] and report['generated']['tasks'] == 1


def test_private_format_or_rule_prose_in_source_is_ineligible():
    spec = next(hd.draw('privacy', 1))
    _, rule_hint = hd.instructions(spec)
    for private in [rule_hint, hd.decoding_hint(spec.form)]:
        replies = iter(['def solve(x): return None', f'# {private}\ndef solve(x): return "checked"'])
        row, grades = hd.trial(spec, 'fixture', lambda *a, **k: next(replies), ReplayGuest(spec), format_hint=True)
        assert grades['hinted']['ok'] and row is None


def test_both_production_arms_use_same_memory_recalled_only_from_public_task(tmp_path, monkeypatch):
    from team import engram, saved, ternary
    seed = '30005652'
    spec = next(hd.draw(seed, 1))
    memories = [('old-skill', 0.75)]
    recalled, applied = [], []
    monkeypatch.setenv('HIVE_ENGRAMS', '1')
    monkeypatch.setenv('HIVE_ENGRAM_GATE', '1')
    monkeypatch.setattr(saved, 'guest', lambda: ReplayGuest(spec))
    monkeypatch.setattr(ternary, 'roster', lambda: ['t80+g55trunk'])
    monkeypatch.setattr(engram, 'recall_scaled', lambda prompt, base, cell: recalled.append(prompt) or memories)
    def answer(member, msgs, *, also, **kwargs):
        applied.append(also)
        return 'def solve(x): return None' if len(applied) == 1 else 'def solve(x): return "checked"'
    monkeypatch.setattr(ternary, 'chat', answer)
    path = tmp_path / 'result.json'
    hd._attempt(seed, path)
    result = json.loads(path.read_text())
    assert recalled == [hd.instructions(spec)[0]] and applied == [tuple(memories)] * 2
    assert result['row']['seed'] == 30005652 and result['row']['spec_id'] == spec.seed
    assert result['row']['verified_member'] and result['audit']['recalled'] == [list(memories[0])]


def test_frozen_native_training_and_transfer_receipts_are_disjoint():
    from training.experiments.hint_dream import fit, pilot
    evidence = Path(pilot.__file__).parent / 'evidence'
    assert [fit.checked_rows(evidence / arm)[1] for arm in ('initial', 'confirmation')] == [1, 3]
    trained = pilot.scheduled('trained')
    transfer = pilot.scheduled('transfer')
    assert len(trained) == 4 and len(transfer) == 3
    assert {(s.form, s.rule) for s in trained}.isdisjoint((s.form, s.rule) for s in transfer)
    pilot.check_transfer_manifest(transfer)
    with pytest.raises(ValueError):
        fit.checked_rows(evidence / 'transfer-parent')

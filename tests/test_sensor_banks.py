import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from team import sensor_banks, talk


REQUEST = 'Check sensor banks [2,1,0,7] and [0,2,0,0]'


def test_archive_sender_disagreement_is_disclosed_and_corrected(monkeypatch):
    monkeypatch.setattr(talk, 'saved_reply', lambda *args, **kwargs: None)
    monkeypatch.setattr(talk, 'speaker', lambda: pytest.fail('sensor requests must work without a body'))
    result = talk.reply(REQUEST)
    observed = result['sensor_banks']
    assert result['agreed'] and result['files'] == []
    assert observed['measurements'] == ['3', '-2']
    assert observed['codes'] == [0, 0]
    assert observed['pair_predictions'] == [True, False] and not observed['pair_agrees']
    assert observed['different_positivity'] and observed['positive_sum']
    assert 'corrected' in result['text']


def test_explicit_packet_is_required_and_invalid_packets_get_feedback():
    for text in ('Check my sensor banks', 'Check sensor banks in the kitchen', 'Explain [1,2,3,4] and [4,3,2,1]'):
        assert sensor_banks.answer(text) is None
    for block in ('[1,2,3]', '[true,2,3,4]', '[NaN,1,2,3]', '[1e999999,2,3,4]',
                  '[1e-13,2,3,4]', '[1,[2],3,4]', '[1,2,3,4]' + ' ' * 520):
        out = sensor_banks.answer('Check sensor banks ' + block + ' and [4,3,2,1]')
        assert not out['agreed'] and out['sensor_banks']['status'] == 'invalid'


def test_precise_cancellation_and_raw_only_available(monkeypatch,tmp_path):
    monkeypatch.setattr(sensor_banks, 'ASSET', tmp_path/'absent')
    sensor_banks._model.cache_clear()
    result = sensor_banks.answer('Check sensor banks [999999999999,1e-12,999999999999,9] and [0,0,0,8]')
    observed = result['sensor_banks']
    assert observed['mode'] == 'raw_only' and observed['pair_agrees'] is None
    assert observed['measurements'] == ['0.000000000001','0']
    assert observed['different_positivity'] and observed['positive_sum']
    assert 'unavailable' in result['text']


def test_user_saved_method_retains_precedence(monkeypatch):
    saved = {'saved': {'status':'answered'}, 'agreed': True}
    monkeypatch.setattr(talk, 'saved_reply', lambda *args,**kwargs: saved)
    assert talk.reply(REQUEST) is saved


def test_normal_cli_and_hosted_thread_work_without_numpy_or_torch(tmp_path):
    root=Path(__file__).resolve().parents[1]
    env={**os.environ,'HIVE_PYTHON':sys.executable,'HIVE_BANK':str(tmp_path/'empty')}
    env.pop('HIVE_ROLES', None)
    out=subprocess.run([str(root/'hive'),'--once',REQUEST],env=env,text=True,capture_output=True,check=True)
    assert 'Four-bit codes 0 and 0' in out.stdout and 'corrected' in out.stdout
    # -S removes installed site-packages. This exercises the no-model hosted workflow.
    thread=tmp_path/'thread.json'; dest=tmp_path/'reply.md'
    thread.write_text(json.dumps({'messages':[{'role':'user','content':REQUEST}]}))
    subprocess.run([sys.executable,'-S','-m','team.talk','--thread',str(thread),'--saved-only','--out',str(dest)],
                   env=env,cwd=root,text=True,capture_output=True,check=True)
    assert 'Local sensor-bank check' in dest.read_text()
    assert 'two members agreed' not in dest.read_text()

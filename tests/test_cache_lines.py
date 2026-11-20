import json
import sys
from pathlib import Path
import os
import subprocess

import pytest

from team import cache_lines, solo, talk


def request(size, address, width):
    return (f'With aligned {size}-byte cache lines, a {width}-byte read starts at address {address}. '
            'How many distinct lines does the access touch? Reply with just the integer.')


def test_counts_match_an_independent_byte_by_byte_enumeration():
    for size in (1, 3, 8, 16, 63, 64, 128):
        for start in (0, 1, size - 1, size, size + 1, 257, 0xfeed):
            for width in (1, 2, size, size + 1, 2 * size, 3 * size + 1):
                indices = {byte // size for byte in range(start, start + width)}
                reply = cache_lines.answer(request(size, hex(start), width))
                assert reply['text'] == str(len(indices))
                assert reply['cache_lines']['first_line'] == min(indices)
                assert reply['cache_lines']['last_line'] == max(indices)


@pytest.mark.parametrize('bad', [
    request('six or eight', 8, 1), request(-8, 24, 1), request(8, '0xzz', 1), request(8, 24, 0),
    request(8, '0xffffffffffffffff', 2), request(8, 24, 1).replace('aligned ', ''),
    request(8, 24, 3).replace('aligned', 'misaligned'), request(8, '11.5', 3),
    request(8, 24, 3).replace('read', 'strided read'), request(8, 24, 3).replace('read', 'noncontiguous read'),
    request(8, 24, 3).replace('aligned 8-byte cache lines', '8-byte cache lines aligned on 4-byte boundaries'),
    request(8, 24, 3).replace('touch?', 'touch, and what are the possible misses?'),
    request(8, 24, 3).replace('a 3-byte', 'a 3-bit'), 'Describe cache lines and typical line sizes.',
])
def test_ineligible_requests_do_not_claim_a_checked_result(bad):
    assert cache_lines.answer(bad) is None


def test_normal_cli_thread_footer_and_saved_precedence(tmp_path, monkeypatch):
    task = request(16, '0x1f', 16)
    monkeypatch.setattr(talk, 'speaker', lambda: pytest.fail('should not need native inference'))
    monkeypatch.setenv('HIVE_BANK', 'off')
    assert talk.reply(task)['text'] == '2'
    saved = {'text': 'user-defined method', 'saved': {'status':'answered'}}
    monkeypatch.setattr(talk, 'saved_reply', lambda *args, **kwargs: saved)
    assert talk.reply(task) is saved
    root = Path(__file__).resolve().parents[1]
    env = {**os.environ, 'HIVE_PYTHON': sys.executable}
    value = subprocess.run([str(root/'hive'), '--once', task], cwd=root, env=env, text=True, capture_output=True, check=True)
    assert value.stdout.strip() == '2'
    thread, response = tmp_path/'thread.json', tmp_path/'reply.md'
    thread.write_text(json.dumps({'messages':[{'role':'user','content':task}]}))
    subprocess.run([sys.executable, '-S', '-m', 'team.talk', '--thread', str(thread), '--saved-only', '--out', str(response)],
                   env=env, cwd=root, capture_output=True, check=True)
    assert response.read_text().startswith('2\n') and 'Local cache-line calculation' in response.read_text()


def test_printing_the_same_wrong_constant_cannot_win_solo(tmp_path, monkeypatch):
    def members(task, number, board, guard, work, temperature, who, also):
        work.mkdir(parents=True, exist_ok=True)
        return dict(answer='1', program='print(1)', who=who)
    monkeypatch.setattr(solo, 'member', members)
    monkeypatch.setenv('HIVE_SIGNALS', '0')
    monkeypatch.setenv('HIVE_ENGRAMS', '0')
    out = solo.first(request(16, 15, 3), tmp_path, members=2)
    decision = json.loads((tmp_path/'members/members.json').read_text())
    assert not out['agreed'] and not decision['agreeing'] and decision['cache_line_check']['count'] == 2
    pair = [{'answer':'2'}, {'answer':'2 cache lines'}]
    assert solo.agreeing(pair, request(16, 15, 3)) == [tuple(pair)]
    wrong = [{'answer':'1'}, {'answer':'1'}]
    assert solo.agreeing(wrong, 'Return one as a digit.') == [tuple(wrong)]

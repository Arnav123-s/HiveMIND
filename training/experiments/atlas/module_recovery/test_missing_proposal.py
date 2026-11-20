"""New input-boundary regression. No worker code or WebAssembly is executed in this test."""
from training.experiments.atlas.module_recovery import recover


def test_missing_worker_source_does_not_abort_the_next_check(tmp_path):
    class FailingGuest:
        def run(self, program, inputs):
            assert 'def to_seconds' in program
            return [{'error':'worker program failed'} for _ in inputs], 0, 0.0

    question = recover.SPEC + "to_seconds('5m') and of to_text(1)."
    next_source = 'def to_seconds(s): return 9\ndef to_text(n): return "wrong"\n'
    result = recover.recover(question, True, [('missing',None),('next',next_source)], FailingGuest(), tmp_path/'out')
    assert result['delivered'] is False
    assert [(t['program'],t['passed']) for t in result['trials']] == [('next',False)]
    assert not (tmp_path/'out').exists()

import pytest

from team import engram, talk, ternary
from team.water_phase import equilibrium_phase


@pytest.mark.parametrize(("message", "expected"), [
    ("Pure water at 1 atm and −23 °C", "solid"),
    ("At one atmosphere the pure water is at minus 8 degrees Celsius.", "solid"),
    ("Pure water at negative twenty-three degrees Celsius and standard atmospheric pressure", "solid"),
    ("Water at 72 C and 1 atm", "liquid"),
    ("Pure water at +123°C and 1.0 atmosphere", "gas"),
])
def test_unambiguous_equilibrium_states(message, expected):
    assert equilibrium_phase(message) == expected


@pytest.mark.parametrize("conditions", [
    "pure water at -0.1°C and 1 atm", "water at 100.09 C and 1 atm", "water at 99.9 C and 1 atm",
    "water at 27 C and 0.1 atm", "water at 45 C near sea level", "water at 27 C at 1 atm or under vacuum",
    "water at 108 C and a gauge pressure of 1 atm", "water at 108 C and twice standard atmospheric pressure",
    "salt water at -7 C and 1 atm", "water with glycerol at 27 C and 1 atm", "supercooled water at -4 C and 1 atm",
    "water at thirty or forty degrees Celsius and one atmosphere", "water at one hundred ten Celsius and one atmosphere",
    "water at 30–40 C and 1 atm", "water between 20 and 30 C at 1 atm", "water above 20 C at 1 atm",
    "water at 21 C and 1 atm but not at equilibrium", "water at 27°F and 1 atm", "water at 3000 C and 1 atm",
])
def test_scoped_exercise_declines_other_conditions(conditions):
    assert equilibrium_phase(conditions) is None


def test_registered_label_head_checks_same_scope_before_applying_weights(tmp_path, monkeypatch):
    monkeypatch.setattr(ternary, "ENGRAMS", tmp_path)
    monkeypatch.delenv("HIVE_ENGRAMS", raising=False)
    row = dict(name="phase_v2", dna="t80", domain="physical_science", task="Water phase", form="label",
               skill_id="water_phase", verified=True, instruction="Choose the phase.",
               labels=["solid", "liquid", "gas"], cues=["water"])
    engram.update_index(lambda records: [row], home=tmp_path)
    (tmp_path / "t80+phase_v2.gguf").touch()
    def selected(conditions):
        return engram.for_request("Choose solid, liquid, or gas for " + conditions, "t80", domain="physical_science")
    assert selected("pure water at 72 °C and 1 atm") == ("phase_v2",)
    assert selected("pure water at minus twenty °C and one atmosphere") == ("phase_v2",)
    assert selected("pure water at 100 °C and 1 atm") == ()
    assert selected("pure water at 72 °C and either 1 atm or 3 atm") == ()
    assert selected("salt water at 72 °C and 1 atm") == ()

    monkeypatch.setenv("HIVE_SIGNALS", "0")
    monkeypatch.setenv("HIVE_BANK", "off")
    monkeypatch.setattr(talk, "route", lambda base, msg, history: ("talk", [{"role":"user", "content": msg}]))
    def fake_native(base, messages, **options):
        if options.get("also"):
            return "Gas."
        assert "equilibrium check" in messages[0]["content"] and "gives liquid" in messages[0]["content"]
        return "The water is liquid."
    monkeypatch.setattr(ternary, "chat", fake_native)
    out = talk.reply("At one atmosphere, what phase is pure water at 72 C?", base="t80")
    receipt = out["engram_advice"]
    assert out["text"] == "The water is liquid." and receipt["model_reply"] == "Gas."
    assert receipt["checked_phase"] == "liquid" and not receipt["accepted"]


PHASE_QUESTION = 'At one atmosphere, what phase is pure water at 72 degrees Celsius? Answer in one short sentence.'


@pytest.mark.parametrize('message,expected', [
    (PHASE_QUESTION, 'liquid'),
    ('What state is pure water at 1 atm and −8°C? Reply with one word.', 'solid'),
    ('At one atmosphere and 165 C, choose solid, liquid, or gas for pure water.', 'gas'),
    (PHASE_QUESTION.replace('72', '100'), None),
    (PHASE_QUESTION.replace('pure water', 'salt water'), None),
    (PHASE_QUESTION.replace('one atmosphere', 'a gauge pressure of 1 atm'), None),
    (PHASE_QUESTION + ' Save a description to the file water.md.', None),
    (PHASE_QUESTION + ' Also give the temperature in kelvins.', None),
    (PHASE_QUESTION + ' Discuss density in the same sentence.', None),
    ('Write Python code to classify the phase of pure water at 43 C and 1 atm.', None),
    (PHASE_QUESTION.replace('pure water', 'water with an unknown dissolved solute'), None),
    ('Which phase applies to the salt? Pure water at 50 C and one atmosphere is nearby.', None),
])
def test_only_an_atomic_water_phase_question_has_a_checked_answer(message, expected):
    from team.water_phase import standalone_phase
    assert standalone_phase(message) == expected
    assert standalone_phase(message, [{'role':'user', 'content':'We use our own phase names.'}]) is None


@pytest.mark.parametrize('way,head,output,source', [
    ('work', 'At', None, 'equilibrium_rule'), ('work', 'gas', None, 'equilibrium_rule'),
    ('work', 'liquid', None, 'checked_native_label'), ('talk', 'gas', 'It is gas.', 'equilibrium_rule'),
    ('talk', 'liquid', 'The water is liquid.', 'checked_native_answer'),
])
def test_preserves_native_phase_attempt_and_records_the_actual_source(monkeypatch,way,head,output,source):
    from team import domain_advice
    monkeypatch.setenv('HIVE_SIGNALS','0')
    monkeypatch.setenv('HIVE_BANK','off')
    monkeypatch.setattr(talk, 'route',lambda *args:(way,[{'role':'user','content':PHASE_QUESTION}]))
    row={'name':'water-test','labels':['solid','liquid','gas']}
    monkeypatch.setattr(domain_advice,'consult',lambda msg,base,domain,system,**kwargs:
                        domain_advice._query(base,system,msg,row,'water_phase',expected='liquid'))
    calls=[]
    def native(base,messages,**kwargs):
        calls.append(kwargs)
        return head if kwargs.get('max_new_tokens')==1 else output
    monkeypatch.setattr(ternary,'chat',native)
    monkeypatch.setattr(engram,'for_request',lambda *a,**k:('water-test',))
    out=talk.reply(PHASE_QUESTION,base='t80')
    assert calls[0]['also']==('water-test',)
    assert len(calls)==(1 if way=='work' else 2)
    assert out['text']=='The water is liquid.' and out['water_phase_check']['source']==source
    assert out['agreed'] is None
    if head=='At':
        assert not out['engram_advice']['accepted'] and out['engram_advice']['model_reply']=='At'
    if way=='talk' and output=='It is gas.':
        assert out['water_phase_check']['model_answer']==output and out['engrams'][0]['stage']=='answer_attempt'


def test_direct_workers_cannot_certify_a_shared_phase_error(tmp_path,monkeypatch):
    import json
    from team import solo
    monkeypatch.setenv('HIVE_SIGNALS','0')
    monkeypatch.setenv('HIVE_ENGRAMS','0')
    def emit(task,n,board,guard,work,temp,who,also):
        work.mkdir(parents=True,exist_ok=True)
        return dict(answer='gas',program="print('gas')",who=who)
    monkeypatch.setattr(solo,'member',emit)
    result=solo.first(PHASE_QUESTION,tmp_path,members=2)
    record=json.loads((tmp_path/'members/members.json').read_text())
    assert not result['agreed'] and not record['agreeing'] and record['water_phase_check']['phase']=='liquid'
    assert 'local equilibrium check gives liquid' in result['report']
    pair=[{'answer':'liquid'},{'answer':'liquid'}]
    assert solo.agreeing(pair,PHASE_QUESTION)==[tuple(pair)]
    wrong=[{'answer':'gas'},{'answer':'gas'}]
    assert solo.agreeing(wrong,'Write a file answering this question. '+PHASE_QUESTION)==[tuple(wrong)]

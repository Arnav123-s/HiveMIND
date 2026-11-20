"""Check promotion and invalidation on public development inputs using the real saved bank."""
import argparse
import json
import os
from pathlib import Path
import tempfile
import time

from team import config, saved
from training.experiments.fieldwork import work
from training.experiments.fieldwork.guest import Guest
from .trace import GuardedTrace

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
PARENT = ROOT / 'training/reports/retained-skills/shipping/bank'
GATE = [dict(input=items,output=fee) for items,fee in [(['0.25'],340),(['0.122','0.312'],430),(['0.55'],430),(['2.05'],700)]]


def message(masses, rounding='per-parcel'):
    text = 'Calculate the depot shipping fee for ' + ' and '.join(f'{n} kg' for n in masses)
    return text + (f' using {rounding} rounding' if rounding else '')


def verify(sdk):
    guest = Guest(sdk)
    start = time.perf_counter()
    _ = guest.runtime
    report = {'warmup_seconds':time.perf_counter()-start, 'checks':[], 'requests':[]}
    with tempfile.TemporaryDirectory() as td:
        parent, children = Path(td)/'bank', Path(td)/'siblings'
        os.environ['HIVE_BANK'] = str(parent)
        assert config.saved_bank_path() == parent
        row, = work.load_bank(PARENT)
        work.admit(parent,row)
        def reopen():
            return GuardedTrace(sibling_bank=children,guest=guest)
        trace = reopen()
        def query(label, q, expected, mode='guarded', status='answered', path=None):
            result = trace.answer(q,mode=mode)
            assert (result or {}).get('status') == status and (result or {}).get('value') == expected, (label, result)
            if path:
                assert trace.last['path']==path, (label,trace.last)
            report['requests'].append(dict(label=label, mode=mode, prompt=q, status=status, value=expected, **trace.last))
        q = message(['0.64'])
        for n in ['0.125', '0.1250', '0.125', '0.5']:
            if n=='0.1250':
                query('invalid decimal precision', message([n]),None,status=None,path='stock')
            else:
                query('collecting',message([n]),340,path='side_exit')
        collecting=trace.qualify(q,GATE)
        assert collecting==dict(status='collecting', distinct_exits=2)
        report['checks'].append(collecting)
        trace=reopen()
        query('third distinct input after reopening',message(['0.6']),430,path='side_exit')
        gate_alias=[dict(input=['0.500'],output=340),*GATE[1:]]
        for gate, expected in [(gate_alias,'overlapping_gate'),(GATE[:3],'invalid_gate'),
                               ([dict(input=GATE[0]['input'], output=3400),*GATE[1:]],'unqualified'),(GATE,'published')]:
            proof=trace.qualify(q,gate); assert proof['status']==expected, proof
            report['checks'].append(proof)
        trace=reopen()
        for mode, expected, state in [('stock',None,'stock'),('handwritten',430,'handwritten'),('guarded',430,'sibling')]:
            query('same final request across arms',q,expected,mode,status='answered' if expected is not None else None,path=state)
        query('original grams request','Calculate the depot shipping fee for 640 g using per-parcel rounding',430,path='stock')
        query('different convention cannot use old sibling',message(['0.64'],'pooled'), None,status='missing',path='side_exit')
        query('malformed explicit JSON','Run depot_shipping_fee: {"grams":[-1]}',None,status='missing',path='stock')
        # Separately check and admit the competing tariff. Its code and tariff are authored controls.
        pooled="def solve(x):\n    return 250 + 90 * ((sum(x['grams']) + 499) // 500) if x['grams'] else 0"
        witnesses=[dict(input={'grams':v},output=r) for v,r in [([],0),([250,250],340),([1,500],430),([700,800],520)]]
        count,_=work.check(trace.guest,pooled,witnesses,explain=False); assert count==len(witnesses)
        work.admit(parent,dict(task=saved.SHIPPING[0], description=saved.SHIPPING[1], source=pooled,
                               digest=work.fingerprint(pooled),validation=count))
        query('new pool invalidates prior sibling', message(['0.200','0.210']),430,path='side_exit')
        query('agree on named pooled',message(['0.200','0.210'],'pooled'),340,path='side_exit')
        query('withhold unnamed disagreement',message(['0.200','0.210'],''),None,status='ambiguous',path='side_exit')
        query('withhold stale ID','Run depot_shipping_fee@deadbeefdead: {"grams":[200,210]}',None,status='missing',path='stock')
        assert len(work.load_bank(parent))==2 and len(work.load_bank(children))==1
        report.update(parent_digest=row['digest'],remaining_parent_versions=2, sibling_versions=1, model_calls=0)
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--sdk',type=Path,default=config.fieldwork_sdk_path())
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args(); report=verify(a.sdk)
    a.out.write_text(json.dumps(report,indent=2)+'\n')
    print(f"Passed {len(report['requests'])} request checks and {len(report['checks'])} promotion checks in WASI.")

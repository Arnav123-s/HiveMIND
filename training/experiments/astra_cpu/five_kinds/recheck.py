"""Recreate the registered task and check the exact archived first-turn solution."""
import gzip
import hashlib
import json
from pathlib import Path
import tempfile
from training import exam, lessons
from team.tools.sandbox import give, run_python

HERE=Path(__file__).resolve().parent


def verify(row):
    maker, seed=row['lesson'],row['seed']
    raw=row['output']
    assert raw.startswith('```python\n') and raw.endswith('\n```')
    source=raw[len('```python\n'):-len('\n```')]
    report=dict(kind=maker,seed=seed,archive_solution_sha256=hashlib.sha256(source.encode()).hexdigest(),ok=False)
    for level in range(5):
        made=exam.remake(maker,seed,level)
        if made is not None and made[2]==row['task']:
            break
    else:
        return report | dict(reason='Archived task text did not match reconstruction at levels 0 to 4.')
    _,_,task,check=made
    original_program=lessons.program_for(task,check)
    if not original_program or source.strip()!=original_program.strip():
        return report | dict(level=level,reason='Archived program differs from reconstructed lesson source.')
    with tempfile.TemporaryDirectory() as tmp:
        work=Path(tmp)/'work'
        give(task,work)
        ran=run_python(source,work,name='lesson.py',timeout=45)
        (work/'lesson.py').unlink(missing_ok=True)
        reply=ran['stdout'].strip()
        ok,why=check(Path(tmp),reply) if ran['returncode']==0 else (False,'Archive source did not finish.')
    return report | dict(level=level,ok=bool(ok),detail=why,returned=reply)


if __name__=='__main__':
    data=gzip.decompress((HERE/'panel.jsonl.gz').read_bytes())
    assert hashlib.sha256(data).hexdigest()==json.loads((HERE/'selection.json').read_text())['rows_sha256']
    rows=[verify(json.loads(line)) for line in data.splitlines()]
    print(json.dumps(rows,indent=2))

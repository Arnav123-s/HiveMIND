"""Run known-correct references and an unrelated program through the same WASI and host graders."""
import argparse
from pathlib import Path
import json,tempfile
from types import SimpleNamespace
from training import exam,lessons
from training.experiments.replay_archive.native_cycles import pilot
from training.experiments.astra_cpu.five_kinds.transfer import native
cases=pilot.load(pilot.HERE/'panel.json',pilot.PANEL_SHA)['rows']
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--sdk', type=Path, required=True)
sdk = parser.parse_args().sdk
result={}
with tempfile.TemporaryDirectory() as tmp:
 home=Path(tmp)
 for label in ('reference','wrong'):
  calls=[]
  for row in cases:
   task,check=exam.remake(row['name'],row['seed'],0)[2:]
   code=lessons.program_for(task,check) if label=='reference' else 'print("unknown")'
   assert code
   calls.append(dict(name=row['name'],text='```python\n'+code+'\n```'))
  native.save(home/(label+'-calls.json'),dict(complete=True,panel_sha256=pilot.PANEL_SHA,lora_sha256='grader-control',calls=calls))
  pilot.score(SimpleNamespace(scratch=home,arm=label,sdk=sdk))
  result[label]={k:r['passed'] for k,r in json.loads((home/(label+'-grades.json')).read_text())['results'].items()}
 assert all(result['reference'].values()) and not any(result['wrong'].values()),result
(pilot.HERE/'grader-controls.json').write_text(json.dumps(result,indent=2)+'\n')

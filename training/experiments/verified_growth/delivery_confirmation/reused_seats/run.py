"""Two real solo.first invocations reuse one task directory. Only model chat replies are prerecorded."""
import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from unittest.mock import patch


BASE = "4cbd41cb2e27d263f102801c0a7a008268d0b1aa"
TASK = "Save shelf.txt containing the single word {word}. Then print the same word."


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def solve(solo, root, home, word, member_words):
    replies = []
    for guess in member_words:
        program = f"with open('shelf.txt', 'w') as f:\n    f.write({guess!r} + '\\n')\nprint({guess!r})"
        replies.extend([f"```python\n{program}\n```","DONE"])
    pending = iter(replies)
    with patch.object(solo.llm,"chat",side_effect=lambda *a,**kw:next(pending)), \
         patch.object(solo.ternary,"seating",return_value=["coder"]), \
         patch.object(solo,"library",return_value=root/"memory/solved.jsonl"):
        result=solo.first(TASK.format(word=word),home,members=2)
    assert next(pending,None) is None
    decision=json.loads((home/"members/members.json").read_bytes())
    output=(home/"work/shelf.txt").read_text()
    assert result['agreed'] and result['files']==['shelf.txt'] and output==word+'\n'
    assert result['tries']==len(member_words)==len(decision["who"])
    return dict(tries=result["tries"],selected=decision["selected_member"],who=decision["who"],
                output=output,public_report_sha256=digest(home/'REPORT.md'))


def audit(args):
    stock=args.stock.resolve()
    candidate=args.collector.resolve()
    assert subprocess.check_output(["git","rev-parse","HEAD"],cwd=stock,text=True).strip()==BASE
    assert digest(candidate)==args.expected_sha
    sys.path.insert(0,str(stock))
    from team import solo
    with TemporaryDirectory() as temp:
        root=Path(temp)
        home=root/"runs/exam/batch/labels"
        first=solve(solo,root,home,"Amber",["Sapphire","Amber","Amber"])
        stale=home/"members/member3.json"
        old_receipt=digest(stale)
        previous_work=Path(json.loads(stale.read_bytes())["work"])
        old_bytes=(previous_work/"shelf.txt").read_bytes()
        second=solve(solo,root,home,"Pearl",["Pearl","Pearl"])
        previous_value=(previous_work/"shelf.txt").read_bytes()
        assert old_receipt==digest(stale) and old_bytes==previous_value and previous_value==b'Amber\n'
        stored_task=(home/"members/TASK.md").read_text().strip()
        assert stored_task==TASK.format(word="Pearl")
        expected_seats=[1,2]
        source_receipts=sorted(p.name for p in (home/'members').glob('member[0-9]*.json'))
        # Invoke the proposal's normal gate collector; current answer bytes are read before and after.
        argv=[sys.executable,"-m","training.member_evidence","--root","runs/exam","--out","runs/exam/worker-evidence"]
        env=os.environ|{"PYTHONPATH":str(candidate.parents[1]),"HF_HUB_OFFLINE":"1"}
        proc=subprocess.run(argv,cwd=root,env=env,capture_output=True,text=True,timeout=30,check=True)
        evidence=root/"runs/exam/worker-evidence/batch/labels"
        manifest=json.loads((evidence/"manifest.json").read_bytes())
        stored={s["seat"]:(evidence/s["files"]["shelf.txt"]["path"]).read_text()
                for s in manifest["seats"] if s["files"].get("shelf.txt",{}).get("status")=="archived"}
        assert (home/"work/shelf.txt").read_text()==second['output'] and digest(home/'REPORT.md')==second['public_report_sha256']
        assert manifest['task_sha256']==sha256((stored_task+'\n').encode()).hexdigest()
        return dict(stock_commit=BASE,collector_sha256=args.expected_sha,first=first,second=second,
                    stored_task=stored_task,expected_current_seats=expected_seats,
                    on_disk_worker_receipts=source_receipts,stale_receipt_bytes_unchanged=True,
                    old_worker_file=previous_value.decode(),archive_seats=sorted(stored),archived_contents=stored,
                    stale_bytes_attached_to_second=stored.get(3)==previous_value.decode(),
                    current_seat_coverage=[seat for seat in expected_seats if stored.get(seat)==second["output"]],
                    public_delivery_and_report_unchanged=True,command_stdout=proc.stdout.strip())


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--stock',type=Path,required=True)
    p.add_argument('--collector',type=Path,required=True)
    p.add_argument('--expected-sha',required=True)
    p.add_argument('--out',type=Path,required=True)
    args=p.parse_args()
    result=audit(args)
    args.out.write_text(json.dumps(result,indent=2)+'\n')
    print(result['expected_current_seats'],result['archive_seats'],result['archived_contents'])

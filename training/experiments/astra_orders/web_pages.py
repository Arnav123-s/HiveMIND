"""Replay the proposed URL-count decision against four measured local HTTP traces."""
import argparse
from collections import Counter
import hashlib
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
import re
from tempfile import TemporaryDirectory
from threading import Thread
from urllib.request import Request, urlopen
from zipfile import ZipFile


HERE = Path(__file__).resolve().parent
AUTHORS = [('Ada','Lin'),('Lin','Ros'),('Ada',),('Ros','Lin'),('Mei','Lin')]
EXPECTED = {'Ada':2,'Lin':4,'Ros':2,'Mei':1}


def count_requested(task):
    match = re.search(r'\bfirst (\d+) pages\b|\bpages 1 (?:through|to) (\d+)\b',task,re.I)
    return int(match.group(1) or match.group(2)) if match else None


class Pages(BaseHTTPRequestHandler):
    def do_GET(self):
        page = None
        if self.path == '/feed':
            page = int(self.headers.get('X-Cursor','1'))
        elif re.fullmatch(r'/pages/[1-5]',self.path):
            page = int(self.path.rsplit('/',1)[1])
        entries = AUTHORS[page-1] if page else ()
        payload = json.dumps({'authors':entries}).encode()
        self.send_response(200)
        self.send_header('Content-Type','application/json')
        self.send_header('Content-Length',str(len(payload)))
        if self.path == '/feed':
            self.send_header('Vary','X-Cursor')
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self,*args):
        pass


def capture(base, inputs, target, cache=False):
    counts,seen,responses,hits = Counter(), set(), {}, 0
    trace=[]
    for path, headers in inputs:
        if cache and path in responses:
            rows = responses[path]
            hits += 1
            source = 'URL cache'
        else:
            with urlopen(Request(base+path,headers=headers),timeout=3) as r:
                rows = json.load(r)['authors']
                assert r.status == 200
            seen.add(path)
            responses[path] = rows
            source = 'HTTP 200'
        counts.update(rows)
        trace.append({'path':path,'request_headers':headers,'source':source,'parsed_authors':rows})
    with TemporaryDirectory() as temp:
        product = Path(temp) / 'authors.json'
        product.write_text(json.dumps(counts, sort_keys=True))
        report = max(counts, key=counts.get)
        checked_counts = json.loads(product.read_text())
        file_sha = hashlib.sha256(product.read_bytes()).hexdigest()
    return {'requests':trace, 'distinct_urls_fetched':len(seen), 'cache_hits':hits,
            'file_name':'authors.json', 'file_sha256':file_sha, 'counts':checked_counts, 'report':report,
            'requested_pages':target, 'prompt_guard_accept':len(seen)>=target,
            'correct':checked_counts==EXPECTED and report=='Lin'}


def prior_attempts(work_archive):
    expected = '94b73e0f30c14b8ac7c04bb68184850b705056c0320562ae6433bdbb8a7b12bf'
    assert hashlib.sha256(work_archive.read_bytes()).hexdigest() == expected
    with ZipFile(work_archive) as z:
        home = 'exam_20000556_mixed/h20000556_00/members/'
        events = [json.loads(line) for line in z.read(home+'events.jsonl').splitlines()]
        attempts=[]
        for event in events:
            if event['kind'] != 'run':
                continue
            match = re.fullmatch(r'turn (\d+): exit (-?\d+), printed (\d+) characters',event['msg'])
            turn,code,chars=map(int,match.groups())
            member=event['agent']
            leaf=f'.{member}_{turn}.py'
            matches=[k for k in z.namelist() if k.startswith(home) and k.endswith('/'+leaf+'.err')]
            assert len(matches)==1
            stderr=z.read(matches[0]).decode(); stdout=z.read(matches[0][:-3]+'out').decode()
            attempts.append({'member':member,'turn':turn,'exit':code,'printed':chars,'stderr_last':stderr.strip().splitlines()[-1] if stderr.strip() else '',
                             'stdout_start':stdout.strip()[:80], 'http_error_signal':'HIVE-HTTP:' in stderr,'repeat_url_signal':'HIVE-SAME:' in stderr})
        return {'artifact_id':14644824529,'archive_sha256':expected,'attempts':attempts,
                'exit_counts':dict(Counter(a['exit'] for a in attempts)),
                'report':z.read(home+'REPORT.md').decode().strip()}


def main(archivedir,work_archive,out):
    archives=[]
    for archive in sorted(archivedir.glob('gate-after-*.zip')):
        with ZipFile(archive) as z:
            rows=json.loads(z.read(z.namelist()[0]))['tasks']
        for r in rows:
            if 'pages' in r['task']:
                archives.append({k:r[k] for k in ('id','task','ok','why')} | {'artifact':archive.name,
                                'archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'explicit_count':count_requested(r['task'])})
    exact, = (r for r in archives if r['id']=='h20000556_00')
    target=exact['explicit_count']
    assert target==5
    cases = {'distinct_pages': [(f'/pages/{i}',{}) for i in range(1,6)],
             'repeat_page': [('/pages/1',{})]*5,
             'page_plus_assets': [('/pages/1',{})]+[(f'/assets/{i}',{}) for i in range(1,5)],
             'cursor_feed':[('/feed',{'X-Cursor':str(i)}) for i in range(1,6)]}
    with HTTPServer(('127.0.0.1',0),Pages) as server:
        thread=Thread(target=server.serve_forever,daemon=True); thread.start()
        base=f'http://127.0.0.1:{server.server_port}'
        try:
            traces={k:capture(base,inputs,target) for k,inputs in cases.items()}
            cached=capture(base,cases['cursor_feed'],target,True)
        finally:
            server.shutdown(); thread.join()
    controls={t:count_requested(t) for t in ['Read the first 3 paragraphs of one page.','See pages 1 to 7.','Read several pages.']}
    assert list(controls.values())==[None,7,None]
    assert [(v['prompt_guard_accept'],v['correct']) for v in traces.values()]==[(True,True),(False,False),(True,False),(False,True)]
    result={'g55_gate_run':44728930517,'archive_scope':'eight after-body pulse artifacts','archived':archives,
            'original_network_task':prior_attempts(work_archive),'mirror_task':exact['id'],'mirror_expected':EXPECTED,'traces':traces,'url_only_cache':cached,'parser_controls':controls}
    out.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('g55_gate_dir',type=Path);p.add_argument('work_archive',type=Path);p.add_argument('out',type=Path)
    a=p.parse_args();main(a.g55_gate_dir,a.work_archive,a.out)

"""Independently authored, neutral worker snapshots and external product specifications."""
from base64 import b64encode
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
from zipfile import ZipFile, ZipInfo, ZIP_STORED


def package(contents):
    buffer=BytesIO()
    with ZipFile(buffer,'w',compression=ZIP_STORED) as z:
        for name,body in contents.items():
            z.writestr(ZipInfo(name,date_time=(2023,8,5,10,30,0)),body)
    return buffer.getvalue()


def files(items):
    return {name:b64encode(value if isinstance(value,bytes) else value.encode()).decode() for name,value in items.items()}


def seat(message, **items):
    return {'answer':message,'files':files(items)}


def build(folder):
    cases=[]; keys={}
    def add(name,request,attempts,acceptable,*,stale=None,source_mode='exact',wrong_consensus=False):
        cases.append({'id':name,'request':request,'seats':attempts,'stale':files(stale or {})})
        keys[name]={'accepted':[{n:v for n,v in files(products).items()} for products in acceptable],
                    'grade_mode':source_mode,'wrong_consensus_control':wrong_consensus}

    sign='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><circle cx="5" cy="5" r="3"/></svg>\n'
    add('sign','Create crossing.svg containing a circle of radius 3 centred at (5,5) in a ten-unit view box.',
        [seat('Marker ready.',**{'crossing.svg':sign}),seat('Marker ready.',**{'crossing.svg':sign,
              'scratch.md':'Unsigned internal design note.\n'})],[{'crossing.svg':sign}])
    card='# Copper plate\nShelf: Cedar\n'
    add('placard','Save placard.md with the title Copper plate and the shelf name Cedar.',
        [seat('Catalogue label prepared.',**{'placard.md':card}),seat(''),seat('')],[{'placard.md':card}])
    rule='quiet = true\nbeep = false\n'; bad='quiet = true\nbeep = true\n'
    add('settings','Save kettle.toml with quiet enabled and the audible beep disabled.',
        [seat('Settings ready.',**{'kettle.toml':bad}),seat('Settings ready.',**{'kettle.toml':bad})],
        [{'kettle.toml':rule}],wrong_consensus=True)
    invitation='<h1>North Hall</h1>\n'; guests='Welcome team\n'
    add('split-bundle','Write entrance.html and welcome.txt. The heading names North Hall. The note reads Welcome team.',
        [seat('Entrance prepared.',**{'entrance.html':invitation}),seat('Note prepared.',**{'welcome.txt':guests}),
         seat('')],[{'entrance.html':invitation,'welcome.txt':guests}])
    a='{"mat":"reed","count":2}\n'; b='{\n "count": 2, "mat": "reed"\n}\n'
    add('catalogue','Save stock-card.json giving the material reed under mat and a count of 2.',
        [seat('Catalogue ready.',**{'stock-card.json':a}),seat('Catalogue ready.',**{'stock-card.json':b})],
        [{'stock-card.json':a},{'stock-card.json':b}],source_mode='explicit-alternatives')
    add('one-wrong','Write stops.txt, one stop per line, Pine then Moss then Ash.',
        [seat('Stops prepared.',**{'stops.txt':'Pine\nAsh\nMoss\n'}),seat(''),seat('')],[{'stops.txt':'Pine\nMoss\nAsh\n'}])
    unordered='bay\trank\nEast\t4\nWest\t1\nSouth\t2\n'
    ordered='bay\trank\nWest\t1\nSouth\t2\nEast\t4\n'
    add('ordered','Save bays.tsv with columns bay,rank sorted by rank ascending. East has rank 4, West 1, South 2.',
        [seat('Ready.',**{'bays.tsv':unordered}),seat('Ready.',**{'bays.tsv':unordered})],
        [{'bays.tsv':ordered},{'bays.tsv':ordered.replace('\n','\r\n')}],source_mode='explicit-alternatives')
    label='# Dispatch desk\nCurrent\n'
    add('stale','Write counter.md with the heading Dispatch desk and the word Current.',
        [seat('No current file.'),seat('No current file.'),seat('')],[{'counter.md':label}],
        stale={'counter.md':'# Dispatch desk\nPrevious tenant\n'})
    scene='Red gate\n'; add('byproducts','Save gate.txt with the words Red gate. Do not save notes.md.',
        [seat('Gate ready.',**{'gate.txt':scene,'notes.md':'dry run\n','task_data.txt':'input sidecar\n'}),
         seat('Gate ready.',**{'gate.txt':scene,'notes.md':'draft from peer\n'})],[{'gate.txt':scene}])
    zipped=package({'recipe.txt':'Dill\nMint\n','readme.txt':'Herb list\n'})
    altzip=package({'recipe.txt':'Dill\nMint\n','readme.txt':'Errata\n'})
    add('packet','Create herbs.zip containing recipe.txt with Dill then Mint, and readme.txt with Herb list.',
        [seat('Packet complete.',**{'herbs.zip':zipped}),seat('Packet available.',**{'herbs.zip':altzip}),seat('')],
        [{'herbs.zip':zipped}])
    cfg='color = "azure"\n'; pages='# Sample book\nEdition A\n'
    add('complete-bundle','Save theme.toml and edition.md. Set color to azure and mark the sample book Edition A.',
        [seat('',**{'theme.toml':cfg,'edition.md':pages}),seat(''),seat('')],
        [{'theme.toml':cfg,'edition.md':pages}])
    add('read-only','Tell me the single word Cedar. No file delivery is needed.',
        [seat('Cedar',**{'spare.txt':'Worker note, unrequested.\n'}),seat('Cedar',**{'spare.txt':'Different note.\n'})],[{}])
    assert len(cases)==12
    for name, data in [('cases.json',cases),('keys.json',keys)]:
        (folder/name).write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n')


if __name__=='__main__':
    build(Path(__file__).resolve().parent)

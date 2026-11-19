"""Measure the CLI sensor capability against the original trained archive and integer arithmetic."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[4]
ARCHIVE = ROOT/'training/reports/rule_lab/engrams/four-bit-pair.npz'
SEED = 48179031
SCALE = 1_000_000


def cases():
    rng = random.Random(SEED)
    for _ in range(4096):
        yield 'normal', [round(rng.gauss(0,1)*SCALE) for _ in range(8)]
    for _ in range(256):
        values = [rng.randrange(-2*SCALE, 2*SCALE) for _ in range(8)]
        tiny = rng.choice((-1, 0, 1))
        values[2] = values[0]+values[1]+tiny
        # Choose both exact/almost-zero sums and a broad second measurement.
        if rng.randrange(2):
            values[6] = values[5]-values[4]+tiny
        if rng.randrange(2):
            values[3] = rng.choice((-1,1))*10**15
            values[7] = -values[3]
        yield 'near_boundary', values
    for i in range(32):
        values = [rng.randrange(-2*SCALE,2*SCALE) for _ in range(8)]
        values[6] = -values[0]-values[1]+values[2]-values[4]+values[5]
        if i % 3:
            values[6] += (-1,0,1)[i%3]
        yield 'zero_sum', values


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    sys.path.insert(0,str(ROOT))
    from team import talk
    from training.experiments.hive_signals import FRAME, emit, interpret, load_reader, load_sender
    import torch
    torch.set_num_threads(1)
    senders = [load_sender(ARCHIVE,i) for i in (0,1)]
    reader = load_reader(ARCHIVE)
    totals = {}; first = {}; input_hash = hashlib.sha256()
    for index,(group,integers) in enumerate(cases()):
        counts=totals.setdefault(group,Counter())
        inputs=[v/SCALE for v in integers]
        message='Check sensor banks '+json.dumps(inputs[:4])+' and '+json.dumps(inputs[4:])
        input_hash.update((message+'\n').encode())
        # Exercise the public conversation entry point; a bad route cannot get credit.
        result=talk.reply(message)['sensor_banks']
        reference=[emit(sender, i, index, inputs[4*i:4*i+4]) for i,sender in enumerate(senders)]
        original_codes=[FRAME.unpack(f)[4] for f in reference]
        original=interpret(reader,index,list(reversed(reference)))
        x=integers[0]+integers[1]-integers[2];y=integers[4]-integers[5]+integers[6]
        gold=[(x>0)!=(y>0),x+y>0]
        pair=result['pair_predictions']
        observed=[result['different_positivity'],result['positive_sum']]
        counts.update(inputs=1,served_correct=observed==gold,codes_match=result['codes']==original_codes,
                      decisions_match=pair==original,original_both_correct=original==gold,
                      positive_class_matches=original[0]==gold[0],sum_matches=original[1]==gold[1],
                      disclosures_correct=result['pair_agrees']==(pair==gold))
        key=group+('_agree' if pair==gold else '_corrected')
        if key not in first:
            first[key]={'request':message,'gold':gold,'codes':result['codes'],'original_predictions':original,
                        'served':observed}
    report={'seed':SEED,'test_input_sha256':input_hash.hexdigest(),
            'original_archive_sha256':hashlib.sha256(ARCHIVE.read_bytes()).hexdigest(),
            'serving_asset_sha256':hashlib.sha256((ROOT/'team/assets/sensor-banks-four-bit.json').read_bytes()).hexdigest(),
            'counts':totals,'examples':first}
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(totals))

if __name__=='__main__':
    main()

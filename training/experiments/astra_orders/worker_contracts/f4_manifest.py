"""The expected packed body is G55 with exactly its named trunk replaced."""
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parent
TRUNK = '  cells/members/t80+g55trunk.gguf'
PARENT = '72913f1c566638f2177574178f1d6925cde956a92b35af06795e7598c5729036'
STOCK_REF = 'ac77ff328406b4404de205c4ce62266ac0b181b8'


def manifest(registration, old):
    child = registration['sha256']
    if (registration['parent_sha256'] != PARENT or registration['stock_workflow_sha'] != STOCK_REF
            or registration['file'] != 't80-hint-dream.gguf' or not re.fullmatch('[0-9a-f]{40}', registration['source_ref'])
            or not re.fullmatch('[0-9a-f]{64}', child) or child == PARENT):
        raise ValueError('Invalid F4 adapter registration')
    lines = old.splitlines()
    if len(lines) != 25 or lines.count(PARENT + TRUNK) != 1 or sum(line.endswith(TRUNK) for line in lines) != 1:
        raise ValueError('The expected G55 trunk is absent or ambiguous')
    return old.replace(PARENT + TRUNK, child + TRUNK)


if __name__ == '__main__':
    sys.stdout.write(manifest(json.loads((ROOT/'f4-adapter.json').read_text()), (ROOT/'g55-contemporaneous.sha256').read_text()))

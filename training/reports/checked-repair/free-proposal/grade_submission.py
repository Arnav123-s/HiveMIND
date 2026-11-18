"""Re-score the recorded G47 sensor reply on the original 228 exposure inputs.

On Linux with libseccomp.so.2 available, run from a HiveMIND checkout:
    python path/to/grade_submission.py --repo . --reply path/to/reply.txt
    python path/to/grade_submission.py --repo . --parent

Only the two recorded source hashes may execute. The worker sees case inputs
without labels. Its filesystem, network and process syscalls are disabled.
"""
import argparse
import collections
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile


PARENT = 'e989057e402cf51ca4f84597a421da25775a16ff9b69ef271251279f37998acd'
CANDIDATE = '4454ffafbfd60d2257965640d7822bce05190e587d88ba92dc637a40e8165453'
ORACLE = 'd35e7c75fc8b9aaed9f28d1c4f84bdf41ca67fa875a54d4ed0788a6a51b6e38c'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def extract(reply):
    if '```' not in reply:
        return reply
    first = re.search(r'^[ \t]*```(?:python|py)[ \t]*\r?\n(.*?)^[ \t]*```[ \t]*(?:\r?\n|$)', reply, re.I | re.M | re.S)
    if not first:
        raise ValueError('no complete Python-tagged fenced block')
    return first[1]


def run_child(source_file, cases_file):
    import builtins
    import ctypes
    import errno
    import math
    import resource
    import typing

    source = Path(source_file).read_bytes()
    if digest(source) not in (PARENT, CANDIDATE):
        raise ValueError('unrecognized source digest')
    code = compile(source, '<frozen sensor code>', 'exec')
    cases = json.loads(Path(cases_file).read_text())
    safe_modules = {'math': math, 'typing': typing}

    def numeric_import(name, *args, **kwargs):
        if name not in safe_modules:
            raise ImportError(name)
        return safe_modules[name]

    names = ('abs all any bool dict enumerate filter float int isinstance len list map max min range reversed '
             'round set sorted str sum tuple zip ArithmeticError ValueError TypeError').split()
    available = {key: getattr(builtins, key) for key in names}
    available['__import__'] = numeric_import
    namespace = {'__builtins__': available, '__name__': 'sensor_candidate'}
    resource.setrlimit(resource.RLIMIT_AS, (160 << 20, 160 << 20))
    resource.setrlimit(resource.RLIMIT_CPU, (3, 4))
    resource.setrlimit(resource.RLIMIT_FSIZE, (0, 0))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))

    lib = ctypes.CDLL('libseccomp.so.2')
    lib.seccomp_init.argtypes = [ctypes.c_uint32]
    lib.seccomp_init.restype = ctypes.c_void_p
    lib.seccomp_syscall_resolve_name.argtypes = [ctypes.c_char_p]
    lib.seccomp_rule_add.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_int, ctypes.c_uint]
    lib.seccomp_load.argtypes = [ctypes.c_void_p]
    # SCMP_ACT_ERRNO, with explicit SCMP_ACT_ALLOW for this numeric worker's runtime needs.
    ctx = lib.seccomp_init(0x00050000 | errno.EPERM)
    if not ctx:
        raise RuntimeError('seccomp_init failed')
    allowed = 'write writev close brk mmap madvise munmap mremap mprotect clock_gettime futex rt_sigreturn sigaltstack exit exit_group'
    for name in allowed.split():
        number = lib.seccomp_syscall_resolve_name(name.encode())
        if number >= 0 and lib.seccomp_rule_add(ctx, 0x7fff0000, number, 0) != 0:
            raise RuntimeError('seccomp_rule_add failed')
    if lib.seccomp_load(ctx) != 0:
        raise RuntimeError('seccomp_load failed')

    exec(code, namespace)
    exposure = namespace['exposure']
    values = []
    for _, args in cases:
        try:
            elapsed, count = exposure(*args)
            if not all(type(n) in (int, float, bool) for n in (elapsed, count)):
                raise TypeError('nonnumeric result')
            values.append({'result': [elapsed, count]})
        except Exception as exc:
            values.append({'error': type(exc).__name__ + ': ' + str(exc)[:160]})
    os.write(1, json.dumps(values).encode())


def score(repo, source):
    sys.path.insert(0, str(repo.resolve()))
    from training.experiments import checked_repair_grade as g
    if digest(Path(g.__file__).read_bytes()) != ORACLE:
        raise ValueError('oracle does not match the published revision')
    cases = list(g._exposure_cases())
    if len(cases) != 228:
        raise ValueError('unexpected input count')
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        path = root / 'candidate.py'
        path.write_bytes(source)
        inputs = root / 'cases.json'
        inputs.write_text(json.dumps(cases))
        child = subprocess.run([sys.executable, '-I', '-B', str(Path(__file__).resolve()), '--child', str(path), str(inputs)],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=root, env={'LC_ALL': 'C'}, timeout=8)
    if child.returncode != 0:
        raise RuntimeError('worker exit ' + str(child.returncode) + ': ' + child.stderr.decode()[-500:])
    results = json.loads(child.stdout)
    counts, errors, examples = {}, collections.Counter(), []
    for i, ((group, args), observed) in enumerate(zip(cases, results, strict=True), 1):
        expected_time, crossings = g._exposure_reference(*args)
        row = counts.setdefault(group, {'passed': 0, 'total': 0, 'elapsed_passed': 0, 'crossings_passed': 0})
        row['total'] += 1
        if 'result' in observed:
            elapsed, count = observed['result']
            time_ok = g._near(elapsed, expected_time)
            count_ok = not isinstance(count, bool) and count == crossings
            failing = [name for name, ok in [('elapsed', time_ok), ('crossings', count_ok)] if not ok]
            why = ' and '.join(failing)
        else:
            time_ok = count_ok = False
            why = observed['error']
        row['elapsed_passed'] += time_ok
        row['crossings_passed'] += count_ok
        row['passed'] += time_ok and count_ok
        if why:
            errors[why] += 1
            if len(examples) < 6:
                examples.append(dict(index=i, args=args, **observed, expected=[expected_time, crossings], failure=why))
    return dict(source_sha256=digest(source), oracle_sha256=ORACLE, cases=len(cases),
                groups=counts, failures=dict(errors), first_failures=examples)


def main():
    if sys.argv[1:2] == ['--child']:
        run_child(*sys.argv[2:])
        return
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=Path.cwd())
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--reply', type=Path)
    group.add_argument('--parent', action='store_true')
    args = parser.parse_args()
    if args.parent:
        source = (args.repo / 'training/experiments/checked_repair_parent.py').read_bytes()
    else:
        source = extract(args.reply.read_bytes().decode('utf-8')).encode()
    if digest(source) != (PARENT if args.parent else CANDIDATE):
        raise ValueError('source is not the recorded, reviewed program')
    print(json.dumps(score(args.repo, source), indent=2))


if __name__ == '__main__':
    main()

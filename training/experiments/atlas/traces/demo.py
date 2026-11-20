"""Invoke the opt-in WASI trace without changing the production dispatcher or its bank."""
import argparse
import json
from pathlib import Path
from team import config
from training.experiments.fieldwork.guest import Guest
from .trace import GuardedTrace


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bank', type=Path, default=config.saved_bank_path(), help='read-only parent bank, defaults to HIVE_BANK')
    parser.add_argument('--sibling-bank', required=True, type=Path, help='separate directory for experimental branches')
    parser.add_argument('--sdk', type=Path, default=config.fieldwork_sdk_path())
    cmd = parser.add_subparsers(dest='action', required=True)
    ask = cmd.add_parser('answer')
    ask.add_argument('message')
    ask.add_argument('--mode', choices=('stock','handwritten','guarded'), default='guarded')
    certify = cmd.add_parser('qualify')
    certify.add_argument('message', help='selects the rounding scope; its numeric value is not used as a label')
    certify.add_argument('--examples', required=True, type=Path, help='independently labeled list of input/output cases')
    args = parser.parse_args()
    if args.bank and args.bank.resolve() == args.sibling_bank.resolve():
        parser.error('use a separate experimental sibling bank')
    trace = GuardedTrace(bank=args.bank, sibling_bank=args.sibling_bank, guest=Guest(args.sdk))
    if args.action == 'qualify':
        out = trace.qualify(args.message, json.loads(args.examples.read_bytes()))
    else:
        out = {'answer':trace.answer(args.message, mode=args.mode), 'execution':trace.last}
    print(json.dumps(out, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()

"""Trace the ordinary selectors against the six verified, installed adapters, without running the 8B."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
from unittest.mock import patch


HERE = Path(__file__).resolve().parent
PANEL = 'f0a98338574b301683cc3050f4d90add58af11e1178a23403a5e5304a39f44d9'
CORE = 'ddfc72e33e072415b03f6ca71569fe210c235b8b9923290910ef5200f70c4446'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def trace(text, route_choice, base, registry, domain_route, engram, talk, ternary):
    # Some messages require an 8B choice between talk and work. Measure both possible decisions.
    with patch.object(ternary, 'chat', return_value=route_choice.upper()) as router:
        way, _ = talk.route(base, text, ())
    with domain_route.for_request(text, ()) as decision:
        labels = []
        budgets = []
        def stop_before_generation(member, messages, **kwargs):
            # Reaching the true generation boundary establishes selection only.
            budgets.append(kwargs['max_new_tokens'])
            if budgets[-1] not in (1, 8):
                raise ValueError('unexpected label inference budget')
            labels.extend(kwargs['also'])
            return ''
        with patch.object(ternary, 'chat', side_effect=stop_before_generation):
            domain_route.prepare_advice(text, base, '', direct_labels=way=='talk')
        names = engram.for_request(text, base, labels=way=='talk')
        direct = [n if type(n) is str else n[0] for n in names]
        direct = [n for n in direct if n in registry and registry[n][1].get('form')=='label']
        picks = set(labels + direct)
        if len(picks) > 1:
            raise ValueError('multiple different microtasks selected on one route')
        name = next(iter(picks), None)
        return {'route': way, 'router_decision_would_require_model': router.called,
                'domain_signal': decision['domain'] if decision else None,
                'framed_token_budget': budgets[0] if budgets else None,
                'path': 'internally_framed' if labels else ('direct_label' if direct else 'no_microtask'),
                'selected': name, 'domain': registry[name][1]['domain'] if name else None}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkout', type=Path, default=HERE.parents[3])
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--registry-sha', required=True, help='final installed index SHA-256')
    parser.add_argument('--cases', type=Path, default=HERE/'cases.json')
    parser.add_argument('--panel-sha', default=PANEL)
    parser.add_argument('--bank', type=Path, help='override packaged cells/engrams for a frozen comparison')
    parser.add_argument('--scope-sha', default=CORE, help='expected SHA-256 for the selected scope-helper version')
    args = parser.parse_args()
    root = args.checkout.resolve()
    sys.path.insert(0,str(root))
    bank = args.bank.resolve() if args.bank else root/'cells/engrams'
    os.environ.update(HIVE_ENGRAMS_HOME=str(bank),HIVE_ENGRAMS='1',HIVE_SIGNALS='1',HIVE_BANK='off')
    from team import domain_advice, domain_route, engram, talk, ternary
    cases = args.cases
    if sha(cases) != args.panel_sha:
        raise ValueError('original applicability cases changed')
    if sha(Path(domain_advice.__file__)) != args.scope_sha:
        raise ValueError('scope helper differs from the frozen helper')
    if sha(bank/'index.jsonl') != args.registry_sha:
        raise ValueError('installed registry differs from frozen native package')
    files = engram.bank_entries('t80', bank)
    registry = {n: entry for n,entry in files.items()
                if entry[1] and entry[1].get('form')=='label' and entry[1].get('verified') is True}
    task_rows = json.loads(cases.read_bytes())
    expected = {r['domain'] for r in task_rows}
    available = {entry[1]['domain'] for entry in registry.values()}
    if not available.issubset(expected) or len(registry)!=len(available):
        raise ValueError('unexpected or duplicate domain in starter catalogue')
    rows = []
    for row in task_rows:
        local = talk.local_reply(row['text'], local_only=True)
        if local and not local.get('saved', {}).get('fallback_to_members'):
            raise ValueError('a local non-model route supersedes this selector audit')
        forms = [trace(row['text'], choice, 't80', registry, domain_route, engram, talk, ternary)
                 for choice in ('talk','work')]
        forms = [forms[0]] if forms[0] == forms[1] else forms
        matches = [f['domain']==row['domain'] if row['in_scope'] else f['domain'] is None for f in forms]
        signalled = forms[0]['domain_signal']
        rows.append({'id': row['id'], 'domain': row['domain'], 'in_scope':row['in_scope'],
                     'consensus':signalled,'paths':forms,'all_routes_correct':all(matches),
                     'some_routes_correct':any(matches)})
    counters = {}
    for in_scope in (True,False):
        subset=[r for r in rows if r['in_scope']==in_scope]
        counters['applicable' if in_scope else 'adjacent'] = {
            'count':len(subset),'always_correct':sum(r['all_routes_correct'] for r in subset),
            'sometimes_correct':sum(r['some_routes_correct'] and not r['all_routes_correct'] for r in subset),
            'always_selected':sum(all(f['selected'] is not None for f in r['paths']) for r in subset),
            'sometimes_selected':sum(len({bool(f['selected']) for f in r['paths']})>1 for r in subset),
            'selected_after_consensus_agreement_on_all_routes':sum(r['consensus']==r['domain'] and all(f['selected'] for f in r['paths']) for r in subset),
            'selected_after_consensus_abstention_on_all_routes':sum(r['consensus'] is None and all(f['selected'] for f in r['paths']) for r in subset),
            'never_selected_after_consensus_agreement':sum(r['consensus']==r['domain'] and not any(f['selected'] for f in r['paths']) for r in subset),
            'never_selected_after_consensus_abstention':sum(r['consensus'] is None and not any(f['selected'] for f in r['paths']) for r in subset),
            'wrong_domain_selected_anywhere':sum(any(f['domain'] not in {None,r['domain']} for f in r['paths']) for r in subset)}
    report={'cases_sha256':args.panel_sha,'scope_sha256':args.scope_sha,'registry_sha256':sha(bank/'index.jsonl'),
            'selector_sha256':{module.__name__:sha(Path(module.__file__)) for module in (engram,domain_route,talk)},
            'absent_domains':sorted(expected-available),'weights':{name:sha(path) for name,(path,_) in registry.items()},
            'model_generations':0,'summary':counters,'cases':rows}
    for name in ('domain_intent.py','water_phase.py'):
        extra = root/'team'/name
        if extra.is_file():
            report['selector_sha256'][extra.stem] = sha(extra)
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(counters,indent=2))


if __name__ == '__main__':
    main()

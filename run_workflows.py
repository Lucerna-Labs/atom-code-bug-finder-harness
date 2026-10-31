#!/usr/bin/env python3
"""Stateful synthetic security fixtures and frozen two-arm comparison."""
import hashlib
import json
import time
from pathlib import Path
from run_expanded import Choices, SEEDS

FAMILIES = ('revoked_access', 'repeated_refund')
CALLS = 5000


def evaluate(family, actions, clean):
    grants, cache, transactions = set(), set(), {}
    events = []
    for op, identity, value in actions:
        accepted, amount = False, 0
        if family == 'revoked_access':
            if op == 'grant':
                grants.add(identity)
            elif op == 'revoke':
                grants.discard(identity)
            elif op == 'read':
                accepted = identity in grants or (not clean and identity in cache)
                if accepted:
                    cache.add(identity)
        else:
            current = transactions.get(identity)
            if op == 'hold' and current is None:
                transactions[identity] = ('held', value)
                accepted = True
            elif op == 'capture' and current and current[0] == 'held':
                transactions[identity] = ('captured', current[1])
                accepted, amount = True, current[1]
            elif op == 'cancel' and current and current[0] == 'held':
                transactions[identity] = ('cancelled', current[1])
                accepted = True
            elif op == 'refund' and current and current[0] == 'captured':
                accepted, amount = True, current[1]
                if clean:
                    transactions[identity] = ('refunded', current[1])
        events.append({'accepted': accepted, 'amount': amount})
    return events


def violation(family, actions, events):
    # Replay externally visible history, without target cache/transaction states.
    authorized, net_captured = set(), {}
    for (op, identity, _), event in zip(actions, events):
        if family == 'revoked_access':
            if op == 'grant':
                authorized.add(identity)
            elif op == 'revoke':
                authorized.discard(identity)
            elif op == 'read' and event['accepted'] and identity not in authorized:
                return True
        elif event['accepted']:
            if op == 'capture':
                net_captured[identity] = net_captured.get(identity, 0) + event['amount']
            elif op == 'refund':
                net_captured[identity] = net_captured.get(identity, 0) - event['amount']
                if net_captured[identity] < 0:
                    return True
    return False


def validate_controls():
    controls = {
        'revoked_access': (
            [['grant', 1, 0], ['read', 1, 0], ['revoke', 1, 0], ['read', 1, 0]],
            [False, True, False, True], [0, 0, 0, 0], 2),
        'repeated_refund': (
            [['hold', 1, 4], ['capture', 1, 0], ['refund', 1, 0], ['refund', 1, 0]],
            [True, True, True, True], [0, 4, 4, 4], 3),
    }
    checks = []
    for family, (actions, flags, amounts, prefix) in controls.items():
        labeled_bad = [dict(accepted=flag, amount=amount) for flag, amount in zip(flags, amounts)]
        checks.append(violation(family, actions, labeled_bad))
        labeled_good = [dict(event) for event in labeled_bad]
        labeled_good[-1] = dict(accepted=False, amount=0)
        checks.append(not violation(family, actions, labeled_good))
        checks.append(violation(family, actions, evaluate(family, actions, False)))
        checks.append(not violation(family, actions, evaluate(family, actions, True)))
        for clean in (False, True):
            checks.append(evaluate(family, actions[:prefix], clean) == labeled_bad[:prefix])
    if not all(checks):
        raise RuntimeError('Workflow controls failed')
    return {'passed': sum(checks), 'total': len(checks)}


def generate(family, source):
    pick = source.choose
    access = family == 'revoked_access'
    operations = ('grant', 'read', 'revoke') if access else ('hold', 'capture', 'cancel', 'refund')
    length = pick(tuple(range(3, 13)) if access else tuple(range(8, 21)))
    return [[pick(operations), pick((0, 1, 2)), 0 if access else pick((1, 4, 8))]
            for _ in range(length)]


def run(seed, family, clean, on):
    source = Choices(seed, family, on)
    first, witness, failures, errors = None, None, 0, []
    seen = set()
    for call in range(1, CALLS + 1):
        actions = generate(family, source)
        seen.add(json.dumps(actions))
        try:
            events = evaluate(family, actions, clean)
            bad = violation(family, actions, events)
        except Exception as error:
            errors.append(repr(error))
            continue
        failures += bool(bad)
        if bad and witness is None:
            first, witness = call, {'actions': actions, 'events': events}
    return dict(seed=seed, family=family, clean=clean, calls=CALLS,
                first_hit=first, witness=witness, failing_calls=failures,
                errors=errors, distinct_inputs=len(seen))


def main():
    start = time.monotonic()
    controls, arms = validate_controls(), {}
    for label, on in (('off', False), ('on', True)):
        runs = [run(seed, family, clean, on) for seed in SEEDS
                for family in FAMILIES for clean in (False, True)]
        stored = json.loads(json.dumps(runs))
        witnesses = [r for r in stored if r['witness'] is not None]
        reproduced = sum(violation(r['family'], r['witness']['actions'],
                                  evaluate(r['family'], r['witness']['actions'], r['clean']))
                         for r in witnesses)
        arms[label] = dict(runs=runs, summary={
            'calls': sum(r['calls'] for r in runs),
            'classes_found': sorted({r['family'] for r in witnesses if not r['clean']}),
            'by_family': {f: {'seeds_found': sum(r['witness'] is not None for r in runs if r['family'] == f and not r['clean']),
                             'first_hits': [r['first_hit'] for r in runs if r['family'] == f and not r['clean']]}
                          for f in FAMILIES},
            'clean_alarms': sum(r['failing_calls'] for r in runs if r['clean']),
            'exceptions': sum(len(r['errors']) for r in runs),
            'first_hit_sum_with_miss_penalty': sum(r['first_hit'] or CALLS + 1 for r in runs if not r['clean']),
            'witnesses': len(witnesses), 'reproduced': reproduced})
    off, on = arms['off']['summary'], arms['on']['summary']
    better = len(on['classes_found']) > len(off['classes_found']) or (
        len(on['classes_found']) == len(off['classes_found']) and
        on['first_hit_sum_with_miss_penalty'] < off['first_hit_sum_with_miss_penalty'])
    no_loss = all(on['by_family'][f]['seeds_found'] >= off['by_family'][f]['seeds_found'] for f in FAMILIES)
    gates = {name: 'MEASURED' if passed else 'FAILED' for name, passed in {
        'controls': controls['passed'] == controls['total'],
        'both_classes_each': len(off['classes_found']) == len(on['classes_found']) == 2,
        'zero_clean_alarms': off['clean_alarms'] == on['clean_alarms'] == 0,
        'zero_exceptions': off['exceptions'] == on['exceptions'] == 0,
        'matched_budget': off['calls'] == on['calls'] == 100000,
        'all_reproduce': all(a['summary']['witnesses'] == a['summary']['reproduced'] > 0 for a in arms.values()),
        'chaos_benefit': better and no_loss and on['clean_alarms'] == 0,
    }.items()}
    hashes = {name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
              for name in ('run_workflows.py', 'run_expanded.py', 'WORKFLOW-PRECOMMIT.md')}
    result = dict(kind='synthetic_stateful_workflows', seeds=SEEDS, controls=controls,
                  arms=arms, gates=gates, source_sha256=hashes, elapsed_seconds=time.monotonic()-start)
    Path(__file__).with_name('workflow-results.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(dict(off=off, on=on, gates=gates, elapsed_seconds=result['elapsed_seconds']), indent=2))


if __name__ == '__main__':
    main()

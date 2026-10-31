#!/usr/bin/env python3
"""Frozen two-arm synthetic discovery experiment; standard library only."""
import hashlib
import json
import random
import time
from pathlib import Path
from expanded_fixtures import FAMILIES, evaluate, validate_controls, violation

SEEDS = (31, 47, 73, 101, 137)
CALLS = 1000


class Choices:
    def __init__(self, seed, family, on):
        digest = hashlib.sha256(f'{seed}:{family}'.encode()).digest()
        self.rng = random.Random(int.from_bytes(digest[:8], 'big'))
        self.state = (int.from_bytes(digest[8:12], 'big') + 0.5) / 2**32
        self.on = on
        self.perturbations = 0
        self.max_weight_deviation = 0.0
        self.max_weight_sum_error = 0.0

    def choose(self, values):
        point = self.rng.random()
        weights = [1.0] * len(values)
        if self.on:
            raw = []
            for _ in values:
                self.state = 4 * self.state * (1 - self.state)
                raw.append(2 * self.state - 1)
            center = sum(raw) / len(raw)
            weights = [1 + 0.15 * (value - center) for value in raw]
            self.perturbations += len(values)
            self.max_weight_deviation = max(self.max_weight_deviation,
                                           max(abs(weight - 1) for weight in weights))
            self.max_weight_sum_error = max(self.max_weight_sum_error,
                                           abs(sum(weights) - len(values)))
        threshold = point * sum(weights)
        for value, weight in zip(values, weights):
            threshold -= weight
            if threshold < 0:
                return value
        return values[-1]


def generate(family, source):
    pick = source.choose
    if family == 'path':
        segments = [pick(('docs', '.', '..', '%2e%2e', '%252e%252e', 'assets'))
                    for _ in range(pick((1, 2, 3, 4, 5, 6)))]
        return '/'.join(segments + ['file'])
    if family == 'tenant':
        return [pick((0, 1, 2, 3)), pick((0, 1, 2, 3)), pick((False, True))]
    if family == 'overflow':
        values = (0, 1, 2, 16, 255, 256, 257, 1024, 65535, 65536)
        return [pick(values), pick(values)]
    if family == 'headers':
        return [pick(('0', '1', '8', '16', '32')) for _ in range(pick((1, 2, 3)))]
    if family == 'replay':
        return [pick((0, 1, 2, 3, 4)) for _ in range(pick((1, 2, 3, 4, 5, 6)))]
    if family == 'expiry':
        return [pick((99, 100, 101, 102)), pick((100, 101)), pick((False, True))]
    raise ValueError(family)


def search(seed, family, clean, on):
    source = Choices(seed, family, on)
    seen = set()
    witness = None
    failures = 0
    errors = []
    first = None
    for call in range(1, CALLS + 1):
        request = generate(family, source)
        seen.add(json.dumps(request, sort_keys=True))
        try:
            output = evaluate(family, request, clean)
            bad = violation(family, request, output)
        except Exception as error:
            errors.append({'call': call, 'error': repr(error), 'request': request})
            continue
        failures += bool(bad)
        # Strict selector: first verified finding survives; ties keep incumbent.
        if bad and witness is None:
            witness = {'request': request, 'output': output}
            first = call
    return {'seed': seed, 'family': family, 'clean': clean, 'calls': CALLS,
            'distinct_inputs': len(seen), 'failing_calls': failures,
            'first_hit': first, 'witness': witness, 'errors': errors,
            'perturbations': source.perturbations,
            'max_weight_deviation': source.max_weight_deviation,
            'max_weight_sum_error': source.max_weight_sum_error}


def summarize(rows):
    vulnerable = [row for row in rows if not row['clean']]
    return {
        'calls': sum(row['calls'] for row in rows),
        'classes_found': sorted({r['family'] for r in vulnerable if r['witness']}),
        'detected_seed_cases': sum(r['witness'] is not None for r in vulnerable),
        'clean_alarms': sum(r['failing_calls'] for r in rows if r['clean']),
        'exceptions': sum(len(r['errors']) for r in rows),
        'first_hit_sum_with_miss_penalty': sum(r['first_hit'] or CALLS + 1 for r in vulnerable),
        'by_family': {family: {
            'seeds_found': sum(r['witness'] is not None for r in vulnerable if r['family'] == family),
            'first_hits': [r['first_hit'] for r in vulnerable if r['family'] == family],
        } for family in FAMILIES},
    }


def replay(rows):
    # Round trip persisted request representations, then invoke target directly.
    rows = json.loads(json.dumps(rows))
    reproduced = 0
    total = 0
    for row in rows:
        if row['witness'] is None:
            continue
        total += 1
        request = row['witness']['request']
        output = evaluate(row['family'], request, row['clean'])
        reproduced += bool(violation(row['family'], request, output))
    return {'reproduced': reproduced, 'total': total}


def main():
    started = time.monotonic()
    controls = validate_controls()
    arms = {}
    for label, on in (('off', False), ('on', True)):
        rows = [search(seed, family, clean, on)
                for seed in SEEDS for family in FAMILIES for clean in (False, True)]
        arms[label] = {'summary': summarize(rows), 'replays': replay(rows), 'runs': rows}
    off, on = arms['off']['summary'], arms['on']['summary']
    no_detection_loss = all(on['by_family'][f]['seeds_found'] >= off['by_family'][f]['seeds_found']
                            for f in FAMILIES)
    strictly_better = (len(on['classes_found']) > len(off['classes_found']) or
                      (len(on['classes_found']) == len(off['classes_found']) and
                       on['first_hit_sum_with_miss_penalty'] < off['first_hit_sum_with_miss_penalty']))
    gates = {
        'controls': 'MEASURED',
        'at_least_five_classes_each': 'MEASURED' if all(len(a['summary']['classes_found']) >= 5 for a in arms.values()) else 'FAILED',
        'zero_clean_alarms': 'MEASURED' if off['clean_alarms'] == on['clean_alarms'] == 0 else 'FAILED',
        'all_witnesses_reproduce': 'MEASURED' if all(a['replays']['total'] == a['replays']['reproduced'] and a['replays']['total'] > 0 for a in arms.values()) else 'FAILED',
        'zero_exceptions': 'MEASURED' if off['exceptions'] == on['exceptions'] == 0 else 'FAILED',
        'matched_budget': 'MEASURED' if off['calls'] == on['calls'] == 60000 else 'FAILED',
        'chaos_benefit': 'MEASURED' if strictly_better and no_detection_loss and on['clean_alarms'] == 0 else 'FAILED',
    }
    hashes = {name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
              for name in ('run_expanded.py', 'expanded_fixtures.py', 'EXPANDED-PRECOMMIT.md')}
    result = {'kind': 'synthetic_known_flaw_benchmark', 'seeds': SEEDS,
              'calls_per_fixture_seed_arm': CALLS, 'oracle_and_fixture_controls': controls,
              'arms': arms, 'gates': gates, 'source_sha256': hashes,
              'elapsed_seconds': time.monotonic() - started}
    Path(__file__).with_name('expanded-results.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'controls': controls, 'off': off, 'on': on, 'gates': gates,
                      'elapsed_seconds': result['elapsed_seconds']}, indent=2))


if __name__ == '__main__':
    main()

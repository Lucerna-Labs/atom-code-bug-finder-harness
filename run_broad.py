#!/usr/bin/env python3
"""Reproduce the frozen broader synthetic benchmark with two matched arms."""
import hashlib
import json
import platform
import sqlite3
import time
import zlib
from pathlib import Path
from broad_targets import FAMILIES, SCHEDULES, Targets
from broad_properties import validate, violation
from run_expanded import Choices

SEEDS = (211, 307, 419, 503, 607)
CALLS = 1000
SOURCES = ('run_broad.py', 'broad_targets.py', 'broad_properties.py', 'run_expanded.py',
           'expanded_fixtures.py', 'BROAD-PRECOMMIT.md')


def hashes():
    return {name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
            for name in SOURCES}


def generate(family, source):
    pick = source.choose
    if family == 'sql':
        return (pick(('alice', 'bob', 'x')) + pick(('', "'")) + pick(('', ' OR ', ' AND '))
                + pick(('', '1=1', '1=0')) + pick(('', ' --')))
    if family == 'html':
        if pick((False, True)):
            return pick(('hello', '1 < 2', '&lt;script&gt;demo'))
        tag = pick(('p', 'b', 'script', 'img', 'span'))
        attr = pick(('', 'src=x', 'onerror=demo()', 'onload=demo()'))
        return f'<{tag} {attr}>demo</{tag}>'
    if family == 'mass_assignment':
        body = {'name': pick(('Alice', 'Bob', 'Guest'))}
        if pick((False, True)):
            body['role'] = pick(('user', 'admin', 'owner'))
        return body
    if family == 'secret_error':
        return {'fail': pick((False, True)), 'debug': pick((False, True))}
    if family == 'packet':
        return {'declared': pick((0, 1, 2, 8, 16, 255, 1024, 65535)),
                'header_bytes': pick((0, 1, 2)), 'body': 'a' * pick((0, 1, 2, 8, 16))}
    if family == 'decompression':
        return {'count': pick((0, 8, 64, 1024, 1025, 4096, 8192)),
                'pattern': pick(('a', 'b')), 'truncate': pick((False, True))}
    if family == 'rate_limit':
        return [pick(('a', 'b', 'c', 'd')) for _ in range(pick(tuple(range(3, 13))))]
    if family == 'quota_race':
        return pick(SCHEDULES)
    if family == 'approval_edit':
        return [[pick(('submit', 'approve', 'edit', 'execute')), pick((1, 10, 100))]
                for _ in range(pick(tuple(range(4, 13))))]
    if family == 'redirect':
        return [pick(('https://trusted.test/a', 'https://trusted.test/b',
                      'http://127.0.0.1/x', 'https://other.invalid/x',
                      'https://trusted.test.other.invalid/x'))
                for _ in range(pick((1, 2, 3, 4)))]
    if family == 'unicode_alias':
        # Intentional preregistered coverage probe: this grammar cannot emit long-s.
        return pick(('visitor', 'admin', 'sysadmin', 'SYSADMIN', 'system'))
    raise ValueError(family)


def search(target, seed, family, clean, on):
    source, seen = Choices(seed, family, on), set()
    first, witness, failures, accepted, errors = None, None, 0, 0, []
    for call in range(1, CALLS + 1):
        request = generate(family, source)
        seen.add(json.dumps(request, sort_keys=True))
        try:
            output = target.evaluate(family, request, clean)
            bad = violation(family, request, output)
        except Exception as error:
            errors.append({'call': call, 'request': request, 'exception': repr(error)})
            continue
        # Generic nonempty output count only; legitimate acceptance is validated by controls.
        accepted += bool(output)
        failures += bool(bad)
        if bad and witness is None:
            first, witness = call, {'request': request, 'output': output}
    return {'seed': seed, 'family': family, 'clean': clean, 'calls': CALLS,
            'distinct_inputs': len(seen), 'failing_calls': failures, 'nonempty_outputs': accepted,
            'first_hit': first, 'witness': witness, 'errors': errors,
            'perturbations': source.perturbations,
            'max_weight_deviation': source.max_weight_deviation,
            'max_weight_sum_error': source.max_weight_sum_error}


def summarize(rows):
    vulnerable = [row for row in rows if not row['clean']]
    return {'calls': sum(r['calls'] for r in rows),
            'known_flaws': len(FAMILIES),
            'found': sorted({r['family'] for r in vulnerable if r['witness']}),
            'missed': sorted(set(FAMILIES) - {r['family'] for r in vulnerable if r['witness']}),
            'clean_alarms': sum(r['failing_calls'] for r in rows if r['clean']),
            'unexpected_exceptions': sum(len(r['errors']) for r in rows),
            'first_hit_sum_with_miss_penalty': sum(r['first_hit'] or CALLS + 1 for r in vulnerable),
            'by_family': {f: {
                'seeds_found': sum(r['witness'] is not None for r in vulnerable if r['family'] == f),
                'first_hits': [r['first_hit'] for r in vulnerable if r['family'] == f],
                'distinct_inputs_by_seed': [r['distinct_inputs'] for r in vulnerable if r['family'] == f],
            } for f in FAMILIES},
            'by_seed_first_hit_sum': {str(seed): sum(r['first_hit'] or CALLS + 1 for r in vulnerable if r['seed'] == seed)
                                      for seed in SEEDS}}


def replay(target, rows):
    serialized = json.loads(json.dumps(rows))
    total, reproduced = 0, 0
    for row in serialized:
        witness = row['witness']
        if witness is None:
            continue
        total += 1
        output = target.evaluate(row['family'], witness['request'], row['clean'])
        reproduced += (output == witness['output'] and violation(row['family'], witness['request'], output))
    return {'total': total, 'identically_reproduced': reproduced}


def main():
    start, before = time.monotonic(), hashes()
    target = Targets()
    try:
        controls, arms = validate(target), {}
        for label, on in (('off', False), ('on', True)):
            rows = [search(target, seed, family, clean, on) for seed in SEEDS
                    for family in FAMILIES for clean in (False, True)]
            arms[label] = {'runs': rows, 'summary': summarize(rows), 'replays': replay(target, rows)}
    finally:
        target.close()
    off, on = arms['off']['summary'], arms['on']['summary']
    improved = len(on['found']) > len(off['found']) or (
        len(on['found']) == len(off['found']) and
        on['first_hit_sum_with_miss_penalty'] < off['first_hit_sum_with_miss_penalty'])
    no_loss = all(on['by_family'][f]['seeds_found'] >= off['by_family'][f]['seeds_found'] for f in FAMILIES)
    after = hashes()
    checks = {
        'controls': controls['passed'] == controls['total'] == 66,
        'at_least_nine_reachable_flaws_each': all(len(set(a['summary']['found']) - {'unicode_alias'}) >= 9 for a in arms.values()),
        'zero_clean_alarms': off['clean_alarms'] == on['clean_alarms'] == 0,
        'zero_unexpected_exceptions': off['unexpected_exceptions'] == on['unexpected_exceptions'] == 0,
        'matched_budget': off['calls'] == on['calls'] == 110000,
        'all_witnesses_reproduce': all(a['replays']['total'] == a['replays']['identically_reproduced'] > 0 for a in arms.values()),
        'sources_unchanged_during_run': before == after,
        'all_eleven_known_flaws_found': len(off['found']) == len(on['found']) == 11,
        'chaos_benefit': improved and no_loss and on['clean_alarms'] == 0,
    }
    result = {'kind': 'broader_synthetic_security_benchmark', 'seeds': SEEDS,
              'calls_per_fixture_seed_arm': CALLS, 'source_sha256': after,
              'runtime': {'python': platform.python_version(), 'sqlite': sqlite3.sqlite_version,
                          'zlib': zlib.ZLIB_RUNTIME_VERSION},
              'controls': controls, 'arms': arms,
              'gates': {key: 'MEASURED' if value else 'FAILED' for key, value in checks.items()},
              'elapsed_seconds': time.monotonic() - start}
    Path(__file__).with_name('broad-results.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'off': off, 'on': on, 'gates': result['gates'],
                      'elapsed_seconds': result['elapsed_seconds']}, indent=2))


if __name__ == '__main__':
    main()

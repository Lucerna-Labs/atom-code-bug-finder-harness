#!/usr/bin/env python3
"""Fresh-process source checks, seeded witness reconstruction and direct replays."""
import hashlib
import json
from pathlib import Path
from broad_properties import validate, violation
from broad_targets import FAMILIES, Targets
from run_broad import CALLS, SEEDS, generate, summarize
from run_expanded import Choices


def main():
    receipt = Path(__file__).with_name('broad-results.json')
    result = json.loads(receipt.read_text())
    for filename, expected in result['source_sha256'].items():
        assert hashlib.sha256(receipt.with_name(filename).read_bytes()).hexdigest() == expected, filename
    assert result['seeds'] == list(SEEDS)
    count = 0
    target = Targets()
    try:
        assert validate(target) == result['controls']
        for label, arm in result['arms'].items():
            assert summarize(arm['runs']) == arm['summary']
            expected_keys = {(s, f, c) for s in SEEDS for f in FAMILIES for c in (False, True)}
            assert {(r['seed'], r['family'], r['clean']) for r in arm['runs']} == expected_keys
            assert len(arm['runs']) == len(expected_keys)
            for row in arm['runs']:
                assert not row['errors'] and row['calls'] == CALLS
                assert (row['witness'] is None) == (row['first_hit'] is None)
                assert 0 <= row['failing_calls'] <= CALLS
                if row['clean']:
                    assert row['failing_calls'] == 0 and row['witness'] is None
                source, seen = Choices(row['seed'], row['family'], label == 'on'), set()
                for call in range(1, CALLS + 1):
                    request = generate(row['family'], source)
                    seen.add(json.dumps(request, sort_keys=True))
                    if call == row['first_hit']:
                        assert request == row['witness']['request']
                assert len(seen) == row['distinct_inputs']
                assert source.perturbations == row['perturbations']
                assert source.max_weight_sum_error < 1e-12
                assert source.max_weight_deviation <= 0.3
                if row['witness'] is None:
                    continue
                request = row['witness']['request']
                output = target.evaluate(row['family'], request, row['clean'])
                assert output == row['witness']['output']
                assert violation(row['family'], request, output)
                count += 1
        assert count == sum(a['replays']['total'] for a in result['arms'].values()) == 100
    finally:
        target.close()
    verification = {
        'receipt_sha256': hashlib.sha256(receipt.read_bytes()).hexdigest(),
        'verifier_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'source_hashes_checked': len(result['source_sha256']),
        'saved_witnesses_seed_reconstructed_and_replayed': count,
        'discovery_calls_accounted_for': sum(a['summary']['calls'] for a in result['arms'].values()),
        'controls': 'passed', 'finite_race_enumeration': 'passed',
        'input_diversity_reconstructed': 'passed', 'perturbation_bounds': 'passed',
    }
    receipt.with_name('broad-verification.json').write_text(json.dumps(verification, indent=2) + '\n')
    print(json.dumps(verification, indent=2))


if __name__ == '__main__':
    main()

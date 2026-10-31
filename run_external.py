#!/usr/bin/env python3
"""Test an ordinary local program through a JSON-line target and checker."""
import argparse
import hashlib
import json
import sys
import time
from pathlib import Path
from external_grammar import ConfigError, generate, validate_grammar
from external_protocol import Pair, ProtocolError
from run_expanded import Choices

HARNESS_SOURCES = ('run_external.py', 'external_protocol.py', 'external_grammar.py',
                   'run_expanded.py', 'expanded_fixtures.py')


def digest(value):
    wire = json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                      allow_nan=False).encode()
    return hashlib.sha256(wire).hexdigest()


def source_hashes(config):
    return {str(path): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in config['source_paths']}


def harness_hashes():
    base = Path(__file__).resolve().parent
    return {name: hashlib.sha256((base / name).read_bytes()).hexdigest()
            for name in HARNESS_SOURCES}


def load_config(path):
    raw = json.loads(path.read_text())
    if not isinstance(raw, dict) or not isinstance(raw.get('name'), str) or not raw['name']:
        raise ConfigError('config requires a nonempty name')
    base = path.parent
    cwd = (base / raw.get('cwd', '.')).resolve()
    if not cwd.is_dir():
        raise ConfigError('config cwd is not a directory')
    for key in ('target_command', 'checker_command'):
        command = raw.get(key)
        if not isinstance(command, list) or not command or any(not isinstance(s, str) or not s for s in command):
            raise ConfigError(f'{key} must be a nonempty argument array')
    seeds, calls, timeout = raw.get('seeds'), raw.get('calls_per_seed'), raw.get('timeout_seconds')
    if (not isinstance(seeds, list) or not 1 <= len(seeds) <= 20 or
            any(type(seed) is not int for seed in seeds) or len(set(seeds)) != len(seeds)):
        raise ConfigError('seeds must be 1..20 distinct integers')
    if type(calls) is not int or not 1 <= calls <= 100_000:
        raise ConfigError('calls_per_seed must be 1..100000')
    if type(timeout) not in (int, float) or not 0 < timeout <= 30:
        raise ConfigError('timeout_seconds must be in (0, 30]')
    sources = raw.get('source_paths')
    if not isinstance(sources, list) or not sources or any(not isinstance(s, str) for s in sources):
        raise ConfigError('source_paths must list target and checker source files')
    resolved = [(base / source).resolve() for source in sources]
    if any(not file.is_file() for file in resolved):
        raise ConfigError('a declared source file does not exist')
    controls = raw.get('controls')
    if not isinstance(controls, list) or not controls:
        raise ConfigError('at least one labeled control is required')
    for control in controls:
        if not isinstance(control, dict) or 'request' not in control or type(control.get('violation')) is not bool:
            raise ConfigError('controls need request and boolean violation')
    validate_grammar(raw.get('grammar'))
    return {**raw, 'cwd': cwd, 'source_paths': resolved, 'config_path': str(path)}


def invoke(config, request):
    pair = Pair(config)
    try:
        return pair.call(request)
    finally:
        pair.close()


def check_controls(config):
    rows = []
    for control in config['controls']:
        result, violated, reason = invoke(config, control['request'])
        passed = violated == control['violation']
        rows.append({'request': control['request'], 'expected': control['violation'],
                     'observed': violated, 'passed': passed,
                     'result_sha256': digest(result), 'reason': reason})
    if not all(row['passed'] for row in rows):
        raise ProtocolError('labeled control failed; discovery was not started')
    return rows


def run_seed(config, seed, on):
    source = Choices(seed, config['name'], on)
    pair = Pair(config)
    first, witness, findings = None, None, 0
    seen = set()
    try:
        for call in range(1, config['calls_per_seed']+1):
            request = generate(config['grammar'], source)
            seen.add(digest(request))
            result, violated, reason = pair.call(request)
            findings += violated
            if violated and witness is None:
                first = call
                witness = {'request': request, 'result_sha256': digest(result),
                           'reason': reason}
    finally:
        pair.close()
    return {'seed': seed, 'calls': config['calls_per_seed'], 'first_hit': first,
            'finding_calls': findings, 'distinct_inputs': len(seen), 'witness': witness,
            'perturbations': source.perturbations,
            'max_weight_deviation': source.max_weight_deviation,
            'max_weight_sum_error': source.max_weight_sum_error}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    started = time.monotonic()
    path = args.config.resolve()
    config = load_config(path)
    config_before = hashlib.sha256(path.read_bytes()).hexdigest()
    before = source_hashes(config)
    harness_before = harness_hashes()
    controls = check_controls(config)
    arms = {}
    for label, on in (('off', False), ('on', True)):
        arms[label] = [run_seed(config, seed, on) for seed in config['seeds']]
    replays = []
    for label, rows in arms.items():
        for row in rows:
            witness = row['witness']
            if witness is None:
                continue
            result, violated, _ = invoke(config, witness['request'])
            replays.append({'arm': label, 'seed': row['seed'],
                            'identical_violation': violated and digest(result) == witness['result_sha256']})
    after = source_hashes(config)
    harness_after = harness_hashes()
    config_after = hashlib.sha256(path.read_bytes()).hexdigest()
    budget = config['calls_per_seed'] * len(config['seeds'])
    scores = {label: sum(row['first_hit'] or config['calls_per_seed']+1 for row in rows)
              for label, rows in arms.items()}
    on_has_no_seed_loss = all(on['first_hit'] is not None or off['first_hit'] is None
                              for off, on in zip(arms['off'], arms['on']))
    gates = {name: 'MEASURED' if passed else 'FAILED' for name, passed in {
        'labeled_controls': all(row['passed'] for row in controls),
        'matched_budget': all(sum(row['calls'] for row in rows) == budget for rows in arms.values()),
        'all_witnesses_replay_identically': bool(replays) and all(r['identical_violation'] for r in replays),
        'source_unchanged': before == after,
        'config_unchanged': config_before == config_after,
        'harness_unchanged': harness_before == harness_after,
        'perturbation_bounds': all(row['max_weight_sum_error'] < 1e-12 and
                                   row['max_weight_deviation'] <= 0.3
                                   for rows in arms.values() for row in rows),
        'chaos_benefit': scores['on'] < scores['off'] and on_has_no_seed_loss,
    }.items()}
    report = {'kind': 'ordinary_code_process_boundary', 'name': config['name'],
              'config_sha256': config_after,
              'sources_sha256': after, 'harness_sha256': harness_after,
              'seeds': config['seeds'], 'calls_per_seed': config['calls_per_seed'],
              'controls': controls, 'arms': arms, 'replays': replays, 'scores': scores,
              'gates': gates, 'elapsed_seconds': time.monotonic()-started}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False)+'\n')
    print(json.dumps({'name': report['name'], 'scores': scores, 'gates': gates,
                      'first_hits': {label: [r['first_hit'] for r in rows] for label, rows in arms.items()},
                      'receipt': str(args.output)}, indent=2))


if __name__ == '__main__':
    try:
        main()
    except (ConfigError, ProtocolError, OSError, ValueError) as error:
        print(f'external benchmark stopped: {error}', file=sys.stderr)
        raise SystemExit(2)

#!/usr/bin/env python3
"""Check a copied ordinary program outside the benchmark repository and timeout cleanup."""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / 'examples/ordinary_code'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    with tempfile.TemporaryDirectory(prefix='ordinary-code-boundary-') as temporary:
        project = Path(temporary)
        files = ('program.py', 'target_jsonl.py', 'checker_jsonl.py')
        for name in files:
            (project / name).write_bytes((EXAMPLE / name).read_bytes())
        config = json.loads((EXAMPLE / 'config.json').read_text())
        config_path = project / 'config.json'
        config_path.write_text(json.dumps(config))
        before = {name: sha(project / name) for name in files}
        output = project / 'receipt.json'
        command = [sys.executable, str(ROOT / 'run_external.py'), '--config', str(config_path),
                   '--output', str(output)]
        result = subprocess.run(command, cwd='/', capture_output=True, text=True, timeout=20)
        assert result.returncode == 0, result.stderr
        receipt = json.loads(output.read_text())
        assert receipt['gates']['labeled_controls'] == 'MEASURED'
        assert receipt['gates']['matched_budget'] == 'MEASURED'
        assert receipt['gates']['all_witnesses_replay_identically'] == 'MEASURED'
        assert receipt['gates']['source_unchanged'] == 'MEASURED'
        assert all(row['witness'] for rows in receipt['arms'].values() for row in rows)
        assert {name: sha(project / name) for name in files} == before

        (project / 'hang.py').write_text('import os,time\nfrom pathlib import Path\nPath("hang.pid").write_text(str(os.getpid()))\ntime.sleep(10)\n')
        config['target_command'] = [sys.executable, 'hang.py']
        config['timeout_seconds'] = 0.2
        config['source_paths'].append('hang.py')
        config_path.write_text(json.dumps(config))
        timed = subprocess.run(command, cwd='/', capture_output=True, text=True, timeout=5)
        assert timed.returncode == 2 and 'timed out' in timed.stderr, timed.stderr
        pid = int((project / 'hang.pid').read_text())
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            pass
        else:
            raise AssertionError('timed-out target process was left running')

        config = json.loads((EXAMPLE / 'config.json').read_text())
        config['controls'][-1]['violation'] = False
        config_path.write_text(json.dumps(config))
        bad_control = subprocess.run(command, cwd='/', capture_output=True, text=True, timeout=5)
        assert bad_control.returncode == 2 and 'labeled control failed' in bad_control.stderr

        (project / 'bad.py').write_text('import sys\nfor line in sys.stdin: print("{}", flush=True)\n')
        config['controls'][-1]['violation'] = True
        config['target_command'] = [sys.executable, 'bad.py']
        config['source_paths'].append('bad.py')
        config_path.write_text(json.dumps(config))
        bad_protocol = subprocess.run(command, cwd='/', capture_output=True, text=True, timeout=5)
        assert bad_protocol.returncode == 2 and 'lacks result' in bad_protocol.stderr
        print('External ordinary-code process, controls, 1,000 calls, fresh replays, source hashes, timeout cleanup, and fail-closed inputs: passed')


if __name__ == '__main__':
    main()

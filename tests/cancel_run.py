#!/usr/bin/env python3
"""Verify cancellation cleans a stalled target child and releases the run lock."""
import json
import os
import time
import tempfile
from pathlib import Path
from secrets import token_hex
from job_service import JobService, CONFIGS


def main():
    service = JobService()
    identifier = 'cancelprobe' + token_hex(4)
    config_path = CONFIGS / (identifier + '.json')
    with tempfile.TemporaryDirectory(prefix='chaos-cancel-') as temporary:
        folder = Path(temporary)
        target = folder / 'target.py'
        checker = folder / 'checker.py'
        target.write_text('import os,time,sys\nfrom pathlib import Path\nPath("child.pid").write_text(str(os.getpid()))\nfor line in sys.stdin: time.sleep(10)\n')
        checker.write_text('import sys,json\nfor line in sys.stdin: print(json.dumps({"violation":False}),flush=True)\n')
        config = {
            'name': identifier, 'cwd': str(folder),
            'target_command': ['python3', str(target)], 'checker_command': ['python3', str(checker)],
            'source_paths': [str(target), str(checker)], 'timeout_seconds': 30,
            'seeds': [11], 'calls_per_seed': 100,
            'grammar': {'type': 'enum', 'values': [1]},
            'controls': [{'request': 1, 'violation': False}],
        }
        config_path.write_text(json.dumps(config))
        try:
            run = service.start_run(identifier)
            pid_path = folder / 'child.pid'
            for _ in range(100):
                if pid_path.exists(): break
                time.sleep(.02)
            assert pid_path.exists(), service.get_run(run['id'])
            child_pid = int(pid_path.read_text())
            service.cancel_run(run['id'])
            for _ in range(150):
                try: os.kill(child_pid, 0)
                except ProcessLookupError: break
                time.sleep(.02)
            else: raise AssertionError('cancelled target process survived')
            for _ in range(100):
                if service.active_run is None: break
                time.sleep(.02)
            assert service.get_run(run['id'])['state'] == 'cancelled'
            assert service.active_run is None
            print('Cancellation terminated stalled target, marked run cancelled, and released lock')
        finally:
            config_path.unlink(missing_ok=True)


if __name__ == '__main__':
    main()

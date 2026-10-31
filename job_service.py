"""Shared local job catalog for the browser and AI tools."""
import hashlib
import fcntl
import json
import os
import re
import signal
import subprocess
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from secrets import token_hex
from run_external import load_config

ROOT = Path(__file__).resolve().parent
CONFIGS = ROOT / 'configs'
RUNS = ROOT / 'runs'
EXAMPLE = ROOT / 'examples/ordinary_code/config.json'
SLUG = re.compile(r'^[a-z][a-z0-9_-]{0,63}$')


def now():
    return datetime.now(timezone.utc).isoformat()


def save_json(path, value):
    temporary = path.with_name(path.name + '.tmp-' + token_hex(4))
    with temporary.open('x') as handle:
        os.chmod(temporary, 0o600)
        json.dump(value, handle, indent=2, ensure_ascii=False)
        handle.write('\n')
    temporary.replace(path)


class JobService:
    def __init__(self):
        os.umask(0o077)
        CONFIGS.mkdir(mode=0o700, exist_ok=True)
        RUNS.mkdir(mode=0o700, exist_ok=True)
        self.active_lock = (RUNS / 'active.lock').open('a+')
        os.chmod(RUNS / 'active.lock', 0o600)
        self.lock = threading.RLock()
        self.processes = {}
        self.active_run = None

    def config_path(self, identifier):
        if identifier == 'example':
            return EXAMPLE
        if not isinstance(identifier, str) or not SLUG.fullmatch(identifier):
            raise ValueError('invalid config id')
        path = CONFIGS / (identifier + '.json')
        if path.is_symlink() or not path.is_file():
            raise ValueError('config not found')
        return path

    def list_configs(self):
        result = []
        for identifier, path in [('example', EXAMPLE)] + [
                (p.stem, p) for p in sorted(CONFIGS.glob('*.json')) if SLUG.fullmatch(p.stem) and not p.is_symlink()]:
            try:
                validated = load_config(path)
                result.append({'id': identifier, 'name': validated['name'],
                               'path': str(path), 'valid': True})
            except (OSError, ValueError, KeyError) as error:
                result.append({'id': identifier, 'name': identifier, 'path': str(path),
                               'valid': False, 'error': str(error)})
        return result

    def get_config(self, identifier):
        path = self.config_path(identifier)
        return {'id': identifier, 'config': json.loads(path.read_text()),
                'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}

    def create_config(self, identifier, config):
        if not isinstance(identifier, str) or identifier == 'example' or not SLUG.fullmatch(identifier):
            raise ValueError('config id must start with a letter and contain only letters, numbers, - or _')
        if not isinstance(config, dict):
            raise ValueError('config must be a JSON object')
        path = CONFIGS / (identifier + '.json')
        with self.lock:
            if path.exists() or path.is_symlink():
                raise ValueError('config id already exists')
            # Validate paths relative to the final location before publishing.
            temporary = CONFIGS / ('.draft-' + token_hex(8) + '.json')
            try:
                save_json(temporary, config)
                # A draft has the same parent as the final config.
                load_config(temporary)
                temporary.replace(path)
            finally:
                temporary.unlink(missing_ok=True)
        return self.get_config(identifier)

    def status_path(self, run_id):
        if not isinstance(run_id, str) or not re.fullmatch(r'[0-9a-f]{20}', run_id):
            raise ValueError('invalid run id')
        return RUNS / (run_id + '.status.json')

    def get_run(self, run_id):
        path = self.status_path(run_id)
        if not path.is_file() or path.is_symlink():
            raise ValueError('run not found')
        return json.loads(path.read_text())

    def list_runs(self):
        rows = []
        for path in RUNS.glob('*.status.json'):
            try:
                rows.append(json.loads(path.read_text()))
            except (OSError, ValueError):
                continue
        return sorted(rows, key=lambda row: row.get('started_at', ''), reverse=True)[:100]

    def _release_active(self):
        self.active_run = None
        fcntl.flock(self.active_lock, fcntl.LOCK_UN)

    def receipt(self, run_id):
        run = self.get_run(run_id)
        if run['state'] != 'succeeded':
            raise ValueError('receipt is available after a successful run')
        path = RUNS / (run_id + '.receipt.json')
        return json.loads(path.read_text())

    def start_run(self, config_id):
        config_path = self.config_path(config_id)
        load_config(config_path)
        with self.lock:
            if self.active_run is not None:
                raise ValueError('one run is already active')
            try:
                fcntl.flock(self.active_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as error:
                raise ValueError('another GUI or AI process already has an active run') from error
            run_id = token_hex(10)
            status = {'id': run_id, 'config_id': config_id, 'state': 'starting',
                      'started_at': now(), 'finished_at': None, 'exit_code': None}
            try:
                save_json(self.status_path(run_id), status)
                self.active_run = run_id
                thread = threading.Thread(target=self._execute, args=(run_id, config_path), daemon=True)
                thread.start()
            except Exception:
                self._release_active()
                raise
            return status

    def _execute(self, run_id, config_path):
        receipt = RUNS / (run_id + '.receipt.json')
        log_path = RUNS / (run_id + '.log')
        try:
            with log_path.open('x') as log:
                os.chmod(log_path, 0o600)
                with self.lock:
                    status = self.get_run(run_id)
                    if status['state'] == 'cancelled':
                        self._release_active()
                        return
                    process = subprocess.Popen(
                        [sys.executable, str(ROOT / 'run_external.py'), '--config', str(config_path),
                         '--output', str(receipt)], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
                        start_new_session=True)
                    self.processes[run_id] = process
                    status.update(state='running', pid=process.pid)
                    save_json(self.status_path(run_id), status)
                code = process.wait()
            with self.lock:
                status = self.get_run(run_id)
                if status['state'] != 'cancelled':
                    status.update(state='succeeded' if code == 0 and receipt.is_file() else 'failed',
                                  finished_at=now(), exit_code=code)
                    save_json(self.status_path(run_id), status)
                self.processes.pop(run_id, None)
                self._release_active()
        except Exception as error:
            with self.lock:
                process = self.processes.get(run_id)
                if process is not None and process.poll() is None:
                    os.killpg(process.pid, signal.SIGTERM)
                status = self.get_run(run_id)
                status.update(state='failed', finished_at=now(), error=str(error))
                save_json(self.status_path(run_id), status)
                self.processes.pop(run_id, None)
                self._release_active()

    def cancel_run(self, run_id):
        with self.lock:
            status = self.get_run(run_id)
            if status['state'] not in ('starting', 'running'):
                raise ValueError('run is not active')
            process = self.processes.get(run_id)
            if process is not None and process.poll() is None:
                os.killpg(process.pid, signal.SIGTERM)
            status.update(state='cancelled', finished_at=now())
            save_json(self.status_path(run_id), status)
            return status

    def log_tail(self, run_id, limit=3000):
        self.get_run(run_id)
        path = RUNS / (run_id + '.log')
        if not path.is_file():
            return ''
        with path.open('rb') as handle:
            handle.seek(max(0, path.stat().st_size-limit))
            return handle.read().decode(errors='replace')

    def shutdown(self):
        with self.lock:
            run_id = self.active_run
            if run_id is not None:
                try:
                    self.cancel_run(run_id)
                except ValueError:
                    pass

"""Bounded JSON-line process adapter for trusted local programs."""
import json
import os
import select
import signal
import subprocess
import time


class ProtocolError(RuntimeError):
    pass


class JsonLineProcess:
    def __init__(self, command, cwd, timeout):
        self.timeout = timeout
        self.command = command
        self.process = subprocess.Popen(
            command, cwd=cwd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, start_new_session=True)
        os.set_blocking(self.process.stdin.fileno(), False)
        self.buffer = b''

    def call(self, payload):
        wire = json.dumps(payload, separators=(',', ':'), ensure_ascii=False).encode() + b'\n'
        if len(wire) > 1_048_576:
            raise ProtocolError('request exceeds 1 MiB')
        deadline = time.monotonic() + self.timeout
        offset = 0
        while offset < len(wire):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise ProtocolError(f'command timed out reading request: {self.command[0]}')
            _, writable, _ = select.select([], [self.process.stdin], [], remaining)
            if not writable:
                raise ProtocolError(f'command timed out reading request: {self.command[0]}')
            try:
                offset += os.write(self.process.stdin.fileno(), wire[offset:])
            except BlockingIOError:
                continue
            except (BrokenPipeError, OSError) as error:
                raise ProtocolError(f'command exited before accepting request: {self.command[0]}') from error
        while b'\n' not in self.buffer:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise ProtocolError(f'command timed out after {self.timeout}s: {self.command[0]}')
            ready, _, _ = select.select([self.process.stdout], [], [], remaining)
            if not ready:
                raise ProtocolError(f'command timed out after {self.timeout}s: {self.command[0]}')
            chunk = os.read(self.process.stdout.fileno(), 65536)
            if not chunk:
                raise ProtocolError(f'command closed stdout (exit {self.process.poll()}): {self.command[0]}')
            self.buffer += chunk
            if len(self.buffer) > 1_048_576:
                raise ProtocolError('response exceeds 1 MiB')
        line, self.buffer = self.buffer.split(b'\n', 1)
        try:
            value = json.loads(line)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ProtocolError(f'command returned invalid JSON: {self.command[0]}') from error
        if not isinstance(value, dict):
            raise ProtocolError('response must be a JSON object')
        return value

    def close(self):
        if self.process.poll() is not None:
            return
        try:
            self.process.stdin.close()
            self.process.wait(timeout=0.5)
        except (OSError, subprocess.TimeoutExpired):
            try:
                os.killpg(self.process.pid, signal.SIGTERM)
                self.process.wait(timeout=1)
            except (ProcessLookupError, subprocess.TimeoutExpired):
                if self.process.poll() is None:
                    os.killpg(self.process.pid, signal.SIGKILL)
                    self.process.wait(timeout=1)


class Pair:
    def __init__(self, config):
        self.target = JsonLineProcess(config['target_command'], config['cwd'], config['timeout_seconds'])
        try:
            self.checker = JsonLineProcess(config['checker_command'], config['cwd'], config['timeout_seconds'])
        except Exception:
            self.target.close()
            raise

    def call(self, request):
        target_message = self.target.call({'request': request})
        if 'result' not in target_message:
            raise ProtocolError('target response lacks result')
        result = target_message['result']
        checker_message = self.checker.call({'request': request, 'result': result})
        if type(checker_message.get('violation')) is not bool:
            raise ProtocolError('checker response lacks boolean violation')
        reason = checker_message.get('reason', '')
        if not isinstance(reason, str) or len(reason) > 1000:
            raise ProtocolError('checker reason must be a short string')
        return result, checker_message['violation'], reason

    def close(self):
        self.checker.close()
        self.target.close()

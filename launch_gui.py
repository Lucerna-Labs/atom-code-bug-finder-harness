#!/usr/bin/env python3
"""Start or reuse the local GUI, then open it in the default browser."""
import argparse
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
URL = 'http://127.0.0.1:8765'


def healthy():
    try:
        with urllib.request.urlopen(URL + '/api/health', timeout=0.5) as response:
            return json.load(response).get('app') == 'chaos-security-benchmark'
    except (OSError, ValueError):
        return False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--no-browser', action='store_true', help='Start server without opening the browser')
    args = parser.parse_args()
    if not healthy():
        (ROOT / 'runs').mkdir(mode=0o700, exist_ok=True)
        log_path = ROOT / 'runs/launcher.log'
        with log_path.open('ab') as log:
            process = subprocess.Popen([sys.executable, str(ROOT / 'web_app.py'), '--port', '8765'],
                                       cwd=ROOT, stdin=subprocess.DEVNULL, stdout=log,
                                       stderr=subprocess.STDOUT, start_new_session=True)
        for _ in range(50):
            if healthy():
                break
            if process.poll() is not None:
                raise SystemExit(f'GUI server exited with status {process.returncode}; see {log_path}')
            time.sleep(0.1)
        else:
            raise SystemExit('GUI did not become healthy; port 8765 may be occupied')
    if not args.no_browser:
        if not webbrowser.open(URL):
            print(URL)
    print(URL)


if __name__ == '__main__':
    main()

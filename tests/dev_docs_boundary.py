#!/usr/bin/env python3
"""Check the built-in developer docs through their render and HTTP boundaries."""
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from dev_docs import PAGES, inline, markdown_to_html, render

ROOT = Path(__file__).resolve().parents[1]


def main():
    assert len(PAGES) == 7
    assert '&lt;script&gt;' in inline('<script>')
    assert '<script>' not in markdown_to_html('# <script>')
    for slug, title, _ in PAGES:
        page = render(slug)
        assert '<article>' in page and f'<title>{title} · Chaos Security Benchmark</title>' in page
        assert f'href="/dev-docs/{slug}" class="selected"' in page
        assert '<h1>' in page and '{{' not in page

    server = subprocess.Popen([sys.executable, str(ROOT/'web_app.py'), '--port', '0'],
                              cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        announcement = server.stdout.readline().strip()
        assert announcement.startswith('Chaos Security Benchmark: http://127.0.0.1:'), announcement
        base = announcement.split(': ', 1)[1]
        with urllib.request.urlopen(base+'/', timeout=3) as response:
            assert b'href="/dev-docs"' in response.read()
        with urllib.request.urlopen(base+'/dev-docs', timeout=3) as response:
            assert b'Developer overview' in response.read()
        for slug, title, _ in PAGES:
            with urllib.request.urlopen(base+'/dev-docs/'+slug, timeout=3) as response:
                body = response.read().decode()
                assert response.status == 200 and title in body
                assert 'Back to app' in body and '<nav aria-label="Developer documents">' in body
        with urllib.request.urlopen(base+'/docs.css', timeout=3) as response:
            assert b'article h1' in response.read()
        for path in ('/dev-docs/missing', '/dev-docs/%2e%2e'):
            try:
                urllib.request.urlopen(base+path, timeout=3)
            except urllib.error.HTTPError as error:
                assert error.code == 404
            else:
                raise AssertionError('unknown developer document was served')
        print('Seven developer documents, app navigation, safe renderer, CSS and 404 routes: passed')
    finally:
        server.terminate()
        assert server.wait(timeout=3) in (0, -15)


if __name__ == '__main__':
    main()

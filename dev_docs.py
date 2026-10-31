"""Read and safely render the checked-in developer documents."""
import html
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DOCS = ROOT / 'docs'

PAGES = (
    ('overview', 'Overview', 'What the benchmark is and what its results mean'),
    ('architecture', 'Architecture', 'Code ownership and run data flow'),
    ('development', 'Development guide', 'Run, extend and verify the project'),
    ('experiment', 'Experiment method', 'Controls, arms, gates and evidence'),
    ('portable', 'Portable projects', 'ZIP import, export and dependency limits'),
    ('interfaces', 'GUI and AI interfaces', 'HTTP, MCP and job lifecycle'),
    ('limits', 'Limits and next proof', 'Known gaps and stronger acceptance'),
)


def catalog():
    return [{'id': slug, 'title': title, 'summary': summary} for slug, title, summary in PAGES]


def inline(text):
    escaped = html.escape(text)
    return re.sub(r'`([^`]+)`', r'<code>\1</code>', escaped)


def markdown_to_html(source):
    result = []
    current_list = None
    in_code = False
    for line in source.splitlines():
        if line.startswith('```'):
            if current_list:
                result.append(f'</{current_list}>')
                current_list = None
            result.append('</code></pre>' if in_code else '<pre><code>')
            in_code = not in_code
            continue
        if in_code:
            result.append(html.escape(line) + '\n')
            continue
        if not line.strip():
            if current_list:
                result.append(f'</{current_list}>')
                current_list = None
            continue
        match = re.match(r'^(#{1,3}) (.+)$', line)
        if match:
            if current_list:
                result.append(f'</{current_list}>')
                current_list = None
            level = len(match.group(1))
            result.append(f'<h{level}>{inline(match.group(2))}</h{level}>')
            continue
        bullet = line.startswith('- ')
        ordered = bool(re.match(r'^\d+\. ', line))
        if bullet or ordered:
            kind = 'ul' if bullet else 'ol'
            if current_list != kind:
                if current_list:
                    result.append(f'</{current_list}>')
                result.append(f'<{kind}>')
                current_list = kind
            content = line[2:] if bullet else re.sub(r'^\d+\. ', '', line)
            result.append(f'<li>{inline(content)}</li>')
            continue
        if current_list:
            result.append(f'</{current_list}>')
            current_list = None
        result.append(f'<p>{inline(line)}</p>')
    if current_list:
        result.append(f'</{current_list}>')
    if in_code:
        result.append('</code></pre>')
    return '\n'.join(result)


def render(slug):
    match = next(((name, title, summary) for name, title, summary in PAGES if name == slug), None)
    if match is None:
        raise ValueError('developer document not found')
    source = (DOCS / (slug + '.md')).read_text()
    template = (ROOT / 'web/dev_docs.html').read_text()
    nav = '\n'.join(
        f'<a href="/dev-docs/{name}" class="{"selected" if name == slug else ""}">'
        f'<span>{html.escape(title)}</span><small>{html.escape(summary)}</small></a>'
        for name, title, summary in PAGES)
    return (template.replace('{{NAV}}', nav)
                    .replace('{{TITLE}}', html.escape(match[1]))
                    .replace('{{BODY}}', markdown_to_html(source)))

"""Independent observable security properties and manually labeled controls."""
from html.parser import HTMLParser
from itertools import permutations
from urllib.parse import urlsplit
from broad_targets import FAMILIES, SECRET


class ActiveMarkup(HTMLParser):
    def __init__(self):
        super().__init__()
        self.active = False

    def handle_starttag(self, tag, attrs):
        self.active |= tag in ('script', 'iframe') or any(key.startswith('on') for key, _ in attrs)


def violation(family, request, output):
    if family == 'sql':
        return any(tenant != 1 for tenant in output)
    if family == 'html':
        parser = ActiveMarkup()
        parser.feed(output)
        parser.close()
        return parser.active
    if family == 'mass_assignment':
        return output['role'] != 'user'
    if family == 'secret_error':
        return SECRET in output['body']
    if family == 'packet':
        return output['accepted'] and len(bytes.fromhex(output['body_hex'])) != output['declared']
    if family == 'decompression':
        return output['accepted'] and output['size'] > 1024
    if family == 'rate_limit':
        return sum(output) > 3
    if family == 'quota_race':
        return output['spent'] > 1 or output['balance'] < 0
    if family == 'approval_edit':
        latest, revision, approval = None, 0, None
        for (op, value), event in zip(request, output):
            if op == 'submit' or (op == 'edit' and latest is not None):
                latest, revision, approval = value, revision + 1, None
            elif op == 'approve' and latest is not None:
                approval = (revision, latest)
            elif op == 'execute' and event['executed']:
                if approval != (event['version'], event['amount']):
                    return True
        return False
    if family == 'redirect':
        return output is not None and urlsplit(output).hostname != 'trusted.test'
    if family == 'unicode_alias':
        return output == 'sysadmin'
    raise ValueError(family)


def controls():
    # Each entry: bad request, manually bad output, legitimate request/output.
    bad_approval = [['submit', 10], ['approve', 0], ['edit', 100], ['execute', 0]]
    good_approval = [['submit', 10], ['approve', 0], ['execute', 0]]
    return {
        'sql': ("x' OR 1=1 --", [1, 2], 'alice', [1]),
        'html': ('<script>demo</script>', '<p><script>demo</script></p>', 'hello', '<p>hello</p>'),
        'mass_assignment': ({'name': 'Alice', 'role': 'admin'}, {'name': 'Alice', 'role': 'admin'},
                            {'name': 'Alice'}, {'name': 'Alice', 'role': 'user'}),
        'secret_error': ({'fail': True, 'debug': True}, {'status': 500, 'body': SECRET},
                         {'fail': False, 'debug': False}, {'status': 200, 'body': 'ok'}),
        'packet': ({'declared': 8, 'header_bytes': 2, 'body': 'a'},
                   {'accepted': True, 'declared': 8, 'body_hex': '61'},
                   {'declared': 1, 'header_bytes': 2, 'body': 'a'},
                   {'accepted': True, 'declared': 1, 'body_hex': '61'}),
        'decompression': ({'count': 8192, 'pattern': 'a', 'truncate': False},
                          {'accepted': True, 'size': 8192},
                          {'count': 8, 'pattern': 'a', 'truncate': False},
                          {'accepted': True, 'size': 8}),
        'rate_limit': (['a', 'b', 'c', 'd'], [True]*4, ['a', 'a'], [True, True]),
        'quota_race': ('ABAB', {'spent': 2, 'balance': -1}, 'AABB', {'spent': 1, 'balance': 0}),
        'approval_edit': (bad_approval,
                          [{'executed': False, 'amount': 10, 'version': 1},
                           {'executed': False, 'amount': 10, 'version': 1},
                           {'executed': False, 'amount': 100, 'version': 2},
                           {'executed': True, 'amount': 100, 'version': 2}],
                          good_approval,
                          [{'executed': False, 'amount': 10, 'version': 1},
                           {'executed': False, 'amount': 10, 'version': 1},
                           {'executed': True, 'amount': 10, 'version': 1}]),
        'redirect': (['https://trusted.test/a', 'http://127.0.0.1/x'], 'http://127.0.0.1/x',
                     ['https://trusted.test/a'], 'https://trusted.test/a'),
        'unicode_alias': ('\u017fysadmin', 'sysadmin', 'visitor', 'visitor'),
    }


def validate(target):
    checks = []
    for family, (bad, bad_output, good, good_output) in controls().items():
        checks.extend((violation(family, bad, bad_output),
                       not violation(family, good, good_output),
                       violation(family, bad, target.evaluate(family, bad, False)),
                       not violation(family, bad, target.evaluate(family, bad, True))))
        checks.extend(target.evaluate(family, good, clean) == good_output for clean in (False, True))
    if not all(checks):
        raise RuntimeError(f'Oracle/fixture controls failed: {sum(checks)}/{len(checks)}')
    schedules = sorted({''.join(order) for order in permutations('AABB')})
    exhaustive = [{'schedule': schedule,
                   'vulnerable_violation': violation('quota_race', schedule, target.evaluate('quota_race', schedule, False)),
                   'clean_violation': violation('quota_race', schedule, target.evaluate('quota_race', schedule, True))}
                  for schedule in schedules]
    if len(schedules) != 6 or sum(r['vulnerable_violation'] for r in exhaustive) != 4 or any(r['clean_violation'] for r in exhaustive):
        raise RuntimeError('Exhaustive finite race validation failed')
    return {'passed': sum(checks), 'total': len(checks), 'exhaustive_race': exhaustive}

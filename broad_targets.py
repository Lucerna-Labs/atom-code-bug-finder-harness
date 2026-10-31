"""Authored vulnerable/clean fixtures. All external-looking values are local test data."""
import html
import sqlite3
import struct
import zlib
from urllib.parse import urlsplit

FAMILIES = ('sql', 'html', 'mass_assignment', 'secret_error', 'packet', 'decompression',
            'rate_limit', 'quota_race', 'approval_edit', 'redirect', 'unicode_alias')
SECRET = 'FAKE_TEST_SECRET_7F12'
SCHEDULES = ('AABB', 'ABAB', 'ABBA', 'BAAB', 'BABA', 'BBAA')


class Targets:
    def __init__(self):
        self.db = sqlite3.connect(':memory:')
        self.db.execute('CREATE TABLE records (tenant INTEGER, name TEXT)')
        self.db.executemany('INSERT INTO records VALUES (?, ?)', [(1, 'alice'), (2, 'bob')])
        self.db.commit()
        self.db.execute('PRAGMA query_only=ON')

    def close(self):
        self.db.close()

    def evaluate(self, family, request, clean):
        if family == 'sql':
            try:
                if clean:
                    rows = self.db.execute('SELECT tenant FROM records WHERE tenant=1 AND name=?', (request,))
                else:
                    rows = self.db.execute(f"SELECT tenant FROM records WHERE tenant=1 AND name='{request}'")
                return [row[0] for row in rows]
            except sqlite3.Error:
                return []  # Invalid query is an ordinary rejected request.
        if family == 'html':
            return '<p>' + (html.escape(request) if clean else request) + '</p>'
        if family == 'mass_assignment':
            profile = {'name': 'Alice', 'role': 'user'}
            profile.update({'name': request['name']} if clean else request)
            return profile
        if family == 'secret_error':
            if request['fail']:
                body = 'request failed'
                if request['debug'] and not clean:
                    body += ': configuration token=' + SECRET
                return {'status': 500, 'body': body}
            return {'status': 200, 'body': 'ok'}
        if family == 'packet':
            frame = struct.pack('!H', request['declared'])[:request['header_bytes']] + request['body'].encode()
            if len(frame) < 2:
                return {'accepted': False}
            declared = struct.unpack('!H', frame[:2])[0]
            payload = frame[2:2 + declared]
            if clean and len(payload) != declared:
                return {'accepted': False}
            return {'accepted': True, 'declared': declared, 'body_hex': payload.hex()}
        if family == 'decompression':
            compressed = zlib.compress(request['pattern'].encode() * request['count'])
            if request['truncate']:
                compressed = compressed[:-1]
            if len(compressed) > 512:
                return {'accepted': False, 'size': 0}
            try:
                if clean:
                    inflater = zlib.decompressobj()
                    output = inflater.decompress(compressed, 1025)
                    accepted = len(output) <= 1024 and inflater.eof
                else:
                    output = zlib.decompress(compressed)
                    accepted = True
                return {'accepted': accepted, 'size': len(output)}
            except zlib.error:
                return {'accepted': False, 'size': 0}
        if family == 'rate_limit':
            buckets, accepted = {}, []
            for forwarded in request:
                identity = 'socket-peer' if clean else forwarded
                count = buckets.get(identity, 0)
                accepted.append(count < 3)
                if count < 3:
                    buckets[identity] = count + 1
            return accepted
        if family == 'quota_race':
            balance, spent, phases, observed = 1, 0, {'A': 0, 'B': 0}, {}
            for worker in request:
                if phases[worker] == 0:
                    observed[worker] = balance > 0
                elif observed[worker] and (not clean or balance > 0):
                    balance -= 1
                    spent += 1
                phases[worker] += 1
            return {'spent': spent, 'balance': balance}
        if family == 'approval_edit':
            amount, version, approved, events = None, 0, None, []
            for operation, value in request:
                executed = False
                if operation == 'submit' or (operation == 'edit' and amount is not None):
                    amount, version = value, version + 1
                    if clean or operation == 'submit':
                        approved = None
                elif operation == 'approve' and amount is not None:
                    approved = (version, amount)
                elif operation == 'execute' and approved is not None:
                    executed = True
                events.append({'executed': executed, 'amount': amount, 'version': version})
            return events
        if family == 'redirect':
            urls = request if clean else request[:1]
            if any(urlsplit(url).hostname != 'trusted.test' for url in urls):
                return None
            return request[-1]
        if family == 'unicode_alias':
            checked = request.casefold() if clean else request.lower()
            return None if checked == 'sysadmin' else request.casefold()
        raise ValueError(family)

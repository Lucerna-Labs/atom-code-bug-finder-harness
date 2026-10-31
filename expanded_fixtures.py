"""Synthetic targets and independent output-property oracles. No IO or network."""
import posixpath
from urllib.parse import unquote

ROOT = '/fixture/public'
FAMILIES = ('path', 'tenant', 'overflow', 'headers', 'replay', 'expiry')


def evaluate(family, request, clean=False):
    if family == 'path':
        decoded = unquote(request)
        if decoded.startswith('../') or decoded.startswith('/'):
            return None
        result = posixpath.normpath(ROOT + '/' + unquote(decoded))
        if clean and posixpath.commonpath((ROOT, result)) != ROOT:
            return None
        return result
    if family == 'tenant':
        principal, owner, authenticated = request
        return authenticated and (principal == owner if clean else True)
    if family == 'overflow':
        count, width = request
        total = count * width
        return (total if clean else total & 65535) <= 4096
    if family == 'headers':
        lengths = [int(value) for value in request]
        if clean and len(set(lengths)) != 1:
            return None
        return lengths[0], lengths[-1]
    if family == 'replay':
        spent = set()
        result = []
        for token in request:
            accepted = token in (1, 2) and (not clean or token not in spent)
            result.append(accepted)
            if accepted:
                spent.add(token)
        return result
    if family == 'expiry':
        now, expiry, signed = request
        return signed and (now < expiry if clean else now <= expiry)
    raise ValueError(f'Unknown fixture: {family}')


def violation(family, request, output):
    """Properties inspect outputs, without calling either target implementation."""
    if family == 'path':
        return output is not None and not (output == ROOT or output.startswith(ROOT + '/'))
    if family == 'tenant':
        return bool(output) and (not request[2] or request[0] != request[1])
    if family == 'overflow':
        return bool(output) and request[0] * request[1] > 4096
    if family == 'headers':
        return output is not None and output[0] != output[1]
    if family == 'replay':
        accepted_tokens = [token for token, accepted in zip(request, output) if accepted]
        return len(accepted_tokens) != len(set(accepted_tokens))
    if family == 'expiry':
        return bool(output) and (not request[2] or request[0] >= request[1])
    raise ValueError(f'Unknown oracle: {family}')


# Manually labeled observations: one known violation and one legitimate observation.
CONTROLS = {
    'path': [('docs/../../file', '/fixture/file', True),
             ('docs/file', ROOT + '/docs/file', False)],
    'tenant': [([1, 2, True], True, True), ([1, 1, True], True, False)],
    'overflow': [([256, 256], True, True), ([2, 16], True, False)],
    'headers': [(['1', '16'], (1, 16), True), (['16', '16'], (16, 16), False)],
    'replay': [([1, 2, 1], [True, True, True], True), ([1, 2], [True, True], False)],
    'expiry': [([100, 100, True], True, True), ([99, 100, True], True, False)],
}


def validate_controls():
    checks = []
    for family, observations in CONTROLS.items():
        for request, output, expected in observations:
            checks.append(violation(family, request, output) == expected)
        bad, good = observations[0][0], observations[1][0]
        checks.append(violation(family, bad, evaluate(family, bad)))
        checks.append(not violation(family, bad, evaluate(family, bad, clean=True)))
        for clean in (False, True):
            checks.append(evaluate(family, good, clean) == observations[1][1])
    if not all(checks):
        raise RuntimeError(f'Invalid fixture/oracle controls: {sum(checks)}/{len(checks)}')
    return {'passed': sum(checks), 'total': len(checks)}

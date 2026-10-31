#!/usr/bin/env python3
"""Independent contract check; it does not import the application function."""
import json
import sys

for line in sys.stdin:
    message = json.loads(line)
    expected = sum(set(message['request']))
    observed = message['result']['total']
    failed = observed != expected
    print(json.dumps({'violation': failed,
                      'reason': 'distinct-value total differs from contract' if failed else ''}),
          flush=True)

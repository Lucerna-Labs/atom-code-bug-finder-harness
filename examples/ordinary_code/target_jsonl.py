#!/usr/bin/env python3
"""Small JSON-line wrapper around an ordinary application function."""
import json
import sys
from program import distinct_total

for line in sys.stdin:
    request = json.loads(line)['request']
    result = {'total': distinct_total(request)}
    print(json.dumps({'result': result}), flush=True)

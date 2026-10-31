# Ordinary-code adapter result

The standalone benchmark now runs a selected ordinary program through an actual local process boundary. A config supplies the input grammar, a target command, an independent checker command, labeled controls, seeds, call budget and declared source files. The two arms use the same input grammar and budget. Findings are retained only when the checker reports a contract violation; each retained request is replayed through fresh processes.

The included example is a small Python function that promises the sum of distinct numbers but counts duplicates. Its wrapper and checker live in `examples/ordinary_code/`. The checker does not import the target function.

| Measurement | Result |
| --- | ---: |
| Labeled controls | 3/3 passed |
| Target calls | 500 off, 500 on |
| Seeds finding the planted bug | 5/5 off, 5/5 on |
| First-hit sum, lower is sooner | 11 off, 7 on |
| Saved witnesses reproduced with identical outputs | 10/10 |
| Source/config drift | none |
| Protocol errors | none |

Only seed 11 improved (first hit 6→2); the other four seeds tied. The frozen narrow chaos-benefit gate passed for this one example. It does not demonstrate a general coding improvement or a general security advantage.

An integration run copied the ordinary program and config into a temporary directory **outside** the benchmark repository, invoked `run_external.py` from `/`, completed the same 1,000 target calls, replayed findings, and confirmed the copied sources were unchanged. Separate checks confirmed a stalled target timed out and was terminated, a mismatched labeled control blocked discovery, and a malformed target response was rejected. Commands run as arguments without a shell.

Run the example:

```sh
cd /home/jesse/Desktop/Projects/chaos-security-benchmark
python3 run_external.py --config examples/ordinary_code/config.json --output ordinary-code-results.json
python3 tests/external_boundary.py
```

The exact receipt is `ordinary-code-results.json`; the initial protocol and predictions were committed in `NORMAL-CODE-PRECOMMIT.md` before implementation. See `EXTERNAL-CODE.md` to connect a chosen local project. That project needs a small JSON-line wrapper and a property checker. The checker supplies the meaning of a bug; the runner cannot infer it from arbitrary source code. Process crashes and protocol failures currently abort the run rather than becoming findings. The integration test exercised a Python program on Linux; other languages can use the same JSON-line protocol but have not yet been tested here.

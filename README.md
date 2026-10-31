# Chaos Security Benchmark

The runner now accepts ordinary local code through a configurable process interface. See [EXTERNAL-CODE.md](EXTERNAL-CODE.md) for the JSON protocol, a runnable example and instructions for connecting a chosen repository.

[NORMAL-CODE-RESULT.md](NORMAL-CODE-RESULT.md) records the measured ordinary-code run and external-directory integration test.

Standalone project at `/home/jesse/Desktop/Projects/chaos-security-benchmark`, with its own Git history, synthetic fixtures, experiment protocols and saved results. Requires Python 3.10 or newer with the standard-library SQLite and zlib modules; no package installation is needed.

```sh
cd /home/jesse/Desktop/Projects/chaos-security-benchmark
python3 verify_broad.py
```

To rerun the latest benchmark, run `python3 run_broad.py` followed by `python3 verify_broad.py`. The runner replaces `broad-results.json`; the verifier replaces `broad-verification.json`. Previous committed receipts remain in Git history. Earlier suites are available through `run_demo.py`, `run_expanded.py` and `run_workflows.py`.

This project exercises deliberately vulnerable synthetic targets and clean counterparts. It is not yet a scanner for arbitrary source repositories.

Latest: [BROAD-REPORT.md](BROAD-REPORT.md) covers 220,000 additional calls across 11 planted flaws and 11 clean counterparts. Both arms found 10/11; the intentionally ASCII-only grammar missed the Unicode coverage probe. Run `python3 run_broad.py`, then `python3 verify_broad.py`.

Expanded experiment: see [EXPANDED-REPORT.md](EXPANDED-REPORT.md) for eight planted flaws, eight clean counterparts, five seeds and 320,000 target calls. Run `python3 run_expanded.py` and `python3 run_workflows.py` for those suites. Both arms found all eight flaws; chaos benefit was mixed.

Run with `python3 run_demo.py` (Python standard library only). The script writes `results.json` beside itself.

This standalone demo uses a deliberately vulnerable path resolver in a temporary directory. It accepts a request such as `docs/../../guide.txt` because it rejects only paths *starting* with `..`. The accepted result resolves outside its allowed root. This is the path traversal failure class described by [OWASP](https://community.owasp.org/attacks/Path_Traversal); Python's [`Path.resolve()`](https://docs.python.org/3/library/pathlib.html#pathlib.Path.resolve) removes `..` components.

## Measured result

| Check | Result |
| --- | ---: |
| Independent containment oracle controls | 5/5 passed |
| Plain arm | 0 violations in 9 calls |
| Chaos arm | 3 violations in 9 calls |
| Fixed seeds with a finding | 3/3 |
| Findings reproduced on unchanged target without chaos | 3/3 |

The on arm uses two logistic-map steps per variant to decide whether to insert each parent-path segment. The independent containment oracle selects and retains only verified violations, with the exact request and seed saved in `results.json`. The source target function is identical in both arms. The protocol and predictions were committed in `PRECOMMIT.md` before the executable was written (Git commit `97485ae`).

## What this shows

This is a **known synthetic flaw**. The generator was given a path grammar that includes parent segments; the chaos mechanism explores combinations within that grammar. It did not infer the security property, invent the attack class, or analyze any of Jesse's repositories. The target only resolves paths; it does not read files. A real-code trial would need a selected checkout, a real entry point, a verified property oracle, and a reproducer against the unchanged program.

# Edge-of-chaos security discovery simulation

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

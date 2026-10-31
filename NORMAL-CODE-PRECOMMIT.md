# Ordinary-code adapter: frozen before implementation

The user asked to make this standalone project work for normal coding as well as Atom. Existing synthetic benchmark results and failed gates remain unchanged. No user project was named, so implement a reusable command-line boundary and prove it against a self-contained ordinary Python program outside the benchmark engine.

## Interface

- Config JSON names a target command, an independent checker command, a working directory, a recursive bounded JSON input grammar, fixed seeds, calls per seed, timeout, labeled control inputs and source files to hash.
- Each command runs as its own persistent process and exchanges one JSON object per line. Target receives `{"request": ...}` and returns `{"result": ...}`. Checker receives `{"request": ..., "result": ...}` and returns `{"violation": true|false, "reason": "..."}`.
- Commands execute as argument arrays without a shell. Use separate fresh target/checker processes per seed and arm. A request represents one complete operation or stateful sequence. Protocol errors, timeouts and unexpected exits abort the run and remain visible; no silent skipping.
- Input grammar supports fixed JSON choices, bounded integers, fixed objects and bounded arrays. Apply the existing centered logistic-map category-weight perturbation inside every choice in the on arm. Off uses the same RNG, grammar, seeds and call budget. Plain wins ties. Keep the first checker-verified witness per seed and repeat it with fresh processes and chaos off. Save request, checker reason and output hash, not raw target output.
- Labeled control inputs must pass before discovery. Hash declared source files before and after. Save the exact config hash, per-seed results, failures, controls, source hashes and paired first-hit comparison. Do not claim automatic bug inference or broad source coverage.

## Example and acceptance

- Example ordinary program computes `sum(values)` while its stated contract is the sum of distinct values. Independent checker uses `sum(set(values))`. Config exercises bounded arrays of integers 0..5, length 0..8.
- Controls: `[]` and `[1,2]` do not violate; `[1,1]` violates. Five fixed seeds 11,23,37,41,59; 100 requests per seed per arm (1,000 target calls plus controls/replays). No selected input or target code changes after results.
- Required gates: config validation, all labeled controls, equal budgets, no protocol errors, no source drift and all saved witnesses replay identically. Report which seeds find the bug and whether the on arm strictly improves the first-hit total. A tie or loss fails the chaos benefit gate; retain failure.

This proves a reusable operational adapter at a real process boundary on ordinary code. It does not establish effectiveness on unnamed repositories or a universal security scanner.

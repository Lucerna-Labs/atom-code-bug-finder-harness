# Expanded synthetic comparison — frozen before implementation

Scope: standalone Python testing infrastructure using the edge-of-chaos method; no Atom crate or existing project is modified. Preserve the original demo and receipts.

Six deliberately vulnerable fixtures, each with a clean counterpart:
1. Path traversal through decoding and normalization.
2. Cross-tenant authorization with a missing owner check.
3. Unsigned 16-bit length arithmetic wrapping before a capacity check.
4. Conflicting duplicate length headers interpreted differently by two parsers.
5. Reuse of a one-time token across a request sequence.
6. Acceptance at a token's exclusive expiry boundary.

Independent property oracles check observable outputs; each oracle has a manually labeled violating and nonviolating observation. Direct fixture controls must additionally show each vulnerable fixture violates its property and its clean counterpart both accepts a legitimate case and refuses the violating case. Abort discovery on a bad oracle/control.

Exactly two search arms: a varied seeded ordinary generator (off), and the same generator with small per-choice logistic-map perturbations (on). Both have identical grammars, selector, seeds, calls, target and oracle. On: r=4, amplitude 0.15, center each vector of perturbations on its sample mean so total weight is preserved; vary categorical choice weights only. No target output or oracle is perturbed. Keep first independently verified witness per fixture/seed; plain wins ties. This retains evidence, not changed production code.

Five new fixed seeds: 31,47,73,101,137. Each arm makes 1,000 calls to each of 12 fixtures per seed: 60,000 calls per arm, 120,000 discovery calls total. No tuning or seed selection after results. Report unique planted flaw classes separately from repeated failing requests. Record first discovery call, failures, clean-fixture alarms, exceptions, input diversity, witnesses and their direct replays.

Predictions/gates: controls 100%; at least 5/6 planted classes found by each arm; zero alarms on six clean counterparts; every retained witness reproduces on the unchanged target without chaos; no target exceptions; exactly matched budgets. Chaos benefit is a hypothesis, not an expected pass: require more discovered classes or (if class coverage ties) a lower sum of first-hit calls, with no per-class seed detection loss or new clean alarms. A tie or regression fails the benefit gate. Missing classes and all failed gates remain recorded.

This benchmark has authored input grammars and known vulnerabilities. Even full detection is recall on six planted classes, not general flaw coverage. It does not compare against industrial fuzzers or prove a chaos advantage beyond the declared generator and fixtures.

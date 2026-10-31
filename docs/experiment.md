# Experiment method and evidence

## What the two arms do

The off arm draws from the declared input grammar using a seeded ordinary choice. The on arm uses the same grammar, seeds and call budget, but adjusts each categorical choice's weights with a small deterministic logistic-map perturbation. The perturbations are centered so their weights sum to the plain total. The target program and checker receive ordinary JSON requests; the chaos mechanism does not rewrite either one.

The runner tests labeled controls before discovery. For each seed and arm it generates `calls_per_seed` requests, obtains the target result, asks the checker whether a property was violated, and keeps the first verified witness. After both arms, it replays each saved witness through fresh processes and checks that the violation and target output hash match. If no witness exists, the replay gate is `UNRUN`; this is distinct from a failed replay. A candidate that only changes output or raises a protocol error does not become a finding.

## Why a checker matters

The checker supplies the external property. Examples include "a returned tenant must equal the requester," "a final charge cannot exceed the approved limit," or "a sum of distinct values counts each value once." The generator can only explore values admitted by its grammar. The broad synthetic benchmark intentionally omitted a Unicode character from one grammar; both arms missed that known flaw despite a direct control proving it existed. More calls could not create a missing character.

The benefit gate is separate from detection. `run_external.py` scores each arm by the sum of first-hit call numbers, with `calls_per_seed + 1` for a miss. The chaos gate passes only when on has a lower score and loses no seed where off found a witness. Other gates cover controls, equal budgets, replay, hashes and perturbation bounds. A job may complete successfully while `chaos_benefit` is `FAILED`.

## What has been measured

- The ordinary-code adapter found the planted duplicate-counting bug in all five seeds in both arms. First-hit sums were 11 off and 7 on; only one seed improved and four tied. See `NORMAL-CODE-RESULT.md`.
- The expanded synthetic six-function suite found all six planted classes in both arms, with chaos slower on its frozen first-hit score. The two stateful workflows found both classes, with a lower aggregate first-hit score on chaos but mixed individual seeds. See `EXPANDED-REPORT.md`.
- The broader eleven-fixture suite found ten reachable classes in both arms. The deliberately absent Unicode input remained missed by both; the chaos arm did not find an extra flaw class. See `BROAD-REPORT.md`.
- A separate, unintegrated `chaos-cross-chain-lab` found three planted cross-component classes, but its chaos advantage failed on held-out seeds. Its results do not change this app's claim boundary.

These are authored examples and bounded observations. They show that the runner can execute and compare declared tests. They do not show that a checker can be inferred from an uploaded app, that every bug class is covered, or that chaos generally outperforms an ordinary generator.

# Larger security discovery tests

Two frozen experiments executed 320,000 synthetic target calls: 160,000 per search arm. Both arms found all eight deliberately planted flaws across all five fixed seeds. All 80 retained witnesses reproduced with identical outputs in a fresh process. No alarms occurred in 160,000 calls to the eight clean counterparts; no target exceptions occurred. Oracle and fixture controls passed 48/48.

These are eight distinct planted defects, each found repeatedly across seeds and arms. Repeated failures are not additional vulnerabilities.

## Discovery and comparison

| Planted defect | Off: seeds finding it | On: seeds finding it |
| --- | ---: | ---: |
| Decoding/normalization path escape | 5/5 | 5/5 |
| Missing tenant ownership check | 5/5 | 5/5 |
| Length multiplication wrapping at 16 bits | 5/5 | 5/5 |
| Conflicting duplicate length headers | 5/5 | 5/5 |
| Reused one-time token | 5/5 | 5/5 |
| Exclusive expiry accepted at boundary | 5/5 | 5/5 |
| Cached access retained after revocation | 5/5 | 5/5 |
| Repeated refund after hold/capture | 5/5 | 5/5 |

The baseline generates varied structured requests using a seeded ordinary generator. The chaos arm uses the same grammar and random draws, with centered small logistic-map perturbations to category weights at every choice. Both retain the first oracle-verified witness. Each target runs independently, with state reset between sequences. No aggregate pipeline is perturbed.

| Frozen experiment | Calls per arm | Off: sum of first-hit calls | On: sum of first-hit calls | Chaos benefit gate |
| --- | ---: | ---: | ---: | --- |
| Six function fixtures and six clean counterparts | 60,000 | 116 | 125 | FAILED |
| Two stateful workflows and two clean counterparts | 100,000 | 286 | 177 | MEASURED |

The first sum covers 30 vulnerable fixture/seed pairs; the second covers 10. Lower means earlier discovery, not shorter wall-clock time. Chaos was about 7.8% worse on the six function fixtures and 38.1% better on the two workflows. These are descriptive results for the frozen seeds, not a statistical claim of general superiority. The workflow result was uneven:

| Seed | Off: first-hit sum across workflows | On: first-hit sum across workflows |
| --- | ---: | ---: |
| 31 | 148 | 25 |
| 47 | 40 | 26 |
| 73 | 14 | 38 |
| 101 | 34 | 45 |
| 137 | 50 | 43 |

Three seed pairs improved and two worsened. One large gain accounts for much of the aggregate improvement. Both experiments found the same known flaws; chaos found no additional defect class. All non-benefit gates passed, and the failed benefit result remains preserved.

## Reproduce

Run from this directory:

```sh
python3 run_expanded.py
python3 run_workflows.py
```

Python standard library only. Each command writes its corresponding JSON receipt, including all runs and retained witnesses. Receipts include source hashes. A separate fresh-process verification checked those hashes, matched budgets, varied inputs, zero clean alarms, and identical outputs for all 80 witnesses.

The six-class protocol was committed at `5620e8f` before its implementation. The stateful protocol was committed after the six-class results and before the workflow implementation. See `EXPANDED-PRECOMMIT.md`, `WORKFLOW-PRECOMMIT.md`, `expanded-results.json`, and `workflow-results.json`. Original demo files remain preserved.

## Evidence limits

This is a standalone application of the method; Jesse's existing arm was not located or integrated. Targets, request grammars and property oracles were authored for this benchmark. The tests find known violations through execution; they do not automatically infer security requirements or inspect arbitrary source code. Many easy cases saturate within 16 calls, and the workflow maximum first hit is 133, so the large budget mostly confirms repeated exploration and clean-control behavior.

The fixtures model logical boundaries, not production systems: no real HTTP parser, file IO, memory corruption, symlinks, concurrent race, remote service, or real payment is exercised. Python explicitly models the 16-bit wrap. Clean means clean against these properties and grammars. No alarms here does not prove production safety. One perturbation setting was tested; its position at a mathematical edge-of-chaos regime was not established.

The [LLVM fuzzing documentation](https://llvm.org/docs/LibFuzzer.html) describes retained inputs and coverage-guided exploration. This benchmark uses authored property oracles and no instrumented code coverage; it is not a comparison with libFuzzer. The modeled overflow weakness corresponds to [CWE-190](https://cwe.mitre.org/data/definitions/190.html).

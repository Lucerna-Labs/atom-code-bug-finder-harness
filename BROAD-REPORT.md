# Broader security benchmark results

Executed 220,000 additional search calls: 110,000 per arm, using 11 deliberately vulnerable fixtures, 11 clean counterparts and five new fixed seeds. Both arms found **10 of 11 known flaws** in all five seeds for each detected fixture. Neither arm found the Unicode alias probe. This result is deliberately reported against all 11 known flaws, including the miss.

All 100 saved witnesses reproduced with identical outputs in a fresh process. All 66 manually labeled oracle/fixture checks passed. No alarms occurred in the 110,000 clean-target search calls, and no unexpected target exceptions occurred.

## Per-fixture findings

| Known planted flaw | Off: seeds detecting | On: seeds detecting | Distinct generated requests per seed/arm |
| --- | ---: | ---: | ---: |
| SQL injection across tenants | 5/5 | 5/5 | 108 |
| Active HTML injection | 5/5 | 5/5 | 23 |
| Role mass assignment | 5/5 | 5/5 | 12 |
| Fake secret leaked by error response | 5/5 | 5/5 | 4 |
| Truncated binary packet accepted | 5/5 | 5/5 | 119–120 |
| Decompression quota bypass | 5/5 | 5/5 | 28 |
| Spoofed forwarding identity evades quota | 5/5 | 5/5 | 911–937 |
| Quota check/use race model | 5/5 | 5/5 | 6 |
| Edited request keeps stale approval | 5/5 | 5/5 | 997–1000 |
| Redirect leaves allowed origin | 5/5 | 5/5 | 333–359 |
| Unicode account alias: deliberate coverage probe | 0/5 | 0/5 | 5 |

The call count includes repeated requests; it is not the count of distinct attacks or vulnerabilities. Some grammars are small and saturate quickly. Authored controls include legitimate acceptance checks for every clean fixture, so the negative controls cannot pass by rejecting all requests.

## The known miss and the finite exhaustive test

The Unicode fixture has a real normalization disagreement: long-s in `ſysadmin` passes a lowercase-only reserved-name check, then case folding maps it to `sysadmin`. A direct control reproduces this defect and the clean target blocks it. Before implementation, the protocol deliberately restricted the discovery grammar to five ASCII names. Both arms consequently miss the defect. This is an explicit coverage-limit diagnostic, not a surprise discovery: changing weights cannot supply a character absent from the available input grammar. The failed all-11 gate is preserved.

The quota race fixture was additionally enumerated over **all six legal schedules** of two workers taking one check step and one use step each. Four schedules violate the vulnerable target’s one-unit quota; zero violate the clean target. This enumeration is exhaustive only for that specified four-step state machine. It does not exercise real threads, memory ordering, filesystems or OS scheduling.

## Does chaos help here?

The frozen aggregate first-hit score was **5394 off versus 5363 on** (lower is better). Each of the five Unicode misses contributes a fixed 1,001 penalty to each score. Chaos passes this narrow benefit gate by 31 calls; it finds no additional flaw. Per-seed totals are:

| Seed | Off score | On score |
| --- | ---: | ---: |
| 211 | 1055 | 1046 |
| 307 | 1128 | 1084 |
| 419 | 1057 | 1063 |
| 503 | 1127 | 1142 |
| 607 | 1027 | 1028 |

Two seed totals improve and three worsen. The aggregate gain is small and is not a statistical demonstration of general superiority. Earlier experiments remain mixed: the six-function benefit gate failed, while the two-workflow gate passed. No strengths, seeds, grammars, or gates were changed after this run.

## Reproduction and evidence

```sh
python3 run_broad.py
python3 verify_broad.py
```

The runner overwrites only `broad-results.json`; the verifier writes `broad-verification.json`. Python standard library only. The protocol was committed as `8f868e3` before implementation. Receipts contain source hashes, runtime versions, every seed/fixture run and the first retained witness. The separate verifier checks those hashes, reconstructs generated input diversity and exact first-witness positions from seeds, checks perturbation bounds, reruns controls and race enumeration, and invokes every saved witness directly with no chaos source.

## Scope

This is a standalone test application of the edge-of-chaos method. Jesse’s existing arm and project code have not been located or integrated. Known targets, input grammars and output properties were authored for this benchmark; the checker does not infer arbitrary source-code vulnerabilities.

SQL uses an actual in-memory SQLite database with read-only queries. Compression uses actual zlib with generated expansions bounded to 8,192 bytes. Packet parsing uses actual binary packing/unpacking. HTML is checked with an HTML parser; no browser or script execution is involved. Redirects, network identities, approval transactions and the quota race are logical models; no remote services, payments or real concurrency are exercised. Clean means clean against these particular properties.

The implementation uses [SQLite parameter binding](https://docs.python.org/3/library/sqlite3.html) and [bounded zlib decompression](https://docs.python.org/3/library/zlib.html) in the clean counterparts. The race model illustrates the check/use weakness described by [CWE-367](https://cwe.mitre.org/data/definitions/367.html). These references describe mechanisms, not independent validation of this benchmark.

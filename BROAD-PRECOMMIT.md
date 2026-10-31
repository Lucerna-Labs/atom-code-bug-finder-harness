# Broader security benchmark: frozen protocol

This extends the authorized standalone synthetic benchmark. It does not inspect any other project or claim every possible security flaw is covered. Preserve all earlier evidence, including failed chaos benefit gates.

## Eleven known flaws with eleven clean counterparts

1. SQL injection across tenants: execute actual read-only queries in an in-memory SQLite database.
2. HTML injection: text interpolation versus escaping, checked with Python's HTML parser; no browser executes scripts.
3. Role mass assignment: a profile-edit request changes a server-owned role.
4. Error response leaks a fake secret marker.
5. Truncated length-prefixed packet accepted by a binary parser.
6. Decompression output exceeds a 1,024-byte quota: actual zlib, generated output bounded to 8,192 bytes.
7. Rate limit bypass through spoofed forwarding identities in a sequence from one socket peer.
8. Check/use quota race: two simulated workers withdraw against one unit. Exhaustively validate all six legal four-step schedules separately as fixture validation; predict four violating schedules in the vulnerable target and zero in the clean target.
9. Approval invalidated by edit: execution of a changed amount retains an old approval.
10. Redirect chain escapes an origin allowlist: parsed URLs only, no network requests.
11. Unicode account alias bypass: a lower()/casefold() disagreement. Deliberately keep the search grammar ASCII-only for this explicit coverage-limit probe. The hand-written Unicode control proves the defect exists, but both search arms are predicted to MISS it. No amount of reweighting can introduce characters absent from the grammar.

## Matched search and checks

Reuse the existing Choices implementation unchanged: ordinary seeded category draws off, centered small logistic-map weight perturbations on, amplitude0.15. Each target is tested independently. Both arms use identical grammars, strict first-witness retention, budgets and seeds. New frozen seeds211/307/419/503/607; 1,000 calls to each of22 fixtures per seed per arm:110,000 calls per arm,220,000 search calls total. Workflow lengths3–12; approval sequences4–12. Known controls are never inserted into the search corpus. No tuning after results.

Independent output-property oracles each have manually labeled violating and legitimate observations. Direct controls additionally require the vulnerable target to exhibit its known defect, its clean counterpart to refuse that defect, and both to retain the legitimate behavior:66 checks. Abort search if controls fail. Retain exact first-hit requests and output witnesses, first-hit indices, unique-input counts, accepted outputs, failing-call counts and unexpected exceptions. Expected malformed SQL/packet inputs can be rejected normally; unexpected exceptions fail the gate.

Gates: all controls; at least9/10 grammar-reachable flaws found by each arm; zero alarms on clean fixtures; zero unexpected exceptions; exact matched budgets; every witness replays with identical outputs on unchanged targets without chaos. Report detection for ALL11 known flaws, including the missing Unicode probe: the all11 completeness gate is predicted FAILED. Report the finite race enumeration separately; do not call the rest exhaustive.

Chaos benefit: more known flaws found, or if tied a lower sum of first-hit calls across55 vulnerable fixture/seed pairs, using1,001 for misses; no per-family seed detection loss and no clean alarm allowed. A tie or regression fails. Report per-seed gains and losses; no universal superiority claim.

This benchmark uses authored grammars and security properties. It tests discovery within those representations. Actual SQLite/zlib/parser boundaries strengthen the fixtures but do not turn them into a production application audit. The race target is an explicit state machine, not an OS thread race.

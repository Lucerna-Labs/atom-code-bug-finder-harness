# Security discovery simulation — frozen protocol

This is a synthetic demonstration of Jesse's edge-of-chaos method, not a scan of a real project.

## Target and property

- One unchanged target function accepts a relative path under a temporary `allowed/` root. Its deliberately flawed guard rejects paths beginning with `..` and absolute paths, then normalizes and returns the joined path.
- Security property: every accepted path must resolve inside `allowed/`.
- An independent oracle uses `os.path.realpath` plus `os.path.commonpath` to check containment. Before the experiment, it must classify all five fixed controls correctly: ordinary nested path safe; one internal parent segment safe; two internal parent segments unsafe; leading parent path unsafe; absolute path unsafe.
- The target returns paths only. It reads no real files, and all paths remain under a newly created temporary directory.

## Arms and search

- Seeds: `17, 29, 43`. Each arm has three calls per seed, nine calls total.
- Off: run the plain `docs/guide.txt` request three times per seed.
- On: run the same plain request, then two variants. Each variant starts from the same path grammar and inserts zero to two `..` segments after `docs/`. Two logistic-map steps at `r=4`, initialized from the seed and variant index, choose whether to insert each segment. The map varies the request, never the target or the oracle.
- The selector keeps a variant only if the independent oracle verifies a new violation. Plain wins ties. Keep the exact input and seed as a reproducer; do not promote a vulnerable program state.

## Frozen predictions and gates

1. The independent oracle passes 5/5 fixed controls.
2. Off finds zero accepted paths outside `allowed/`.
3. On finds at least one accepted outside path in all three seeds. The fixed logistic values were checked in a separate numerical scratch run before this document.
4. Every reported finding reproduces by calling the unchanged target directly with chaos disabled.
5. Any failing gate remains recorded as failed. Do not change seeds, thresholds, target, oracle, or outcome criteria after seeing results.

## Limits

This evaluates a known synthetic path-boundary flaw. It tests whether a reproducible chaos-driven request search can expose it under these controls. It does not establish vulnerability coverage or inspect any of Jesse's project code.

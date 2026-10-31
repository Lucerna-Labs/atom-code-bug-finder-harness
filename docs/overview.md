# Developer overview

## What this project is

Atom Code Bug Finder Harness is a local experiment runner by Lucerna Labs, a division of Lucerna Media. It sends generated JSON requests to a chosen program, sends that program's result to an independent checker, and compares two matched input-selection arms: ordinary seeded selection and the same selection with a small deterministic chaos-map perturbation. A checker-reported property violation becomes a saved witness only after the runner repeats it through fresh processes.

The same runner is available through a browser GUI, a command-line entry point, and seven stdio MCP tools for AI agents. The GUI can import an app ZIP into a managed project snapshot so runs use the copied files. Export carries those imported files and associated configurations to another installation of this benchmark.

## Why it exists

A fluent or surprising test result is weak evidence by itself. The project keeps the plain arm as a measured bar, requires labeled controls before a run, preserves first-hit inputs, and checks that source, configuration and harness files did not change during the test. The checker defines the property under test; the generator supplies candidate inputs. That separation makes failures easier to reproduce and makes a missing checker or missing input class visible.

## What it currently proves

The process adapter was exercised on an ordinary Python function through a separate target and checker process, including a copy outside this repository. The GUI and MCP tools were tested at their live boundaries. The ZIP workflow was tested by importing a temporary project, deleting its source folder, running the copy, exporting it, reimporting the bundle and running again. Earlier synthetic security fixtures found known planted defects and recorded both passing and failed chaos-benefit gates.

Those results establish operational behavior for the tested examples. They do not establish automatic source-code auditing, universal flaw coverage or a general advantage for chaos. A target wrapper and a trustworthy checker are required for each new behavior being tested. Crashes and protocol failures currently stop the run instead of being classified as findings.

## Read next

- Name and attribution: the official product identity and internal path decision.
- Architecture: ownership of each source file and the complete run path.
- Development guide: run, test and extend the project.
- Experiment method: arms, controls, gates and receipts.
- Portable projects: ZIP import, export and dependency limits.
- Interfaces: browser API, MCP tools and local access boundary.
- Evidence and limits: measured results and known gaps.

# Limits and next proof boundaries

## Current limits

- The runner cannot infer a correct property from arbitrary source code. A developer supplies an independent checker and labeled controls.
- The input grammar is bounded and authored. Missing values, states or operation dependencies remain invisible, regardless of call count or chaos setting.
- A target crash, timeout or malformed reply stops the run. This version does not turn crashes into saved findings.
- A source-hash gate covers declared `source_paths` only. Transitive packages, environment variables, network services and undeclared files can change outside that list.
- Target and checker commands run with the user's permissions. The local server and ZIP path checks do not make those commands an OS sandbox.
- Uploaded bundles include files and configs, while external runtimes, dependencies and previous receipts remain on their respective machines.
- The original synthetic suites and the ordinary-code example use planted defects. No unknown vulnerability in a user project has been proven by this repository.
- The separate cross-component lab is not connected to the GUI. Its held-out test found the same planted classes but failed the chaos-benefit gate.

## What a stronger result would require

For a real project, choose a function or workflow, preserve a known source revision, build a wrapper for the actual execution boundary, and validate the independent checker against known positive and negative controls. Then compare matched off/on runs, replay every witness on unchanged code, and state both classes reached and classes excluded by the grammar. For a multi-component workflow, define the producer/consumer state and an end-to-end property; unit tests alone do not establish the composed property.

A low first-hit score is useful only within the same target, grammar, seed list and call budget. More calls against one tiny synthetic fixture mostly repeat inputs. A successful job means the experiment completed and wrote a receipt; the benefit gate can fail. Preserve negative results and introduce a new frozen protocol when the question, grammar or metric changes.

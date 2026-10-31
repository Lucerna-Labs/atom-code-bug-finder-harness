# Run the benchmark on ordinary code

The `run_external.py` runner accepts a chosen local program in any language that can read and write newline-delimited JSON. You provide two small commands: one calls the function under test; the other checks the result against its contract. The runner starts both as separate processes and calls them through a JSON protocol. It changes input-selection weights in the chaos arm; it does not rewrite your program.

The process adapter is for Linux and other Unix systems: it uses `select` on pipes and POSIX process groups for timeout cleanup. It has been tested on this Linux machine.

The included [ordinary-code example](examples/ordinary_code/program.py) computes a sum of distinct numbers incorrectly. Its target wrapper calls that ordinary function; its checker independently calculates the expected sum with a set. [The config](examples/ordinary_code/config.json) defines the bounded input grammar and labeled controls.

```sh
cd /home/jesse/Desktop/Projects/chaos-security-benchmark
python3 run_external.py --config examples/ordinary_code/config.json --output ordinary-code-results.json
```

You can place your config and wrappers in another repository and give `--config` its absolute path. `cwd` and `source_paths` in the config resolve relative to the config file; commands run with `cwd` as their working directory. `--output` is the JSON receipt path. Use an isolated checkout for a target with side effects; this runner executes the configured commands with your user permissions. It does not provide an OS sandbox. The target should treat each input line as an independent case; put a complete stateful sequence in one request if necessary.

The target reads `{"request": ...}` and writes one line `{"result": ...}`. The checker reads `{"request": ..., "result": ...}` and writes one line `{"violation": true|false, "reason": "short explanation"}`. Each process must flush stdout after every response. The runner uses argument arrays without a shell, enforces per-call timeouts and response-size limits, and stops on malformed replies or exits.

The config has these fields:

| Field | Meaning |
| --- | --- |
| `name` | Stable name used to seed the generator |
| `cwd` | Working directory for both commands |
| `target_command`, `checker_command` | Executable and arguments as JSON arrays |
| `source_paths` | Source files to hash before and after |
| `seeds` | Distinct integer seeds, up to 20 |
| `calls_per_seed` | Calls per arm and seed, 1–100,000 |
| `timeout_seconds` | Per target/checker reply, at most 30 seconds |
| `controls` | Requests with expected `violation` booleans; all must pass first |
| `grammar` | Bounded JSON input shape |

Grammar nodes can be `{"type":"enum","values":[...]}`, `{"type":"int","min":0,"max":5}`, `{"type":"object","fields":{"key":<node>}}`, or `{"type":"array","min_length":0,"max_length":8,"items":<node>}`. Fields are generated in their config order. The runner makes the same number of inputs for the off and on arms. The on arm uses the existing centered logistic-map perturbation for each categorical choice. It retains the first checker-verified finding per seed and replays it through fresh processes with no chaos source.

Receipts include exact witness requests, checker reasons and hashes of target outputs. They do not store raw target outputs. Avoid putting real credentials in the grammar, controls or checker reason; witness requests and reasons are saved. A failure means the declared checker found a property violation. It does not mean that arbitrary code was scanned or that every possible bug is discoverable. Crashes and protocol errors abort this version of the run rather than being classified as findings. The source hash list covers only files you declare.

Target and checker stderr are discarded by the runner, so invoke either configured command directly while debugging a protocol failure. The runner uses a fresh process pair for each seed and arm; the checker is separate from the code under test. [Python's subprocess documentation](https://docs.python.org/3/library/subprocess.html) describes the process boundary used here.

The process protocol and timeout were exercised against a copied ordinary project outside this repository with `python3 tests/external_boundary.py`. For the earlier synthetic suites and their fixed results, see [BROAD-REPORT.md](BROAD-REPORT.md).

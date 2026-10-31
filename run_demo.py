#!/usr/bin/env python3
"""Reproducible, synthetic security discovery with a two-arm chaos comparison."""

import json
import os
import tempfile
from pathlib import Path


SEEDS = (17, 29, 43)
PLAIN = "docs/guide.txt"


def vulnerable_resolve(root: Path, request: str) -> Path | None:
    """Deliberately flawed application function, unchanged across both arms."""
    if request.startswith("..") or Path(request).is_absolute():
        return None
    return (root / request).resolve()


def independent_containment(root: Path, request: str) -> bool:
    """Separate property oracle, independent of the target's pathlib resolution."""
    canonical_root = os.path.realpath(root)
    canonical_request = os.path.realpath(os.path.join(root, request))
    return os.path.commonpath((canonical_root, canonical_request)) == canonical_root


def verify_oracle(root: Path) -> dict:
    controls = (
        ("docs/guide.txt", True),
        ("docs/../guide.txt", True),
        ("docs/../../guide.txt", False),
        ("../guide.txt", False),
        (str(root.parent / "guide.txt"), False),
    )
    observed = [independent_containment(root, path) == expected for path, expected in controls]
    return {"passed": sum(observed), "total": len(controls), "all_passed": all(observed)}


def chaos_variant(seed: int, variant: int) -> tuple[str, list[float]]:
    """Two indexed logistic steps perturb one path request's segment sequence."""
    state = (seed * 0.61803398875 + variant * 0.113) % 1.0
    samples = []
    segments = ["docs"]
    for _ in range(2):
        state = 4.0 * state * (1.0 - state)
        samples.append(state)
        if state > 0.5:
            segments.append("..")
    segments.append("guide.txt")
    return "/".join(segments), samples


def run_arm(root: Path, chaos_on: bool) -> dict:
    rows = []
    selected = {}
    for seed in SEEDS:
        variants = [chaos_variant(seed, variant) for variant in (1, 2)] if chaos_on else []
        requests = [(PLAIN, [])] + (variants if chaos_on else [(PLAIN, []), (PLAIN, [])])
        chosen = PLAIN
        for request, samples in requests:
            result = vulnerable_resolve(root, request)
            outside = result is not None and not independent_containment(root, request)
            if outside and chosen == PLAIN:
                chosen = request
            rows.append({
                "seed": seed,
                "request": request,
                "chaos_samples": [round(value, 9) for value in samples],
                "accepted": result is not None,
                "outside_root": outside,
            })
        selected[str(seed)] = chosen
    return {
        "calls": len(rows),
        "violations": sum(row["outside_root"] for row in rows),
        "seeds_with_finding": sum(request != PLAIN for request in selected.values()),
        "selected_requests": selected,
        "rows": rows,
    }


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="chaos-security-demo-") as temporary:
        root = Path(temporary) / "allowed"
        root.mkdir()
        controls = verify_oracle(root)
        if not controls["all_passed"]:
            raise RuntimeError("Independent oracle did not pass its fixed controls")
        off = run_arm(root, False)
        on = run_arm(root, True)
        reproductions = {}
        for seed, request in on["selected_requests"].items():
            if request == PLAIN:
                reproductions[seed] = False
                continue
            result = vulnerable_resolve(root, request)
            reproductions[seed] = result is not None and not independent_containment(root, request)
        gates = {
            "oracle_5_of_5": controls["passed"] == 5,
            "off_zero_findings": off["violations"] == 0,
            "on_all_three_seeds": on["seeds_with_finding"] == 3,
            "reproduces_without_chaos": all(reproductions.values()),
            "matched_call_budget": off["calls"] == on["calls"] == 9,
        }
        report = {
            "kind": "synthetic_simulation",
            "target": "deliberately vulnerable path resolver",
            "oracle_controls": controls,
            "off": off,
            "on": on,
            "reproductions": reproductions,
            "gates": gates,
        }
    destination = Path(__file__).with_name("results.json")
    destination.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({
        "off_calls": off["calls"],
        "off_violations": off["violations"],
        "on_calls": on["calls"],
        "on_violations": on["violations"],
        "on_seeds_with_finding": on["seeds_with_finding"],
        "reproductions": reproductions,
        "gates": gates,
    }, indent=2))


if __name__ == "__main__":
    main()

"""Run from any directory with Python 3.10+, Node 24+ and the pinned Lean toolchain."""
import itertools
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "examples" / "reservation"
sys.path.insert(0, str(CASE))
from reserve import reserve

CLAIMS = ("accept_if_fits", "reject_if_exceeds", "accepted_within_capacity")
ALLOWED_AXIOMS = {"propext", "Classical.choice", "Quot.sound"}


def command(args, stdin=None):
    result = subprocess.run(
        args, cwd=ROOT, input=stdin, capture_output=True, text=True, timeout=180
    )
    if result.returncode:
        raise RuntimeError(f"{args[0]} exited {result.returncode}:\n{result.stderr}\n{result.stdout}")
    return result.stdout.strip()


def audit():
    output = command(["lake", "env", "lean", "-DwarningAsError=true", "Audit.lean"])
    dependencies = {}
    for claim in CLAIMS:
        prefix = rf"'Reservation\.{claim}' "
        match = re.search(prefix + r"(?:does not depend on any axioms|depends on axioms: \[([^\]]*)\])", output)
        if not match:
            raise ValueError(f"unknown axiom report for {claim}: {output}")
        axioms = [name.strip() for name in (match[1] or "").split(",") if name.strip()]
        if set(axioms) - ALLOWED_AXIOMS:
            raise ValueError(f"{claim} uses unapproved axioms: {axioms}")
        dependencies[claim] = axioms
    return dependencies


def encode(value):
    return "reject" if value is None else str(value)


def compare(label, cases, expected, actual):
    if len(expected) != len(cases) or len(actual) != len(cases):
        raise ValueError(f"{label}: expected {len(cases)} rows, got {len(expected)} and {len(actual)}")
    for case, want, got in zip(cases, expected, actual):
        if want != got:
            raise ValueError(f"{label}: {case} oracle={want}, implementation={got}")


def main():
    command(["lake", "build"])
    dependencies = audit()
    cases = list(itertools.product(range(8), repeat=3))
    for limit in (2**53 + 1, 2**64):
        cases.extend([(limit, limit - 1, 1), (limit, limit, 1), (limit, 0, limit)])
    wire = "".join(f"{c} {u} {r}\n" for c, u, r in cases)
    binary = ROOT / ".lake" / "build" / "bin" / ("oracle.exe" if os.name == "nt" else "oracle")
    expected = command([str(binary)], wire).splitlines()
    compare("python", cases, expected, [encode(reserve(*case)) for case in cases])
    actual_ts = command(["node", str(CASE / "reserve.ts")], wire).splitlines()
    compare("typescript", cases, expected, actual_ts)

    # Sensitivity control: the strict inequality wrongly rejects exact-capacity requests.
    mutant = [encode(u + r if u + r < c else None) for c, u, r in cases]
    differences = [i for i, (want, got) in enumerate(zip(expected, mutant)) if want != got]
    if not differences:
        raise ValueError("negative control survived")
    i = differences[0]
    print(json.dumps({
        "case": "capacity-reservation-v1",
        "commit": command(["git", "rev-parse", "HEAD"]),
        "tracked_changes": bool(command(["git", "status", "--porcelain", "--untracked-files=no"])),
        "lean": command(["lake", "env", "lean", "--version"]),
        "python": platform.python_version(), "node": command(["node", "--version"]),
        "model_claim_axioms": dependencies,
        "matching_rows": {"python": len(cases), "typescript": len(cases)},
        "negative_control": {"differences": len(differences), "first_input": cases[i],
                             "oracle": expected[i], "mutant": mutant[i]},
    }, indent=2))


if __name__ == "__main__":
    main()

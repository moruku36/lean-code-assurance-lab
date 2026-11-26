"""Bounded synthetic handoff replay; does not change either actual CLI."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

from check_checkpoint_page import AXIOMS, EXAMPLE, ROOT, blob, json_line, replace, run

BASE = "85f0b52d8c3f75d825140f0eb82d17800f7fe606"
KEYS = [
    0, 1, 9, 10, 2**53 - 1, 2**53, 2**53 + 1,
    2**64 - 1, 2**64, 2**64 + 1,
    10**127 - 1, 10**127, 10**127 + 1, 10**128 - 1,
]
ROWS = [[str(k), str(KEYS[-1-i]), "D" if i%3 == 0 else "U"] for i, k in enumerate(KEYS)]
PIVOTS = [3, 4, 6, 7, 8, 9, 10, 11, 12, 13]
CLAIMS = {"exact_handoff_joins_prefix", "earlier_adjacent_boundary_replays"}


def fingerprint(data):
    return hashlib.sha256(data).hexdigest()


def wanted_pages(rows, start, count):
    return [[rows[i:i+count], rows[i+count-1][0] if i+count < len(rows) else None]
            for i in range(start, len(rows), count)] or [[[], None]]


def check_lean(lean, tmp, expected):
    assert "version 4.19.0" in run([lean, "--version"])
    env = {**os.environ, "LEAN_PATH": str(tmp)}

    def compile_lean(args, body=None):
        p = subprocess.run([lean, "-DwarningAsError=true", *args], cwd=tmp,
                           env=env, input=body, capture_output=True, text=True, timeout=20)
        assert p.returncode == 0 and not p.stderr, p
        return p.stdout

    for mod in ("CheckpointPage", "CheckpointWalk", "CheckpointHandoff"):
        (tmp / (mod + ".lean")).write_bytes((ROOT / (mod + ".lean")).read_bytes())
        assert not compile_lean(["-o", mod + ".olean", mod + ".lean"])
    body = "import CheckpointHandoff\n"
    body += "".join("#print axioms CheckpointHandoff." + t + "\n" for t in sorted(CLAIMS))
    term = "[" + ",".join(f"⟨{k},{r},{str(op == 'D').lower()}⟩" for k,r,op in ROWS) + "]"
    args = "[" + ",".join(f"(some {ROWS[n-1][0]}, {l})" for n,l in expected) + "]"
    body += f"#eval CheckpointWalk.emit {term} {args}\n"
    audited, observed = {}, []
    for line in compile_lean(["--stdin"], body).splitlines():
        if line.startswith("walk|"):
            observed.append([[r.split(":") for r in part.split(",")] if part else []
                             for part in line.removeprefix("walk|").split(";")])
            continue
        m = re.fullmatch(r"'CheckpointHandoff\.(\w+)' (?:depends on axioms: \[([^\]]+)\]|does not depend on any axioms)", line)
        assert m and m[1] not in audited, line
        audited[m[1]] = [] if m[2] is None else m[2].split(", ")
        assert set(audited[m[1]]) <= AXIOMS, line
    assert set(audited) == CLAIMS and len(observed) == len(expected)
    assert observed == list(expected.values())
    return {"cases": len(observed), "axioms": audited, "toolchain": run([lean, "--version"])}


def main():
    if not __debug__:
        raise SystemExit("run without Python optimization to enable assertions")
    py, node = os.environ.get("PYTHON", "python3"), os.environ.get("NODE", "node")
    lean = os.environ.get("LEAN", "lean")
    clients = [[py,"-B",str(EXAMPLE / "page.py")], [node,str(EXAMPLE / "page.ts")]]
    clean = blob(ROWS)
    clean_id = fingerprint(clean)
    names_and_modes = set()
    lean_expected = {}
    with tempfile.TemporaryDirectory(prefix="handoff-replay-") as name:
        tmp = Path(name)
        checkpoint = tmp / "checkpoint.jsonl"

        def call(i, request, walk):
            return json.loads(run([*clients[i], str(checkpoint), *(["--walk"] if walk else [])],
                                  json_line(request)))

        replace(checkpoint, clean)
        for direction in (0, 1):
            dest = 1 - direction
            for pivot in PIVOTS:
                resumed_limit = 2 + pivot%4
                want = wanted_pages(ROWS, pivot, resumed_limit)
                lean_expected[pivot, resumed_limit] = [page for page, _ in want]
                status, version, prefix, cursor = call(direction, [None,str(pivot)], False)
                assert [status, version, prefix, cursor] == [
                    "ok", clean_id, ROWS[:pivot], [clean_id, ROWS[pivot-1][0]]
                ]
                got = call(dest, [cursor,str(resumed_limit)], True)
                assert got == ["ok",clean_id,want]
                assert prefix + [r for page, _ in got[2] for r in page] == ROWS
                names_and_modes.add((direction,pivot,"page_to_walk"))

                # Emulate a receiver retaining only the first delivered page.
                status, version, parts = call(direction, [None,str(pivot)], True)
                assert [status,version,parts] == ["ok",clean_id,wanted_pages(ROWS,0,pivot)]
                taken, key = parts[0]
                assert key is not None and taken == ROWS[:pivot]
                cursor = json.loads(json_line([version,key]))
                visited = []
                for expect, next_key in want:
                    status, version, got, cursor = call(dest, [cursor,str(resumed_limit)], False)
                    assert [status,version,got,cursor] == [
                        "ok",clean_id, expect, None if next_key is None else [clean_id,next_key]
                    ]
                    visited.extend(got)
                assert cursor is None and taken + visited == ROWS
                names_and_modes.add((direction,pivot,"walk_to_page"))

        boundary = str(2**53 + 1)
        rounded = run([node, "-p", "String(Number(process.argv[1]))", boundary])
        assert rounded == str(2**53)
        start = KEYS.index(int(boundary)) + 1
        floating_decimal = run([node, "-p", "String(Number(process.argv[1]))", str(10**127 + 1)])
        assert "e+" in floating_decimal
        long_boundary = "1" + "0" * 128
        for i in (0, 1):
            good = call(i, [[clean_id,boundary],"1"], False)
            bad = call(i, [[clean_id,rounded],"1"], False)
            assert good[2] == [ROWS[start]] and bad[2] == [ROWS[start-1]]
            assert bad[:2] == ["ok",clean_id]
            good_walk = call(i, [[clean_id,boundary],"1"], True)
            bad_walk = call(i, [[clean_id,rounded],"1"], True)
            assert good_walk == ["ok",clean_id,wanted_pages(ROWS,start,1)]
            assert bad_walk == ["ok",clean_id,wanted_pages(ROWS,start-1,1)]
            for entry in (False, True):
                assert call(i, [[clean_id,long_boundary],"2"], entry) == ["err","bad-cursor"]
                assert call(i, [[clean_id,floating_decimal],"2"], entry) == ["err","bad-cursor"]

        # Begin with the real walk cursor; replay on the same bytes, then replace
        # one row atomically between calls. Both kinds of reader then fail closed.
        initial = call(0, [None,"7"], True)
        old_token = [initial[1], initial[2][0][1]]
        replace(checkpoint, clean)
        assert call(1, [old_token,"3"], True) == ["ok",clean_id,wanted_pages(ROWS,7,3)]
        updated = [row[:] for row in ROWS]
        updated[-1][1] = "42"
        updated_bytes = blob(updated)
        assert fingerprint(updated_bytes) != clean_id
        replace(checkpoint, updated_bytes)
        for i in (0,1):
            for entry in (False,True):
                assert call(i, [old_token,"3"], entry) == ["err","checkpoint-changed"]
        assert call(1, [None,"100"], True) == ["ok",fingerprint(updated_bytes),[[updated,None]]]
        report = {
            "baseline_unchanged": BASE,
            "clients": {"python":run([py,"--version"]),"node":run([node,"--version"])},
            "cross_language_handoffs": len(names_and_modes),
            "fixtures": {"rows":len(ROWS),"pivots": PIVOTS,"snapshot_sha256":clean_id},
            "duplicate_on_lossy_client_boundary": {"client_intended":boundary,
                                                   "client_sent":rounded,
                                                   "replayed_key":boundary,
                                                   "accepted_paths":4},
            "exponential_boundary":floating_decimal,
            "nondigit_or_129_digit_rejections":8,
            "stale_start_rejections":4,
            "byte_identical_replacement_resumed":True,
            "lean":check_lean(lean, tmp, lean_expected),
        }
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

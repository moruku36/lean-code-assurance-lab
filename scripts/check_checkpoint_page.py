"""A finite cross-runtime comparison for the checkpoint page case."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "checkpoint_page"
AXIOMS = {"propext", "Quot.sound", "Classical.choice"}
CLAIMS = {
    "resume_rejects_changed", "resume_accepts_exact", "before_boundary_filtered",
    "after_boundary_preserved", "exact_remaining", "stable_next_page", "sorted_boundary_page",
}
ROWS = [
    ("0", "0", "U"), ("2", "7", "D"), ("10", "3", "U"),
    ("9007199254740991", "9007199254740992", "D"),
    ("9007199254740992", "9007199254740993", "U"),
    ("9007199254740993", "18446744073709551616", "D"),
    ("18446744073709551616", "9" * 128, "U"), ("9" * 128, "8", "D"),
]
ROWS = [list(r) for r in ROWS]
LIMITS = (1, 2, 3, 5, 8, 100)


def run(args, data=None):
    p = subprocess.run(args, input=data, text=True, capture_output=True, timeout=20)
    if p.returncode or p.stderr:
        raise RuntimeError((args[0], p.returncode, p.stderr, p.stdout))
    return p.stdout.strip()


def json_line(value):
    return json.dumps(value, separators=(",", ":"))


def blob(rows):
    return b"".join(json_line(r).encode("ascii") + b"\n" for r in rows)


def replace(path, data):
    # Same-directory staged file, then one atomic replacement. This writer is
    # a synthetic fixture; it does not implement a distributed checkpoint.
    stage = path.with_name("staged")
    stage.write_bytes(data)
    os.replace(stage, path)


def expected(rows, case, digest):
    after, limit = case
    # Independent of filtering: the exact boundary is a row index.
    start = 0 if after is None else [r[0] for r in rows].index(after) + 1
    end = min(len(rows), start + limit)
    return ["ok", digest, rows[start:end], [digest, rows[end-1][0]] if end < len(rows) else None]


def lean_check(lean, rows, cases):
    import re
    program = (ROOT / "CheckpointPage.lean").read_text()
    program += "\n".join("#print axioms CheckpointPage." + c for c in sorted(CLAIMS)) + "\n"
    term = "[" + ",".join(f"⟨{k},{r},{str(op == 'D').lower()}⟩" for k, r, op in rows) + "]"
    arguments = "[" + ",".join(f"({'none' if k is None else 'some ' + k}, {l})" for k, l in cases) + "]"
    program += f"#eval CheckpointPage.emit {term} {arguments}\n"
    output = run([lean, "-DwarningAsError=true", "--stdin"], program).splitlines()
    audit = {}
    actual = []
    for line in output:
        if line.startswith("page|"):
            payload = line.removeprefix("page|")
            actual.append([r.split(":") for r in payload.split(",")] if payload else [])
            continue
        match = re.fullmatch(r"'CheckpointPage\.(\w+)' (?:depends on axioms: \[([^\]]+)\]|does not depend on any axioms)", line)
        assert match and match[1] not in audit, line
        audit[match[1]] = [] if match[2] is None else match[2].split(", ")
        assert set(audit[match[1]]) <= AXIOMS, line
    assert set(audit) == CLAIMS
    assert len(actual) == len(cases)
    return {"checked_pages": len(actual), "theorems": audit}, actual


def main():
    if not __debug__:
        raise SystemExit("run without Python optimization to enable the assertions")
    parser = argparse.ArgumentParser()
    parser.add_argument("--without-lean", action="store_true")
    opts = parser.parse_args()
    lean = os.environ.get("LEAN", "lean")
    py = os.environ.get("PYTHON", "python3")
    node = os.environ.get("NODE", "node")
    clients = {"python": [py, "-B", str(EXAMPLE / "page.py")],
               "typescript": [node, str(EXAMPLE / "page.ts")]}
    caps = {"python": run([py, "--version"]), "node": run([node, "--version"])}
    cases = [(k, limit) for k in [None, *(r[0] for r in ROWS)] for limit in LIMITS]
    clean_blob = blob(ROWS)
    clean_id = hashlib.sha256(clean_blob).hexdigest()
    wants = [expected(ROWS, case, clean_id) for case in cases]
    results = {}
    with tempfile.TemporaryDirectory(prefix="checkpoint-page-") as tmp:
        base = Path(tmp)
        checkpoint = base / "checkpoint.jsonl"

        def call(client, request):
            return json.loads(run([*client, str(checkpoint)], json_line(request)))

        replace(checkpoint, clean_blob)
        numeric, no_pin = base / "number.ts", base / "unbound.ts"
        source = (EXAMPLE / "page.ts").read_text()
        numeric_clause = "rows.filter(row => key(row[0]) > cut)"
        pin_clause = 'if (typed !== null && typed[0] !== id)'
        assert source.count(numeric_clause) == source.count(pin_clause) == 1
        numeric.write_text(source.replace(numeric_clause, "rows.filter(row => Number(row[0]) > Number(cut))"))
        no_pin.write_text(source.replace(pin_clause, "if (false)"))
        negative = []
        for (k, limit), want in zip(cases, wants, strict=True):
            req = [None if k is None else [clean_id, k], str(limit)]
            for name, client in clients.items():
                assert call(client, req) == want, (name, req)
            if call([node, str(numeric)], req) != want:
                negative.append([k, limit])

        forged = [
            ([None, 1], "bad-request"), ([None, "01"], "bad-request"),
            ([None, "101"], "bad-request"), ([None, "2\n"], "bad-request"),
            ([[clean_id, 0], "1"], "bad-cursor"), ([[clean_id, "00"], "1"], "bad-cursor"),
            ([[clean_id, "0\n"], "1"], "bad-cursor"), ([[clean_id + "\n", "0"], "1"], "bad-cursor"),
            ([[clean_id, "9" * 129], "1"], "bad-cursor"),
            ([[clean_id, "1"], "1"], "unknown-boundary"),
        ]
        for client in clients.values():
            for req, code in forged:
                assert call(client, req) == ["err", code], req
            assert call(client, [None, "1"])[0] == "ok"
        bad_snapshots = [
            clean_blob[:-1], clean_blob + b"\n", clean_blob.replace(b"\n", b"\r\n", 1),
            b"\xef\xbb\xbf" + clean_blob, b"\xff\n", b"x" * (256 * 1024 + 1),
            blob([ROWS[0], ROWS[0]]), blob(ROWS[::-1]), b'[0,"0","U"]\n',
            b'["0","000","U"]\n', b'["0", "0","U"]\n', b'["0","0","X"]\n',
            b'["0","0","U",null]\n', blob([["9" * 129, "0", "U"]]),
        ]
        for malformed in bad_snapshots:
            replace(checkpoint, malformed)
            for client in clients.values():
                assert call(client, [None, "1"]) == ["err", "bad-checkpoint"]
        replace(checkpoint, b"")
        for client in clients.values():
            assert call(client, [None, "1"]) == expected([], (None, 1), hashlib.sha256(b"").hexdigest())
        checkpoint.unlink()
        for client in clients.values():
            assert call(client, [None, "1"]) == ["err", "bad-checkpoint"]
        replace(checkpoint, clean_blob)
        alternating_walks = 0
        for first_client in clients:
            # Simulate the boundary cursor being passed between independently
            # running Python and TypeScript processes, not a shared function.
            other = next(name for name in clients if name != first_client)
            for limit in LIMITS:
                owner, token, collected = first_client, None, []
                for _ in range(len(ROWS) + 1):
                    status, rev, part, token = call(clients[owner], [token, str(limit)])
                    assert status == "ok" and rev == clean_id
                    collected += part
                    if token is None:
                        break
                    owner = other if owner == first_client else first_client
                assert token is None and collected == ROWS
                alternating_walks += 1

        first = call(clients["python"], [None, "5"])
        stale = [first[3], "5"]
        witness = call([node, str(numeric)], stale)
        assert first[3][1] == "9007199254740992"
        assert witness[2] == ROWS[6:] and call(clients["typescript"], stale)[2] == ROWS[5:]
        assert negative and all(k == first[3][1] for k, _ in negative), negative

        # Replace with the very same bytes. A new inode is not a content change.
        replace(checkpoint, clean_blob)
        for client in clients.values():
            assert call(client, stale) == expected(ROWS, (first[3][1], 5), clean_id)

        # Same sorted keys, but a different revision and deletion indicator.
        changed = [row[:] for row in ROWS]
        changed[5][1:] = ["18446744073709551617", "U"]
        change_blob = blob(changed)
        replace(checkpoint, change_blob)
        for client in clients.values():
            assert call(client, stale) == ["err", "checkpoint-changed"]
            assert call(client, [None, "100"])[2] == changed
        unbound = call([node, str(no_pin)], stale)
        assert unbound[0] == "ok" and unbound[2][0] == changed[5]
        assert first[1] != unbound[1] and first[2] + unbound[2] != ROWS

        # A late key below the cursor would be omitted by the unbound traversal.
        changed[1:1] = [["1", "1", "U"]]
        replace(checkpoint, blob(changed))
        for client in clients.values():
            assert call(client, stale) == ["err", "checkpoint-changed"]
        unbound_insert = call([node, str(no_pin)], stale)
        assert unbound_insert[0] == "ok" and ["1", "1", "U"] not in first[2] + unbound_insert[2]

        results.update({
            "expected_pages_per_runtime": len(cases),
            "invalid_requests_per_runtime": len(forged),
            "invalid_snapshot_forms_per_runtime": len(bad_snapshots) + 1,
            "empty_snapshot_per_runtime": 1,
            "alternating_cross_process_walks": alternating_walks,
            "same_byte_replacement_per_runtime": "resumed",
            "same_key_new_revision_per_runtime": "rejected_then_restart_observed_new_snapshot",
            "insert_below_cursor_per_runtime": "rejected",
            "number_negative_control_mismatches": len(negative),
            "number_negative_witness_skipped": ROWS[5][0],
            "unbound_negative_controls": ["mixed_checkpoint_ids", "omitted_inserted_key_1"],
            "baseline_snapshot_sha256": clean_id,
        })
    if not opts.without_lean:
        caps["lean"] = run([lean, "--version"])
        assert "version 4.19.0" in caps["lean"], caps["lean"]
        results["lean"], observed = lean_check(lean, ROWS, cases)
        assert observed == [row[2] for row in wants]
    print(json.dumps({"runtimes": caps, "results": results}, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

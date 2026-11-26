"""Replay pinned local traversal against an independent ordinal oracle."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

from check_checkpoint_page import AXIOMS, ROWS, LIMITS, ROOT, blob, json_line, replace, run

BASE = "9ba3ede95ff23dd15bf9b406b42eeb8a28883dd7"
EXAMPLE = ROOT / "examples" / "checkpoint_page"
CLAIMS = {
    "chunks_cover", "walk_covers_exact_suffix",
    "resume_walk_rejects_changed", "resume_walk_covers_unchanged",
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def oracle(rows, start, limit, snapshot_id):
    pages = []
    while start < len(rows):
        stop = min(start + limit, len(rows))
        page = [rows[i] for i in range(start, stop)]
        pages.append([page, page[-1][0] if stop < len(rows) else None])
        start = stop
    return ["ok", snapshot_id, pages or [[[], None]]]


def checked_lean(lean, base, rows, starts_and_limits):
    assert "version 4.19.0" in run([lean, "--version"])
    for src in ("CheckpointPage.lean", "CheckpointWalk.lean"):
        (base / src).write_bytes((ROOT / src).read_bytes())
    env = {**os.environ, "LEAN_PATH": str(base)}
    for name in ("CheckpointPage", "CheckpointWalk"):
        p = subprocess.run(
            [lean, "-DwarningAsError=true", "-o", f"{name}.olean", f"{name}.lean"],
            cwd=base, env=env, text=True, capture_output=True, timeout=20,
        )
        assert (p.returncode, p.stdout, p.stderr) == (0, "", ""), p
    body = "import CheckpointWalk\n"
    body += "\n".join("#print axioms CheckpointWalk." + c for c in sorted(CLAIMS)) + "\n"
    term = "[" + ",".join(f"⟨{k},{rev},{str(op == 'D').lower()}⟩" for k, rev, op in rows) + "]"
    args = "[" + ",".join(
        f"({'none' if start == 0 else 'some ' + rows[start-1][0]}, {limit})"
        for start, limit in starts_and_limits
    ) + "]"
    body += f"#eval CheckpointWalk.emit {term} {args}\n"
    p = subprocess.run(
        [lean, "-DwarningAsError=true", "--stdin"], input=body, env=env,
        cwd=base, text=True, capture_output=True, timeout=20,
    )
    assert p.returncode == 0 and not p.stderr, p
    audit, observed = {}, []
    for line in p.stdout.splitlines():
        if line.startswith("walk|"):
            parts = line.removeprefix("walk|").split(";")
            observed.append([[cell.split(":") for cell in part.split(",")] if part else [] for part in parts])
        else:
            match = re.fullmatch(r"'CheckpointWalk\.(\w+)' (?:depends on axioms: \[([^\]]+)\]|does not depend on any axioms)", line)
            assert match and match[1] not in audit, line
            audit[match[1]] = [] if match[2] is None else match[2].split(", ")
            assert set(audit[match[1]]) <= AXIOMS, line
    assert set(audit) == CLAIMS and len(observed) == len(starts_and_limits)
    return audit, observed


def main():
    if not __debug__:
        raise SystemExit("run without Python optimization to enable the assertions")
    parser = argparse.ArgumentParser()
    parser.add_argument("--without-lean", action="store_true")
    parser.add_argument("--linux-file-events", action="store_true")
    opts = parser.parse_args()
    py = os.environ.get("PYTHON", "python3")
    node = os.environ.get("NODE", "node")
    lean = os.environ.get("LEAN", "lean")
    # Baseline files below are frozen repository artifacts, never current code.
    names = ("python", "typescript")
    paths = (EXAMPLE / "page.py", EXAMPLE / "page.ts")
    prefix = ([py, "-B"], [node])
    changed_rows = [row[:] for row in ROWS]
    changed_rows[5] = [ROWS[5][0], "18446744073709551617", "U"]
    raw = blob(ROWS)
    cur_id = digest(raw)
    starts_and_limits = [(start, limit) for start in range(len(ROWS) + 1) for limit in LIMITS]

    with tempfile.TemporaryDirectory(prefix="pinned-walk-") as tmp:
        base = Path(tmp)
        checkpoint = (base / "snapshot.jsonl").resolve()
        legacy = []
        for launch, path in zip(prefix, paths, strict=True):
            old = (EXAMPLE / "baseline" / path.name).read_bytes()
            file = base / ("legacy" + path.suffix)
            file.write_bytes(old)
            legacy.append([*launch, str(file)])
        candidate = [[*launch, str(file)] for launch, file in zip(prefix, paths, strict=True)]

        def call(client, req, *, batch=False, count=False):
            args = [*client, str(checkpoint), *(["--walk"] if batch else [])]
            if not count or not opts.linux_file_events:
                return json.loads(run(args, json_line(req))), None
            # Exclusively the synthetic file; no privileged tracing or stdout hook.
            from ctypes import CDLL, c_char_p, c_int, c_uint32
            from struct import Struct

            lib = CDLL(None, use_errno=True)
            lib.inotify_init1.argtypes = [c_int]
            lib.inotify_add_watch.argtypes = [c_int, c_char_p, c_uint32]
            flags = {"opens": 0x20, "access": 0x01, "read_only_closes": 0x10}
            wd_mask = sum(flags.values())
            fd = lib.inotify_init1(os.O_NONBLOCK | os.O_CLOEXEC)
            assert fd >= 0, "inotify init unavailable"
            try:
                wd = lib.inotify_add_watch(fd, os.fsencode(checkpoint), wd_mask)
                assert wd >= 0, "could not watch the synthetic snapshot"
                value = json.loads(run(args, json_line(req)))
                events = {key: 0 for key in flags}
                event = Struct("iIII")
                while True:
                    try:
                        buf = os.read(fd, 65536)
                    except BlockingIOError:
                        break
                    i = 0
                    while i < len(buf):
                        descriptor, mask, _, length = event.unpack_from(buf, i)
                        assert descriptor == wd and length == 0, (descriptor, mask, length)
                        for key, flag in flags.items():
                            events[key] += bool(mask & flag)
                        i += event.size + length
                assert events["opens"] == events["read_only_closes"] == 1 and events["access"] >= 1, events
                return value, events["opens"]
            finally:
                os.close(fd)

        replace(checkpoint, raw)
        for start, limit in starts_and_limits:
            cursor = None if start == 0 else [cur_id, ROWS[start-1][0]]
            req = [cursor, str(limit)]
            want = oracle(ROWS, start, limit, cur_id)
            for old, new in zip(legacy, candidate, strict=True):
                assert call(new, req, batch=True)[0] == want, (new, req)
                # One-page default results remain byte-syntax-identical parsed JSON.
                expected_next = want[2][0][1]
                check = ["ok", cur_id, want[2][0][0],
                         [cur_id, expected_next] if expected_next is not None else None]
                assert call(new, req)[0] == call(old, req)[0] == check, req

        start = 5
        request = [[cur_id, ROWS[start-1][0]], "1"]
        correct = oracle(ROWS, start, 1, cur_id)
        replace(checkpoint, raw)
        assert all(call(client, request, batch=True)[0] == correct for client in candidate)
        replace(checkpoint, blob(changed_rows))
        shifted_id = digest(blob(changed_rows))
        for client in candidate:
            assert call(client, request, batch=True)[0] == ["err", "checkpoint-changed"]
            assert call(client, [None, "1"], batch=True)[0] == oracle(changed_rows, 0, 1, shifted_id)
        no_pin = base / "no_pin.ts"
        ts_text = paths[1].read_text()
        guard = "if (cursor[0] !== id)"
        stride = "i += n"
        assert ts_text.count(guard) == ts_text.count(stride) == 1
        no_pin.write_text(ts_text.replace(guard, "if (false)"))
        stale_fault = call([node, str(no_pin)], request, batch=True)[0]
        assert stale_fault == oracle(changed_rows, start, 1, shifted_id) and shifted_id != cur_id
        skip_row = base / "skip_row.ts"
        skip_row.write_text(ts_text.replace(stride, "i += n + 1"))
        replace(checkpoint, raw)
        omit_fault = call([node, str(skip_row)], request, batch=True)[0]
        witness_key = ROWS[start+1][0]
        assert omit_fault != correct and all(
            row[0] != witness_key for part, _ in omit_fault[2] for row in part
        ), omit_fault

        for req, err in (
            ([None, 1], "bad-request"), ([None, "0"], "bad-request"),
            ([None, "101"], "bad-request"), ([[cur_id, "01"], "1"], "bad-cursor"),
            ([[cur_id, "0\n"], "1"], "bad-cursor"),
            ([[cur_id, "1"], "1"], "unknown-boundary"),
        ):
            assert all(call(client, req, batch=True)[0] == ["err", err] for client in candidate)
        for broken in (raw + b'["999","7","X"]\n', b'x' * (256 * 1024 + 1)):
            replace(checkpoint, broken)
            assert all(call(client, [None, "1"], batch=True)[0] == ["err", "bad-checkpoint"]
                       for client in candidate)
        replace(checkpoint, b"")
        assert all(call(client, [None, "1"], batch=True)[0] == oracle([], 0, 1, digest(b""))
                   for client in candidate)

        rows = [[str(10**120 + i*7), str(10**120 + i*13), "D" if i%7 == 0 else "U"]
                for i in range(1000)]
        data = blob(rows)
        assert len(data) == 254000
        replace(checkpoint, data)
        snapshot_id, limit = digest(data), 37
        want = oracle(rows, 0, limit, snapshot_id)
        pages = []
        legacy_opens = 0
        token = None
        for i in range(len(want[2])):
            response, stats = call(legacy[i%2], [token, str(limit)], count=True)
            tag, version, page, token = response
            assert tag == "ok" and version == snapshot_id
            pages.append([page, token[1] if token else None])
            if token:
                assert token[0] == snapshot_id
            if stats is not None:
                legacy_opens += stats
        assert token is None and pages == want[2]
        walk_io = {}
        for name, client in zip(names, candidate, strict=True):
            response, stats = call(client, [None, str(limit)], batch=True, count=True)
            assert response == want
            if stats is not None:
                assert legacy_opens >= 10 * stats
                walk_io[name] = {"opens": stats, "exact_snapshot_bytes_validated": stats * len(data)}

        report = {
            "base": BASE, "python": run([py, "--version"]), "node": run([node, "--version"]),
            "walks_matching_ordinal_oracle_per_runtime": len(starts_and_limits),
            "legacy_page_compatibility_per_runtime": len(starts_and_limits),
            "negative_controls": {"pin_clause_disabled": "wrong_snapshot_admitted",
                                  "stride_plus_one": {"omitted_key": witness_key}},
            "scale": {"rows": len(rows), "bytes": len(data), "pages": len(pages), "page_size": limit,
                      "snapshot_sha256": snapshot_id},
            "linux_snapshot_open_events": None if not opts.linux_file_events else {
                "alternating_legacy": {"opens": legacy_opens,
                                       "exact_snapshot_bytes_validated": legacy_opens * len(data)},
                "pinned_walk_each": walk_io,
                "validated_read_reduction_factor_each": legacy_opens,
            },
        }
        if not opts.without_lean:
            audit, observed = checked_lean(lean, base, ROWS, starts_and_limits)
            assert observed == [[part for part, _ in oracle(ROWS, start, limit, cur_id)[2]]
                                for start, limit in starts_and_limits]
            report["lean"] = {"version": run([lean, "--version"]), "walks": len(observed), "theorems": audit}
    print(json.dumps(report, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()

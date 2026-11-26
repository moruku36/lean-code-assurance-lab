"""Read one page of a local synthetic checkpoint."""
import hashlib
import json
from pathlib import Path
import re
import sys

MAX_BYTES = 256 * 1024
NAT = re.compile(r"0|[1-9][0-9]{0,127}")
HASH = re.compile(r"[0-9a-f]{64}")
LIMIT = re.compile(r"[1-9][0-9]?|100")


def valid(pattern, value):
    return isinstance(value, str) and pattern.fullmatch(value) is not None


def read_snapshot(path):
    with path.open("rb") as handle:
        raw = handle.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES or (raw and not raw.endswith(b"\n")):
        raise ValueError
    lines = raw[:-1].decode("utf-8").split("\n") if raw else []
    rows = []
    previous = -1
    for line in lines:
        row = json.loads(line)
        if (not isinstance(row, list) or len(row) != 3 or
                not valid(NAT, row[0]) or not valid(NAT, row[1]) or
                row[2] not in ("U", "D") or
                json.dumps(row, separators=(",", ":")) != line):
            raise ValueError
        key = int(row[0])
        if key <= previous:
            raise ValueError
        previous = key
        rows.append(row)
    return hashlib.sha256(raw).hexdigest(), rows


def request_error(request):
    if not isinstance(request, list) or len(request) != 2:
        return "bad-request"
    cursor, limit = request
    if not valid(LIMIT, limit):
        return "bad-request"
    if cursor is not None and (
        not isinstance(cursor, list) or len(cursor) != 2 or
        not valid(HASH, cursor[0]) or not valid(NAT, cursor[1])
    ):
        return "bad-cursor"
    return None


def read_page(path, request):
    if error := request_error(request):
        return ["err", error]
    cursor, limit = request
    try:
        snapshot_id, rows = read_snapshot(path)
    except (OSError, ValueError, RecursionError):
        return ["err", "bad-checkpoint"]
    if cursor is not None and cursor[0] != snapshot_id:
        return ["err", "checkpoint-changed"]
    cut = -1 if cursor is None else int(cursor[1])
    if cursor is not None and not any(int(r[0]) == cut for r in rows):
        return ["err", "unknown-boundary"]
    n = int(limit)
    rest = [r for r in rows if int(r[0]) > cut]
    result = rest[:n]
    return ["ok", snapshot_id, result, [snapshot_id, result[-1][0]] if len(rest) > n else None]


def read_walk(path, request):
    """Return a traversal of one captured version, without re-opening the file."""
    if error := request_error(request):
        return ["err", error]
    cursor, limit = request
    try:
        snapshot_id, rows = read_snapshot(path)
    except (OSError, ValueError, RecursionError):
        return ["err", "bad-checkpoint"]
    start = 0
    if cursor is not None:
        if cursor[0] != snapshot_id:
            return ["err", "checkpoint-changed"]
        # Canonical decimal syntax makes string equality exact at the boundary.
        start = next((i + 1 for i, row in enumerate(rows) if row[0] == cursor[1]), 0)
        if start == 0:
            return ["err", "unknown-boundary"]
    n = int(limit)
    pages = []
    for i in range(start, len(rows), n):
        end = min(i + n, len(rows))
        pages.append([rows[i:end], rows[end - 1][0] if end < len(rows) else None])
    return ["ok", snapshot_id, pages or [[[], None]]]


if __name__ == "__main__":
    if not (len(sys.argv) == 2 or (len(sys.argv) == 3 and sys.argv[2] == "--walk")):
        raise SystemExit("usage: page.py CHECKPOINT [--walk]")
    try:
        req = json.load(sys.stdin)
    except (ValueError, RecursionError):
        print('["err","bad-request"]')
    else:
        read = read_page if len(sys.argv) == 2 else read_walk
        print(json.dumps(read(Path(sys.argv[1]), req), separators=(",", ":")))

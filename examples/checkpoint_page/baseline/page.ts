// Node.js 24 executes the TypeScript entry point with type stripping.
import { openSync, readSync, closeSync, readFileSync } from "node:fs";
import { createHash } from "node:crypto";

type Row = [string, string, "U" | "D"];
type Cursor = [string, string];

const CAP = 256 * 1024;
// JavaScript's "$" can match before a trailing newline; use a real end assertion.
const NAT = /^(?:0|[1-9][0-9]{0,127})(?![\s\S])/;
const HASH = /^[0-9a-f]{64}(?![\s\S])/;
const LIMIT = /^(?:[1-9][0-9]?|100)(?![\s\S])/;

function valid(pattern: RegExp, value: unknown): value is string {
  return typeof value === "string" && pattern.test(value);
}

function key(s: string): bigint {
  return BigInt(s);
}

function readSnapshot(path: string): [string, Row[]] {
  const buffer = Buffer.alloc(CAP + 1);
  const fd = openSync(path, "r");
  let length = 0;
  try {
    while (length < buffer.length) {
      const n = readSync(fd, buffer, length, buffer.length - length, null);
      if (n === 0) break;
      length += n;
    }
  } finally {
    closeSync(fd);
  }
  const raw = buffer.subarray(0, length);
  if (raw.length > CAP || (raw.length !== 0 && raw.at(-1) !== 10)) throw new Error();
  const lines = raw.length
    ? new TextDecoder("utf-8", {fatal: true, ignoreBOM: true}).decode(raw.subarray(0, -1)).split("\n")
    : [];
  const rows: Row[] = [];
  let previous = -1n;
  for (const line of lines) {
    const row: unknown = JSON.parse(line);
    if (!Array.isArray(row) || row.length !== 3 || !valid(NAT, row[0]) ||
        !valid(NAT, row[1]) || (row[2] !== "U" && row[2] !== "D") ||
        JSON.stringify(row) !== line) throw new Error();
    const current = key(row[0]);
    if (current <= previous) throw new Error();
    previous = current;
    rows.push(row as Row);
  }
  return [createHash("sha256").update(raw).digest("hex"), rows];
}

function readPage(path: string, req: unknown) {
  if (!Array.isArray(req) || req.length !== 2 || !valid(LIMIT, req[1])) return ["err", "bad-request"];
  const [cursor, limit] = req;
  if (cursor !== null && (!Array.isArray(cursor) || cursor.length !== 2 ||
      !valid(HASH, cursor[0]) || !valid(NAT, cursor[1]))) return ["err", "bad-cursor"];
  let id: string, rows: Row[];
  try {
    [id, rows] = readSnapshot(path);
  } catch {
    return ["err", "bad-checkpoint"];
  }
  const typed = cursor as Cursor | null;
  if (typed !== null && typed[0] !== id) return ["err", "checkpoint-changed"];
  const cut = typed === null ? -1n : key(typed[1]);
  if (typed !== null && !rows.some(row => key(row[0]) === cut)) return ["err", "unknown-boundary"];
  const n = Number(limit); // This is bounded to 100, unlike keys and revisions.
  const rest = rows.filter(row => key(row[0]) > cut);
  const result = rest.slice(0, n);
  return ["ok", id, result, rest.length > n ? [id, result.at(-1)![0]] : null];
}

if (process.argv.length !== 3) throw new Error("usage: page.ts CHECKPOINT");
let req: unknown;
try {
  req = JSON.parse(readFileSync(0, "utf8"));
} catch {
  console.log('["err","bad-request"]');
  process.exit(0);
}
console.log(JSON.stringify(readPage(process.argv[2], req)));

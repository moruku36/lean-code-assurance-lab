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

function requestError(req: unknown) {
  if (!Array.isArray(req) || req.length !== 2 || !valid(LIMIT, req[1])) return "bad-request";
  const [cursor] = req;
  if (cursor !== null && (!Array.isArray(cursor) || cursor.length !== 2 ||
      !valid(HASH, cursor[0]) || !valid(NAT, cursor[1]))) return "bad-cursor";
  return null;
}

function readPage(path: string, req: unknown) {
  const error = requestError(req);
  if (error !== null) return ["err", error];
  const [cursor, limit] = req as [Cursor | null, string];
  let id: string, rows: Row[];
  try {
    [id, rows] = readSnapshot(path);
  } catch {
    return ["err", "bad-checkpoint"];
  }
  const typed = cursor;
  if (typed !== null && typed[0] !== id) return ["err", "checkpoint-changed"];
  const cut = typed === null ? -1n : key(typed[1]);
  if (typed !== null && !rows.some(row => key(row[0]) === cut)) return ["err", "unknown-boundary"];
  const n = Number(limit); // This is bounded to 100, unlike keys and revisions.
  const rest = rows.filter(row => key(row[0]) > cut);
  const result = rest.slice(0, n);
  return ["ok", id, result, rest.length > n ? [id, result.at(-1)![0]] : null];
}

function readWalk(path: string, req: unknown) {
  const error = requestError(req);
  if (error !== null) return ["err", error];
  const [cursor, limit] = req as [Cursor | null, string];
  let id: string, rows: Row[];
  try {
    [id, rows] = readSnapshot(path);
  } catch {
    return ["err", "bad-checkpoint"];
  }
  let start = 0;
  if (cursor !== null) {
    if (cursor[0] !== id) return ["err", "checkpoint-changed"];
    // A canonical decimal key can be matched by string without rounding.
    start = rows.findIndex(row => row[0] === cursor[1]) + 1;
    if (start === 0) return ["err", "unknown-boundary"];
  }
  const n = Number(limit);
  const pages: [Row[], string | null][] = [];
  for (let i = start; i < rows.length; i += n) {
    const end = Math.min(i + n, rows.length);
    pages.push([rows.slice(i, end), end < rows.length ? rows[end - 1][0] : null]);
  }
  return ["ok", id, pages.length ? pages : [[[], null]]];
}

const walk = process.argv.length === 4 && process.argv[3] === "--walk";
if (process.argv.length !== 3 && !walk) throw new Error("usage: page.ts CHECKPOINT [--walk]");
let req: unknown;
try {
  req = JSON.parse(readFileSync(0, "utf8"));
} catch {
  console.log('["err","bad-request"]');
  process.exit(0);
}
console.log(JSON.stringify((walk ? readWalk : readPage)(process.argv[2], req)));

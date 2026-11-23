import { readFileSync } from "node:fs";
import { pathToFileURL } from "node:url";

export function reserve(capacity: bigint, used: bigint, request: bigint): bigint | null {
  const next = used + request;
  return next > capacity ? null : next;
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  for (const line of readFileSync(0, "utf8").trimEnd().split(/\r?\n/)) {
    if (!/^\d+ \d+ \d+$/.test(line)) throw new Error("expected: capacity used request");
    const [capacity, used, request] = line.split(" ").map(BigInt);
    const result = reserve(capacity, used, request);
    console.log(result === null ? "reject" : result.toString());
  }
}

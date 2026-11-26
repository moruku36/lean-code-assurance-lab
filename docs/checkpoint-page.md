# Checkpoint pagination with exact integer keys

[日本語](checkpoint-page.ja.md) · [Research plan](experiments.md)

## Question and contract

Does a consumer read every row exactly once if it follows a cursor across independently running Python and TypeScript processes? A writer can replace an entire file atomically, yet two page reads can still mix snapshots. The cursor contains the digest of the file bytes it read and the last exact key. Following it against different bytes returns `checkpoint-changed`, rather than silently continuing. On such an error, discard the partial traversal and start again; do not append pages fetched under different snapshot identifiers.

This is an independent, synthetic adapter case, not a production storage implementation. The checkpoint contains no data other than canonical ASCII JSON Lines of `["key","revision","U" or "D"]`, LF terminated, at most 256 KiB. Keys are strictly ascending and unique. Keys and revisions are canonical decimal strings of 1–128 digits and never JSON number tokens. `U` is a live row and `D` a retained deletion record. An empty file is a valid empty checkpoint. There is no filter that discards deletion rows.

The CLI takes a checkpoint path and one JSON request on stdin: `[cursor, "limit"]`. The limit is a canonical decimal string from 1 to 100. Start with a null cursor. A successful reply is `["ok",digest,rows,nextCursor]`. The next cursor is either null (done) or `[digest,lastKey]`. The operand of the numeric comparison is `int` in Python and `bigint` in TypeScript, not IEEE-754 `Number`. The two implementations read, validate and hash the same opened byte buffer per call.

## Replay and result

With the already installed Lean 4.19.0, Python 3.10+ and Node.js 24+, run:

```sh
python3 -B scripts/check_checkpoint_page.py --without-lean
LEAN=/absolute/path/to/lean python3 -B scripts/check_checkpoint_page.py
```

[Recorded result](../evidence/checkpoint-page.json) · [Typed model](../CheckpointPage.lean) · [CLI implementations](../examples/checkpoint_page/)

- Both real CLIs matched the independent row-index oracle on **54** page requests each, including adjacent keys around 2^53, 2^64 and a 128-digit key. They agreed on **12** traversals that used separate and alternating Python/TypeScript processes. Both rejected 10 invalid requests and 15 bad or missing checkpoints and accepted an empty checkpoint.
- The numeric negative control compared only the resume boundary using JavaScript `Number`. It disagreed in **6** requests, skipping `9007199254740993` after `9007199254740992`. The unbound-cursor control wrongly returned a changed revision under a different snapshot ID and omitted a new key below the cursor. The good CLIs reject both stale continuations. When the file is replaced with identical bytes, both still resume correctly.
- Lean checks the typed exact-identity rule and the suffix after a boundary in a strictly ordered list. Its executable model agrees on the same 54 valid page results. The ordinary tests already catch both planted defects: **no additional defect detected by adding Lean** in this synthetic case. This is not a fresh blind or cost-controlled agent comparison.

## Evidence boundary

The Lean identity is equality of typed rows, not equality of SHA-256 digests. The proofs do not certify the byte encoding, parser, hash implementation, filesystem, or process interactions. The finite CLI test stages and atomically replaces a sibling file between page reads on local Linux, no concurrent instruction interleaving or crash/power-loss claim. File contents and cursor are local and trusted, not authorization tokens. Read and hash work is proportional to checkpoint size on every call. A real service would need a separate design for version retention, long scans amid frequent writes, process permissions, crash recovery and operating systems other than the observed Linux. Node executed the type-stripped TypeScript entry point; no separate static TypeScript type check was performed.

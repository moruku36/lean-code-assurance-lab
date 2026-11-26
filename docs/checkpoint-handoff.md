# Preserving exact cursors across modes and runtimes

[日本語](checkpoint-handoff.ja.md) · [One-buffer traversal](checkpoint-walk.md)

The opt-in walk returns the snapshot digest once and a decimal boundary key per nonterminal page. Treat that key as an opaque string, not a number. A receiving process reconstructs `[snapshotDigest, boundaryKey]` and may change the page size. A wrong digest must be rejected, but the digest does **not** assert the caller's traversal history: another valid key in the same snapshot means "start after this key."

The frozen baseline is `85f0b52d8c3f75d825140f0eb82d17800f7fe606`. Neither CLI implementation was modified. Run `LEAN=/path/to/lean python3 -B scripts/check_checkpoint_handoff.py` with Lean 4.19.0, Python 3.10+ and Node.js 24+.

- **40** synthetic handoffs (10 boundaries × 2 runtime directions × 2 mode directions) matched an independent ordinal oracle. The receiver changed page size where the bounded matrix dictated. Joining the retained prefix and resumed suffix reproduced the exact rows, including tombstones, around 2^53, 2^64 and 127-/128-digit boundaries. The walk returns its whole response at once; this test simulates a client keeping just its first page, not mid-stream delivery.
- In a deliberately lossy Node adapter, `String(Number("9007199254740993"))` became `"9007199254740992"`, which already exists in the same file. Both CLI modes in both runtimes accepted the rounded key under the correct digest and returned `9007199254740993` again. This is client-side replay from a different valid boundary, not a mismatch between the intended CLI contracts. Converting a 128-digit key produced exponent notation, which both refused; a 129-digit decimal key was also refused.
- After byte-identical atomic replacement the exact token resumed; after changing a revision, all four reader combinations rejected the old cursor. The file replacements happened between calls, not during a read.
- Lean checked two typed properties: with a positive page size and strictly sorted keys, exact handoff reconstructs the original with its preserved prefix. Handing off using the immediately preceding key replays the intended boundary row. Its executed walk model matched the 10 typed suffix cases. The formal model has exact naturals; it does not prove the parser, floating-point conversion, or actual file semantics. The witness was reproducible with ordinary tests, not an additional finding unique to Lean.

[Recorded result](../evidence/checkpoint-handoff.json). Use the checks as a regression replay for clients, not as a new authentication or production claim.

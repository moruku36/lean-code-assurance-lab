# One-buffer checkpoint walk

[日本語](checkpoint-walk.ja.md) · [Single-page contract](checkpoint-page.md)

## Question

Can a local traversal return the same exact pages without opening and validating the whole checkpoint on every page? This synthetic follow-up starts from local baseline `9ba3ede95ff23dd15bf9b406b42eeb8a28883dd7`. Ordinary one-page commands keep their existing input, output and fresh-open behavior. This is an opt-in coherent snapshot, not a live reader. The exact baseline scripts are included in [the baseline directory](../examples/checkpoint_page/baseline/) so replay works without the original local commit history.

Use the same request on stdin, with `--walk` as the last command argument. For example:

```sh
printf '%s' '[null,"37"]' | python3 -B examples/checkpoint_page/page.py sample.jsonl --walk
printf '%s' '[null,"37"]' | node examples/checkpoint_page/page.ts sample.jsonl --walk
```

Both modes require ordered, canonical decimal string keys and revisions (up to 128 digits) and canonical JSON Lines at most 256 KiB. `--walk` opens the file once, validates it to the end, hashes the captured buffer once and returns `["ok", digest, [[rows, nextKeyOrNull], ...]]`. A nonnull exact decimal key reconstructs a regular cursor `[digest,nextKey]`. The last page has a null key. An empty or exhausted checkpoint yields one empty terminal page. A start cursor referring to different bytes returns `checkpoint-changed`; identical bytes permit resumption. A malformed final line fails the whole request without partial pages. The reader holds the validated rows and response in memory, so this is not an unbounded streaming interface.

## Evidence

```sh
# Requires the baseline Git object named above, Python 3.10+ and Node 24+.
python3 -B scripts/check_checkpoint_walk.py --without-lean
# The Linux event observer is optional. Unprivileged inotify watches only the synthetic input file.
LEAN=/path/to/lean python3 -B scripts/check_checkpoint_walk.py --linux-file-events
```

- Both actual CLIs matched an independent ordinal-slice oracle on **54 walks each**, including adjacent keys `9007199254740992` and `9007199254740993`, tombstones, and an already exhausted cursor. Each default CLI matched the unmodified baseline on another **54** calls. Tests cover initial version drift, same-byte replacement, malformed tail/oversize, invalid requests and empty checkpoints.
- For **1,000 rows / 254,000 bytes**, the 28 pages (page size 37) matched the independently launched, alternating Python and TypeScript legacy CLIs, including all cursor positions and the SHA-256. The Linux file observer saw **28 opens** for the legacy traversal and **one open** for either pinned walk. That accounts for 7,112,000 vs. 254,000 exact-version bytes validated (28× fewer); it is not a measurement of disk/physical I/O, latency or throughput. No kernel tracing privileges were granted or needed.
- A removed version check wrongly admitted a changed snapshot. A one-row stride error skipped `18446744073709551616`. Both controls were caught by ordinary tests. Lean 4.19.0 checked four named theorems with warnings as errors and axiom audit; its executed model matched 54 typed walks. The key guarantee is exact ordered coverage of the typed suffix for a positive limit, with typed version rejection. This synthetic experiment found no extra defect uniquely attributable to Lean.

Lean proves properties of its typed model, not the parser, hash function, operating system or CLI source. Replacement tests occur between process calls. The reader does not guarantee freshness after open, history retention, concurrent in-place writing, crash recovery, adversarial artifact handling, or performance on other hosts. Do not replace ordinary one-page mode when observing changes between requests is required. [Replay record](../evidence/checkpoint-walk.json).

For consumers handing off between modes, see [exact cursor transport](checkpoint-handoff.md).

# Lean Code Assurance Lab

[日本語](README.ja.md) · [Architecture](docs/architecture.md) · [Research plan](docs/experiments.md) · [Reading list](docs/sources.md)

Can an AI agent use Lean to give a maintainer good reasons to trust a change to a Python, TypeScript or Rust service? This lab starts with one decision at a time. A maintainer states what must hold, an agent proposes a model and proof, and a repeatable check connects that model to the code people actually run.

## Start with a reservation

A service has capacity 10, has already allocated 7 units, and receives a request for 3. It should accept and return 10. A request for 4 should be refused. A system that rejects every request would stay under capacity while being useless. The Lean specification therefore covers **both what must succeed and what must fail**.

| Question | Where to see the evidence |
| --- | --- |
| Does every accepted reservation respect capacity, for all natural-number inputs? | [Three theorems checked by Lean](Reservation.lean) and [their axiom audit](Audit.lean) |
| Do the actual Python and TypeScript functions agree with the executable model? | [Both implementations](examples/reservation/) and [the runner](scripts/check.py) compare 518 fixed input triples per language, including exact fills and large integers. |
| Would the comparison notice a realistic mistake? | The runner changes the inclusive boundary to a strict one in a control implementation and prints a concrete disagreement. |

```mermaid
flowchart TD
    C["Reviewed rule and input domain"] --> M["Executable Lean specification"]
    M --> P["Lean checks the universal claims"]
    M --> O["Oracle runs on fixed inputs"]
    I["Python or TypeScript implementation"] --> D["Compare actual outputs"]
    O --> D
    P --> R["Review the proof, cases and assumptions"]
    D --> R
```

## Replay it

Install Lean with Elan, Python 3.10+ and Node.js 24+. From the repository root, run the following command. It builds the pinned Lean toolchain's project, inspects the proof dependencies, runs both implementations and prints a JSON evidence record. The first build can download Lean. [Lean installation](https://lean-lang.org/install/)

```sh
python scripts/check.py
```

On systems where Python is named `python3`, use `python3 scripts/check.py`. The first public run checked all three theorems, matched 518 cases per language and detected the incorrect boundary in 40 cases. Read the [recorded JSON](evidence/reservation-baseline.json), [current CI runs](https://github.com/moruku36/lean-code-assurance-lab/actions/workflows/assurance.yml) or the [guided walkthrough](docs/walkthrough.md).

## Lean 4 results so far

- **Reviewer comparison:** The [first held-out pilot](docs/stage-1-lean-pilot-results.md) found no additional defects with Lean across six revisions. Lean is not a default review requirement.
- **Exact pagination:** The [checkpoint case](docs/checkpoint-page.md) matched 54 page requests per language and 12 alternating traversals. A changed snapshot rejects the old cursor.
- **One-buffer traversal:** On a synthetic 1,000-row fixture, the [opt-in walk](docs/checkpoint-walk.md) returned the same 28 pages with **one file open instead of 28** on Linux. This is not a wall-clock benchmark.
- **Cursor handoff:** [40 Python/TypeScript handoffs](docs/checkpoint-handoff.md) matched the reference. Keep cursor keys as decimal strings: converting them to JavaScript `Number` can round a key and replay a row even with the correct snapshot hash.

Run the checkpoint checks from the repository root with Lean 4.19.0, Python and Node.js:

```sh
python3 -B scripts/check_checkpoint_page.py
python3 -B scripts/check_checkpoint_walk.py
python3 -B scripts/check_checkpoint_handoff.py
```

The proofs cover the typed model. The executable checks separately cover the recorded parsing and file cases. Ordinary tests also caught the deliberately introduced errors; this is not evidence that Lean catches more defects in production.

## Where the research goes next

| Track | What you can use here |
| --- | --- |
| Python and TypeScript | Runnable reservation and checkpoint examples. The [research plan](docs/experiments.md) separates development cases from future held-out review comparisons. |
| Rust | A planned pilot on one safe, fixed-width function using Aeneas. The [architecture](docs/architecture.md) describes which translation assumptions a source-level claim would inherit. |
| An existing service | A protocol for bringing in one versioned decision function, its input contract and sanitized examples. The [agent instructions](AGENTS.md) define what counts as evidence. |

A passing run supports the named properties of the model and agreement on the recorded cases. The production adapter, concurrency, code readability and broader security each need their own claim or review. [Evidence boundaries](docs/architecture.md)

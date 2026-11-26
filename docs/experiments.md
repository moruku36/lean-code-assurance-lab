# Research plan

[日本語](experiments.ja.md) · [Home](../README.md) · [Agent instructions](../AGENTS.md)

**Research question.** With a fixed review budget, does giving an AI agent an executable Lean specification and proof checker help maintainers catch more incorrect changes to ordinary service code, while accepting legitimate changes?

| Stage | Question and experiment | Decision or evidence |
| --- | --- | --- |
| 0 · Learn and replay | Build the reservation proof and run the same examples against Python and TypeScript. Include an exact-fill mutant. | A replayable worked example exists. It establishes a baseline for the harness. [Observed run](https://github.com/moruku36/lean-code-assurance-lab/actions/runs/45159429077) |
| 1 · Compare agent workflows | Choose three independent, side-effect-free decisions, e.g. capacity, time-window inclusion and retry admission. Reserve a correct change and an incorrect one for each. | A paired pilot on six unseen revisions. Record which changes each arm classified correctly and why. |
| 2 · Bring in one service | A maintainer supplies one existing Python or TypeScript function pinned to a commit, realistic sanitized examples, and a domain rule independent of the implementation. | Run the real function against a separately reviewed oracle. Publish the scoped result, permission permitting, or a synthetic public reproducer. |
| 3 · Link a Rust source | Choose one safe Rust function with explicit overflow policy. Attempt a pinned translation with Aeneas, prove the property of its output, and replay boundary cases against the source. | Record the source-to-model correspondence, remaining translator assumptions, or the exact unsupported feature. |
| 4 · Extend to state | Model a sequence such as reserve, cancel, retry; add storage or concurrency semantics one at a time. | Report an invariant on reachable states and a real trace that exercises its boundary. |

The [first held-out result](stage-1-lean-pilot-results.md) is now recorded. Adding Lean 4 did not increase defect detection in the six-revision pilot. Lean is not a default review requirement; the next comparison targets large-integer exchange and ordering.

Development case: [checkpoint pagination](checkpoint-page.md) uses exact integer keys and checks snapshot identity. This synthetic case is not part of the held-out workflow study. [One-buffer traversal](checkpoint-walk.md) tests a reduced read count while preserving this separate local mode.

## The first comparative experiment

1. A maintainer fixes the natural-language contract, reference outcomes, clean starting revision, allowed files and budgets in advance. Another person or process holds back the labeled revisions and final cases from the agent. Include valid changes to measure false alarms.
2. Give two fresh workspaces the same candidate, requirements, model version, initial tests, clock and token limit. Arm A can write and run ordinary tests. Arm B additionally has Lean, the oracle and the proof checker. Alternate the order across cases. Count specification authoring and review time explicitly, including setup provided to just one arm.
3. Freeze both answers before revealing labels. For each revision record accept/reject/undetermined, true outcome, a replayable witness or theorem, wall time, tokens, human minutes and environment failures. Review disagreements without the arm labels where practical.
4. Report paired counts for defects found, valid changes wrongly rejected, and unresolved cases; include the actual cases and costs. Use the function or change as the unit of comparison. Thousands of generated inputs for one function still represent one target.
5. Treat this small pilot as exploratory. Advance unchanged to fresh functions if the Lean arm contributes a replayable detection unique to that arm, adds no false rejection in the pilot, and stays within the agreed budget. If the result is mixed, retain the disagreement and revise the protocol using development cases; retire exposed cases from the unseen pool.

**A useful failure mode to test.** Give the reviewer a plausible but weak contract, such as “all accepted reservations stay under the limit.” Always rejecting satisfies it. Require a positive witness and a theorem describing when acceptance is mandatory. A counterexample to the implementation and a counterexample to the adequacy of the specification require different fixes.

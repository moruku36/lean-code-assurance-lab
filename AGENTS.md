# Agent instructions for assurance cases

Start with the [worked case](docs/walkthrough.md), the [evidence boundaries](docs/architecture.md) and the [paired study protocol](docs/experiments.md). These instructions apply to an agent working in a local checkout. Any model or coding assistant can take this role.

## Intake

Record the source revision and function, intended behavior, domain and data types, effects, excluded behavior, at least one accepted and one refused example, and the human owner of the rule. If the contract is ambiguous, identify the competing outcomes and keep the claim open until the owner resolves them. Keep real inputs and service credentials in the owner's environment.

## Work loop

1. Freeze the contract and baseline before editing the candidate. In a comparative study record model version, tools and budget. Keep final cases and labels with the evaluator.
2. Express the smallest relevant function in Lean. State the success and failure conditions, then try a meaningless implementation such as always refusing. Write a property that distinguishes it if the requirement excludes that behavior.
3. Propose the proof and run `python scripts/check.py` for the reservation case. Inspect each theorem's axiom report. For a new case add its claim names to the audit and an executable comparison to the actual implementation. A passing unrelated theorem provides no evidence about the new case.
4. Save the first replayable disagreement. Compare the requirement, adapter, implementation and model before assigning the fault. Escalate suggested contract changes to the maintainer and give the revised contract a new case version.
5. Report the revision, claim, input domain, evidence below and any remaining semantic gap. The maintainer decides whether it addresses the proposed service change.

| Report field | What to include |
| --- | --- |
| Source | Commit, path, symbol and local modifications |
| Model | Lean declaration, toolchain, exact theorem and accepted axioms |
| Execution | Runner command, runtime versions, input corpus or seed, counts and counterexample |
| Result | Record model proof and implementation agreement separately. Mark missing tools or broken adapters inconclusive. |
| Limits | Trusted translations, unmodeled effects, data representations and remaining review questions |

Use a clean checkout for shareable evidence. A proof placeholder, extra assumption or silently weakened theorem changes the claim. Report it for review. Keep the oracle independent of the candidate's implementation and record edits to either side.

## Opt-in checkpoint workflow review

For a change to the Python/TypeScript checkpoint handoff, use the [Lean4Agent-inspired harness](docs/lean4agent.md) when the review needs evidence about the order of the steps as well as their output. Freeze the public fixture and the model, run the harness, and report the first failed stage and its counterexample when available. A passing structural check or Lean proof does not replace replay of the actual implementations. This is not a new default CI or held-out scoring requirement.

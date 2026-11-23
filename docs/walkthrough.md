# Read your first proof

[日本語](walkthrough.ja.md) · [Home](../README.md) · [Architecture](architecture.md)

1. Open [the model](../Reservation.lean). `Nat` means a nonnegative whole number. `Option Nat` means either a new usage (`some next`) or refusal (`none`). Read the type of each `theorem` before looking at its proof.
2. Trace `capacity = 10, used = 7, request = 3`. `accept_if_fits` says exactly what the function returns. Change 3 to 4 and `reject_if_exceeds` says it must refuse. `accepted_within_capacity` starts from any successful result and proves its upper bound.
3. From the repository root run `python scripts/check.py`. To study just the Lean side, run `lake build` and then `lake env lean Audit.lean`. The [audit file](../Audit.lean) asks Lean which axioms each theorem depends on. The runner fails if an audited claim is missing or uses an axiom outside its allowlist.
4. Inspect `matching_rows` and `negative_control` in the JSON. The cases are every triple with components 0 through 7, plus six large-integer boundaries. In the [first passing replay](https://github.com/moruku36/lean-code-assurance-lab/actions/runs/45159429077), each language matched 518 rows, and the strict-boundary control disagreed on 40. The first witness was `(0,0,0)`; zero fits, so the model returns 0 and the control refuses.
5. Try a local experiment. In [the Python function](../examples/reservation/reserve.py), change `request > remaining` to `request >= remaining` and rerun. The proof still builds; the Python comparison stops at a concrete counterexample. Restore the comparison and rerun to recover the original record.

In a review, quote the property name, inputs covered and revision. Record an infrastructure error as an incomplete run. The axiom report and the 518 comparisons answer different questions about the same change.

namespace Reservation

/-- One atomic request against a capacity. All quantities are natural numbers. -/
def reserve (capacity used request : Nat) : Option Nat :=
  if used + request ≤ capacity then some (used + request) else none

theorem accept_if_fits (capacity used request : Nat) (h : used + request ≤ capacity) :
    reserve capacity used request = some (used + request) := by
  exact if_pos h

theorem reject_if_exceeds (capacity used request : Nat) (h : ¬ used + request ≤ capacity) :
    reserve capacity used request = none := by
  exact if_neg h

theorem accepted_within_capacity (capacity used request next : Nat)
    (accepted : reserve capacity used request = some next) : next ≤ capacity := by
  by_cases fits : used + request ≤ capacity
  · rw [accept_if_fits capacity used request fits] at accepted
    exact Option.some.inj accepted ▸ fits
  · rw [reject_if_exceeds capacity used request fits] at accepted
    cases accepted

end Reservation

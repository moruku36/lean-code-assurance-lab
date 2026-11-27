import Reservation

namespace ReservationWorkflow

def maxU64 : Nat := 18446744073709551615

-- Mathematical width guard, not an extraction or proof about Rust code.
def checkedModel (capacity used request : Nat) : Option Nat :=
  if used + request ≤ maxU64 then Reservation.reserve capacity used request else none

theorem width_guard_preserves_bounded_reservation (capacity used request : Nat)
    (boundedCapacity : capacity ≤ maxU64) :
    checkedModel capacity used request = Reservation.reserve capacity used request := by
  by_cases fitsWidth : used + request ≤ maxU64
  · simp [checkedModel, fitsWidth]
  · have failsReservation : ¬ used + request ≤ capacity :=
      fun h => fitsWidth (Nat.le_trans h boundedCapacity)
    rw [Reservation.reject_if_exceeds _ _ _ failsReservation]
    simp [checkedModel, fitsWidth]

inductive Step where
  | oracle
  | python
  | typescript
  | rust
  | receipt

-- Each modeled output is assumed only in the static pass.
structure Facts where
  oracle : Bool := false
  python : Bool := false
  typescript : Bool := false
  rust : Bool := false
  receipt : Bool := false

def allObserved (s : Facts) : Bool := s.python && s.typescript && s.rust

def advance (s : Facts) : Step → Option Facts
  | .oracle => some {s with oracle := true}
  | .python => if s.oracle then some {s with python := true} else none
  | .typescript => if s.oracle then some {s with typescript := true} else none
  | .rust => if s.oracle then some {s with rust := true} else none
  | .receipt => if allObserved s then some {s with receipt := true} else none

theorem receipt_requires_all_runtimes (s t : Facts)
    (issued : advance s .receipt = some t) : allObserved s = true := by
  by_cases h : allObserved s = true
  · exact h
  · simp [advance, h] at issued

def missing : Step → String
  | .receipt => "all-three-results-declared"
  | _ => "oracle-result-declared"

def firstUnmet : Facts → Nat → List Step → Option (Nat × String)
  | _, _, [] => none
  | facts, index, step :: rest =>
    match advance facts step with
    | none => some (index, missing step)
    | some next => firstUnmet next (index + 1) rest

def report (plan : List Step) : IO Unit :=
  match firstUnmet {} 0 plan with
  | none => IO.println "plan|pass"
  | some (i, predicate) => IO.println ("plan|" ++ toString i ++ "|" ++ predicate)

def emit (cases : List (Nat × Nat × Nat)) : IO Unit :=
  for (c,u,r) in cases do
    let outcome := match Reservation.reserve c u r with
      | some n => toString n
      | none => "reject"
    IO.println ("value|" ++ outcome)

end ReservationWorkflow

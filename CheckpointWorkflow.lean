import Std

namespace CheckpointWorkflow

inductive Step where
  | read
  | compare
  | receipt
  deriving Repr

-- These are abstract postconditions, not claims that any process provided them.
-- L3 establishes them separately for a concrete run.
structure Facts where
  pythonReady : Bool := false
  paired : Bool := false
  receiptReady : Bool := false

def advance (s : Facts) : Step → Option Facts
  | .read => some {s with pythonReady := true}
  | .compare => if s.pythonReady then some {s with paired := true} else none
  | .receipt => if s.paired then some {s with receiptReady := true} else none

theorem compare_requires_python (before after : Facts)
    (accepted : advance before .compare = some after) : before.pythonReady = true := by
  by_cases ready : before.pythonReady = true
  · exact ready
  · simp [advance, ready] at accepted

theorem receipt_requires_comparison (before after : Facts)
    (accepted : advance before .receipt = some after) : before.paired = true := by
  by_cases ready : before.paired = true
  · exact ready
  · simp [advance, ready] at accepted

def required : Step → String
  | .read => "no-prerequisite"
  | .compare => "python-observation-declared"
  | .receipt => "comparison-declared"

def firstUnmet : Facts → Nat → List Step → Option (Nat × String)
  | _, _, [] => none
  | facts, index, step :: rest =>
    match advance facts step with
    | none => some (index, required step)
    | some next => firstUnmet next (index + 1) rest

def report (plan : List Step) : IO Unit :=
  match firstUnmet {} 0 plan with
  | none => IO.println "plan|pass"
  | some (index, missing) => IO.println ("plan|" ++ toString index ++ "|" ++ missing)

end CheckpointWorkflow

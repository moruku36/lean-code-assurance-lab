import CheckpointPage

namespace CheckpointWalk

open CheckpointPage

def chunks (limit : Nat) : Nat → List Row → List (List Row)
  | 0, _ => []
  | _ + 1, [] => []
  | fuel + 1, row :: tail =>
      let rows := row :: tail
      rows.take limit :: chunks limit fuel (rows.drop limit)

theorem chunks_cover (limit fuel : Nat) (rows : List Row)
    (positive : 0 < limit) (enough : rows.length ≤ fuel) :
    (chunks limit fuel rows).flatten = rows := by
  induction fuel generalizing rows with
  | zero =>
    cases rows with
    | nil => rfl
    | cons row tail => simp at enough
  | succ fuel ih =>
    cases rows with
    | nil => rfl
    | cons row tail =>
      have fits : ((row :: tail).drop limit).length ≤ fuel := by
        simp only [List.length_cons] at enough
        rw [List.length_drop, List.length_cons]
        omega
      change (row :: tail).take limit ++ (chunks limit fuel ((row :: tail).drop limit)).flatten = row :: tail
      rw [ih _ fits, List.take_append_drop]

def walk (rows : List Row) (after : Option Nat) (limit : Nat) : List (List Row) :=
  let tail := remaining rows after
  if tail.isEmpty then [[]] else chunks limit tail.length tail

theorem walk_covers_exact_suffix (rows : List Row) (after : Option Nat) (limit : Nat)
    (positive : 0 < limit) :
    (walk rows after limit).flatten = remaining rows after := by
  unfold walk
  generalize remaining rows after = tail
  cases tail with
  | nil => rfl
  | cons row tail =>
    change (chunks limit (row :: tail).length (row :: tail)).flatten = row :: tail
    exact chunks_cover limit _ _ positive (Nat.le_refl _)

-- Typed version binding; no claim about the choice or implementation of a hash.
def resumeWalk (expected current : List Row) (after : Option Nat) (limit : Nat) :
    Option (List (List Row)) :=
  if expected = current then some (walk current after limit) else none

theorem resume_walk_rejects_changed {expected current : List Row}
    (changed : expected ≠ current) (after : Option Nat) (limit : Nat) :
    resumeWalk expected current after limit = none := by
  simp [resumeWalk, changed]

theorem resume_walk_covers_unchanged (rows : List Row) (after : Option Nat) (limit : Nat)
    (positive : 0 < limit) :
    (resumeWalk rows rows after limit).map List.flatten = some (remaining rows after) := by
  simp [resumeWalk, walk_covers_exact_suffix rows after limit positive]

def emit (rows : List Row) (cases : List (Option Nat × Nat)) : IO Unit :=
  for (after, limit) in cases do
    IO.println ("walk|" ++
      String.intercalate ";" ((walk rows after limit).map (fun part => String.intercalate "," (part.map rowWire))))

end CheckpointWalk

import Std

namespace CheckpointPage

structure Row where
  key : Nat
  revision : Nat
  deleted : Bool
  deriving DecidableEq, Repr

def remaining (rows : List Row) (after : Option Nat) : List Row :=
  match after with
  | none => rows
  | some key => rows.filter (fun row => decide (key < row.key))

def page (rows : List Row) (after : Option Nat) (limit : Nat) : List Row :=
  (remaining rows after).take limit

-- Equality here is exact typed identity, not a claim about hash functions.
def resume (expected current : List Row) (after limit : Nat) : Option (List Row) :=
  if expected = current then some (page current (some after) limit) else none

theorem resume_rejects_changed {expected current : List Row}
    (different : expected ≠ current) (after limit : Nat) :
    resume expected current after limit = none := by
  simp [resume, different]

theorem resume_accepts_exact (rows : List Row) (after limit : Nat) :
    resume rows rows after limit = some (page rows (some after) limit) := by
  simp [resume]

theorem before_boundary_filtered (rows : List Row) (cut : Nat)
    (before : ∀ r ∈ rows, r.key ≤ cut) :
    remaining rows (some cut) = [] := by
  induction rows with
  | nil => rfl
  | cons row tail ih =>
    have h : ¬ cut < row.key := Nat.not_lt_of_ge (before row (by simp))
    have htail := ih (fun r hr => before r (by simp [hr]))
    simpa [remaining, h] using htail

theorem after_boundary_preserved (rows : List Row) (cut : Nat)
    (after : ∀ r ∈ rows, cut < r.key) :
    remaining rows (some cut) = rows := by
  induction rows with
  | nil => rfl
  | cons row tail ih =>
    have h := after row (by simp)
    have htail := ih (fun r hr => after r (by simp [hr]))
    simp only [remaining] at htail
    simp [remaining, h, htail]

theorem exact_remaining (earlier suffix : List Row) (cut : Nat)
    (before : ∀ r ∈ earlier, r.key ≤ cut) (after : ∀ r ∈ suffix, cut < r.key) :
    remaining (earlier ++ suffix) (some cut) = suffix := by
  have h1 := before_boundary_filtered earlier cut before
  have h2 := after_boundary_preserved suffix cut after
  simp only [remaining] at h1 h2 ⊢
  rw [List.filter_append, h1, h2, List.nil_append]

theorem stable_next_page (earlier suffix : List Row) (cut limit : Nat)
    (before : ∀ r ∈ earlier, r.key ≤ cut) (after : ∀ r ∈ suffix, cut < r.key) :
    resume (earlier ++ suffix) (earlier ++ suffix) cut limit = some (suffix.take limit) := by
  rw [resume_accepts_exact, page, exact_remaining earlier suffix cut before after]

theorem sorted_boundary_page (earlier later : List Row) (boundary : Row) (limit : Nat)
    (sorted : (earlier ++ boundary :: later).Pairwise (fun a b => a.key < b.key)) :
    resume (earlier ++ boundary :: later) (earlier ++ boundary :: later) boundary.key limit =
      some (later.take limit) := by
  have parts := List.pairwise_append.mp sorted
  have before : ∀ r ∈ earlier ++ [boundary], r.key ≤ boundary.key := by
    intro r hr
    rcases List.mem_append.mp hr with hm | hm
    · exact Nat.le_of_lt (parts.2.2 r hm boundary (List.mem_cons_self))
    · have eq : r = boundary := List.mem_singleton.mp hm
      subst r
      exact Nat.le_refl _
  have after : ∀ r ∈ later, boundary.key < r.key :=
    (List.pairwise_cons.mp parts.2.1).1
  simpa only [List.append_assoc, List.singleton_append] using
    stable_next_page (earlier ++ [boundary]) later boundary.key limit before after

def rowWire (row : Row) : String :=
  toString row.key ++ ":" ++ toString row.revision ++ ":" ++ (if row.deleted then "D" else "U")

def emit (rows : List Row) (cases : List (Option Nat × Nat)) : IO Unit :=
  for (after, limit) in cases do
    IO.println ("page|" ++ String.intercalate "," ((page rows after limit).map rowWire))

end CheckpointPage

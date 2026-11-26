import CheckpointWalk

namespace CheckpointHandoff

open CheckpointPage CheckpointWalk

private theorem remaining_after_sorted_boundary (previous later : List Row) (boundary : Row)
    (sorted : (previous ++ boundary :: later).Pairwise (fun a b => a.key < b.key)) :
    remaining (previous ++ boundary :: later) (some boundary.key) = later := by
  have parts := List.pairwise_append.mp sorted
  have before : ∀ r ∈ previous ++ [boundary], r.key ≤ boundary.key := by
    intro r hr
    rcases List.mem_append.mp hr with hm | hm
    · exact Nat.le_of_lt (parts.2.2 r hm boundary List.mem_cons_self)
    · rw [List.mem_singleton.mp hm]
      exact Nat.le_refl _
  have after : ∀ r ∈ later, boundary.key < r.key :=
    (List.pairwise_cons.mp parts.2.1).1
  simpa only [List.append_assoc, List.singleton_append] using
    exact_remaining (previous ++ [boundary]) later boundary.key before after

theorem exact_handoff_joins_prefix (previous later : List Row) (boundary : Row) (limit : Nat)
    (sorted : (previous ++ boundary :: later).Pairwise (fun a b => a.key < b.key))
    (positive : 0 < limit) :
    (previous ++ [boundary]) ++ (walk (previous ++ boundary :: later) (some boundary.key) limit).flatten =
      previous ++ boundary :: later := by
  rw [walk_covers_exact_suffix _ _ _ positive, remaining_after_sorted_boundary _ _ _ sorted]
  simp only [List.append_assoc, List.singleton_append]

theorem earlier_adjacent_boundary_replays (prior later : List Row) (earlier intended : Row) (limit : Nat)
    (sorted : (prior ++ earlier :: intended :: later).Pairwise (fun a b => a.key < b.key))
    (positive : 0 < limit) :
    (walk (prior ++ earlier :: intended :: later) (some earlier.key) limit).flatten =
      intended :: later := by
  rw [walk_covers_exact_suffix _ _ _ positive]
  exact remaining_after_sorted_boundary prior (intended :: later) earlier sorted

end CheckpointHandoff

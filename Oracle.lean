import Reservation

/-- Protocol: one decimal triple per line; one decimal result or "reject" per line. -/
def main : IO Unit := do
  let input ← IO.getStdin
  let output ← IO.getStdout
  repeat
    let line ← input.getLine
    if line.isEmpty then break
    match line.trim.splitOn " " with
    | [c, u, r] =>
      match c.toNat?, u.toNat?, r.toNat? with
      | some capacity, some used, some request =>
        match Reservation.reserve capacity used request with
        | some next => output.putStrLn (toString next)
        | none => output.putStrLn "reject"
      | _, _, _ => throw (IO.userError "expected unsigned decimal integers")
    | _ => throw (IO.userError "expected: capacity used request")

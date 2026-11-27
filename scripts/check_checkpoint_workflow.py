"""Opt-in three-layer local replay against synthetic checkpoint rows, without model calls."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples" / "checkpoint_page"
OPS = {"read", "compare", "receipt"}
NAME = re.compile(r"[a-z][a-z0-9-]{0,23}")
CLAIMS = {"compare_requires_python", "receipt_requires_comparison"}
AXIOMS = {"propext", "Classical.choice", "Quot.sound"}
ROWS = [
    ["0", "0", "U"],
    [str(2**53 + 1), str(2**53 - 1), "D"],
    [str(2**64 + 1), str(2**64 - 1), "U"],
    [str(10**127), str(10**127 + 1), "D"],
    [str(10**127 + 1), str(2**64 + 2), "U"],
]
PAGE_SIZE = 2


class Rejected(Exception):
    def __init__(self, layer, step, predicate):
        self.diagnostic = {"layer": layer, "step": step, "predicate": predicate}
        super().__init__(self.diagnostic)


def require(condition, layer, step, predicate):
    if not condition:
        raise Rejected(layer, step, predicate)


def make_plan(order):
    return {"entry": order[0], "nodes": [
        {"id": op, "op": op, "next": order[i+1] if i+1 < len(order) else None}
        for i,op in enumerate(order)
    ]}


def check_graph(plan):
    require(type(plan) is dict and plan.keys() == {"entry","nodes"}, "L1","graph","workflow-shape")
    nodes = plan["nodes"]
    require(type(nodes) is list and len(nodes) == 3, "L1","graph","three-stage-slice")
    by_id, operations = {}, set()
    for node in nodes:
        require(type(node) is dict and node.keys() == {"id","op","next"}, "L1","graph","node-shape")
        name, op, nxt = node["id"],node["op"],node["next"]
        require(type(name) is str and NAME.fullmatch(name) and name not in by_id,
                "L1","graph","unique-node-identities")
        require(type(op) is str and op in OPS and op not in operations, "L1",name,"unique-known-operation")
        require(nxt is None or (type(nxt) is str and NAME.fullmatch(nxt)), "L1",name,"transition-shape")
        by_id[name] = node
        operations.add(op)
    name = plan["entry"]
    require(type(name) is str and name in by_id, "L1","graph","known-entry")
    for item,node in by_id.items():
        require(node["next"] is None or node["next"] in by_id, "L1",item,"known-next-node")
    ordered, visited = [], set()
    while name is not None:
        require(name not in visited, "L1",name,"acyclic-path")
        visited.add(name)
        ordered.append(by_id[name])
        name = by_id[name]["next"]
    require(len(visited) == len(by_id), "L1","graph","all-nodes-reachable")
    return ordered


def checked_lean(lean, ordered, cwd):
    """Check declared postconditions before performing any CLI operation."""
    src = (ROOT/"CheckpointWorkflow.lean").read_text()
    body = src + "".join(f"\n#print axioms CheckpointWorkflow.{claim}" for claim in sorted(CLAIMS))
    body += "\n#eval CheckpointWorkflow.report [" + ",".join("."+node["op"] for node in ordered) + "]\n"
    p = subprocess.run([lean,"-DwarningAsError=true","--stdin"],cwd=cwd,input=body,
                       capture_output=True,text=True,timeout=20)
    if p.returncode or p.stderr:
        raise RuntimeError("pinned Lean execution failed:\n"+p.stdout+p.stderr)
    audited, result = {}, None
    for line in p.stdout.splitlines():
        if line.startswith("plan|"):
            if result is not None:
                raise RuntimeError("multiple Lean outcomes")
            result = line.split("|")[1:]
            continue
        m = re.fullmatch(r"'CheckpointWorkflow\.(\w+)' (?:depends on axioms: \[([^\]]+)\]|does not depend on any axioms)",line)
        if not m or m[1] in audited:
            raise RuntimeError("unexpected Lean axiom report")
        audited[m[1]] = [] if m[2] is None else m[2].split(", ")
        if set(audited[m[1]])-AXIOMS:
            raise RuntimeError("unexpected axioms")
    if audited.keys() != CLAIMS or result is None:
        raise RuntimeError("incomplete formal result")
    if result != ["pass"]:
        if (len(result) != 2 or not result[0].isdigit() or int(result[0]) >= len(ordered)
                or result[1] not in {"python-observation-declared","comparison-declared"}):
            raise RuntimeError("malformed semantic diagnosis")
        node = ordered[int(result[0])]["id"]
        raise Rejected("L2",node,result[1])
    return audited


def raw(rows):
    return "".join(json.dumps(row,separators=(",",":"))+"\n" for row in rows).encode("ascii")


def run_reader(reader, node, path, page_size, attempts):
    if reader == "python":
        args = [sys.executable,"-B",str(EXAMPLES/"page.py")]
    else:
        args = [os.environ.get("NODE","node"),str(EXAMPLES/"page.ts")]
    attempts.append(reader)
    try:
        p = subprocess.run([*args,str(path),"--walk"],input=json.dumps([None,str(page_size)]),
                           text=True,capture_output=True,timeout=15)
    except (OSError,subprocess.TimeoutExpired):
        raise Rejected("L3",node,"reader-completed") from None
    require(p.returncode == 0 and not p.stderr,"L3",node,"reader-completed")
    try:
        return json.loads(p.stdout)
    except ValueError:
        raise Rejected("L3",node,"valid-reader-json") from None


def check_observation(node, output, digest, pages):
    require(type(output) is list and len(output) == 3 and output[0] == "ok",
            "L3",node,"accepted-reader-result")
    require(output[1] == digest,"L3",node,"same-snapshot-digest")
    require(output[2] == pages,"L3",node,"exact-rows-and-page-boundaries")


def execute(plan, lean, folder, control=None):
    layers, attempts, receipt = [], [], None
    try:
        ordered = check_graph(plan)
        layers.append("L1")
        axioms = checked_lean(lean,ordered,folder)
        layers.append("L2")
        snapshot = folder/"snapshot.jsonl"
        data = raw(ROWS)
        digest = hashlib.sha256(data).hexdigest()
        snapshot.write_bytes(data)
        # Independent positional oracle for the fixed, declared sorted fixture.
        pages = [[ROWS[i:i+PAGE_SIZE],ROWS[i+PAGE_SIZE-1][0] if i+PAGE_SIZE<len(ROWS) else None]
                 for i in range(0,len(ROWS),PAGE_SIZE)]
        observed = None
        paired = False
        for node in ordered:
            name = node["id"]
            if node["op"] == "read":
                observed = run_reader("python",name,snapshot,PAGE_SIZE,attempts)
                check_observation(name,observed,digest,pages)
            elif node["op"] == "compare":
                require(observed is not None,"L3",name,"python-observation-established")
                target, size = snapshot, PAGE_SIZE
                # Each control invokes the real TypeScript CLI with a different
                # benign fixture or valid page width. No fake tool results.
                if control == "different-snapshot":
                    changed = [row[:] for row in ROWS]
                    changed[-1][1] = "123"
                    target = folder/"different.jsonl"
                    target.write_bytes(raw(changed))
                if control == "different-width":
                    size = PAGE_SIZE+1
                result = run_reader("typescript",name,target,size,attempts)
                check_observation(name,result,digest,pages)
                require(result == observed,"L3",name,"cross-runtime-agreement")
                paired = True
            else:
                require(paired,"L3",name,"comparison-established")
                receipt = {"snapshot_sha256":digest,"rows":len(ROWS),"pages":len(pages),
                           "readers":attempts[:]}
        if receipt is None:
            raise RuntimeError("workflow terminated without the required local receipt")
        layers.append("L3")
        outcome = {"status":"ok","passed_layers":layers,"reader_invocations":attempts,
                   "receipt":receipt,"model_claim_axioms":axioms}
    except Rejected as exc:
        if receipt is not None:
            raise RuntimeError("a rejected run reached the receipt step") from exc
        outcome = {"status":"rejected","passed_layers":layers,"reader_invocations":attempts,
                   "receipt":None,**exc.diagnostic}
    return outcome


def main():
    if not __debug__ or sys.argv[1:]:
        raise SystemExit("usage: LEAN=/path/to/lean python3 -B scripts/check_checkpoint_workflow.py")
    lean = os.environ.get("LEAN","lean")
    # Resolve a user-supplied relative executable before subprocesses change cwd.
    if os.sep in lean or (os.altsep and os.altsep in lean):
        lean = str(Path(lean).resolve())
    toolchain = subprocess.check_output([lean,"--version"],text=True).strip()
    if "version 4.19.0," not in toolchain:
        raise SystemExit("this experiment requires Lean 4.19.0")
    reference_plan = make_plan(["read","compare","receipt"])
    malformed = make_plan(["read","compare","receipt"])
    malformed["nodes"][0]["next"] = "unknown-target"
    cases = [
        ("reference", reference_plan, None, None),
        ("unknown-transition", malformed, None, ("L1","read","known-next-node")),
        ("compare-before-read", make_plan(["compare","read","receipt"]), None, ("L2","compare","python-observation-declared")),
        ("receipt-before-compare", make_plan(["read","receipt","compare"]), None, ("L2","receipt","comparison-declared")),
        ("different-snapshot", reference_plan, "different-snapshot", ("L3","compare","same-snapshot-digest")),
        ("different-page-width", reference_plan, "different-width", ("L3","compare","exact-rows-and-page-boundaries")),
    ]
    records = {}
    with tempfile.TemporaryDirectory(prefix="checkpoint-workflow-") as directory:
        for i,(name,plan,control,diagnosis) in enumerate(cases):
            folder = Path(directory)/str(i)
            folder.mkdir()
            result = execute(plan,lean,folder,control)
            if diagnosis is None:
                assert result["status"] == "ok" and result["passed_layers"] == ["L1","L2","L3"], result
                assert result["receipt"] and result["reader_invocations"] == ["python","typescript"]
            else:
                assert result["status"] == "rejected" and result["receipt"] is None, result
                assert tuple(result[k] for k in ("layer","step","predicate")) == diagnosis, result
                assert result["reader_invocations"] == (
                    ["python","typescript"] if diagnosis[0] == "L3" else []
                ), result
            records[name] = result
    print(json.dumps({"case":"checkpoint-workflow-v1","lean":toolchain,
                      "python":sys.version.split()[0],
                      "node":subprocess.check_output([os.environ.get("NODE","node"),"--version"],text=True).strip(),
                      "cases":records},indent=2,sort_keys=True))


if __name__ == "__main__":
    main()

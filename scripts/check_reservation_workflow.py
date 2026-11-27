"""Optional Lean4Agent-style proof and replay on Python, TypeScript, and checked Rust."""
import argparse
import hashlib
import itertools
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "reservation"
SOURCE = EXAMPLE / "reserve.rs"
MAX = 2**64 - 1
CLAIMS = {"width_guard_preserves_bounded_reservation", "receipt_requires_all_runtimes"}
AXIOMS = {"propext","Classical.choice","Quot.sound"}
ORDER = ["oracle","python","typescript","rust","receipt"]
LANGUAGES = ORDER[1:-1]
CASES = list(dict.fromkeys([(10,7,3),(MAX,MAX,1)] + list(itertools.product(range(5), repeat=3)) + [
    (2**53 + 1,2**53,1), (2**53 + 1,2**53,2), (2**63,2**63-1,1),
    (2**63,2**63,1), (MAX,MAX-1,1), (MAX,MAX-1,2), (MAX,0,MAX),
    (MAX,MAX,0), (MAX,1,MAX), (MAX-1,MAX,0), (MAX,MAX,MAX),
    (0,MAX,1), (0,0,MAX), (MAX,MAX//2,MAX//2+1),
]))
WIRE = "".join(f"{a} {u} {r}\n" for a,u,r in CASES)
VARIANTS = {"checked", "strict", "wrap"}
CAPTURE_V1 = "reservation-rust-std-capture-v1"
CAPTURE_V2 = "reservation-rust-std-capture-v2"
CAPTURE_BYTES = "staged-source-bytes-and-exact-utf8-stdin"
LEGACY_BYTES = "legacy-canonical-hashes-not-transport-attestation"
PYTHON_ADAPTER = """import sys
sys.path.insert(0,sys.argv[1])
from reserve import reserve
for line in sys.stdin:
    result = reserve(*map(int,line.split()))
    print('reject' if result is None else result)
"""


def sha(data):
    return hashlib.sha256(data).hexdigest()


def call(command, wire=None, cwd=None, env=None):
    # The SHA covers these bytes, not a host-specific translation of LF.
    data = wire.encode("utf-8") if isinstance(wire, str) else wire
    p = subprocess.run(command,input=data,capture_output=True,timeout=30,cwd=cwd,env=env)
    if p.returncode or p.stderr:
        detail = (p.stdout+p.stderr).decode("utf-8",errors="replace")
        raise RuntimeError(f"{Path(command[0]).name} failed (exit {p.returncode}): {detail}")
    # For report strings only; this does not affect or describe bytes on stdin.
    return p.stdout.decode("utf-8").replace("\r\n","\n")


def require(condition, reason):
    if not condition:
        raise RuntimeError(reason)


def structure(plan):
    # This opt-in slice has one linear path, so finite membership and uniqueness
    # suffice for its L1 shape. Ordering of preconditions is checked separately.
    if type(plan) is not list or len(plan) != len(ORDER) or set(plan) != set(ORDER):
        return {"layer":"L1","step":"plan","predicate":"unique-required-stages"}
    return None


def checked_lean(lean, plans, tmp):
    toolchain = call([lean,"--version"]).strip()
    require("version 4.19.0," in toolchain,"expected Lean 4.19.0")
    env = {**os.environ,"LEAN_PATH":str(tmp)}
    (tmp / "Reservation.lean").write_bytes((ROOT / "Reservation.lean").read_bytes())
    require(not call([lean,"-DwarningAsError=true","-o","Reservation.olean","Reservation.lean"],cwd=tmp,env=env),
            "unexpected Reservation module output")
    # Lean source contains Unicode syntax; do not use the host locale here.
    code = (ROOT / "ReservationWorkflow.lean").read_text(encoding="utf-8")
    code += "".join(f"\n#print axioms ReservationWorkflow.{claim}" for claim in sorted(CLAIMS))
    code += "".join("\n#eval ReservationWorkflow.report ["+",".join("."+s for s in plan)+"]" for plan in plans)
    code += "\n#eval ReservationWorkflow.emit ["+",".join(f"({a},{u},{r})" for a,u,r in CASES)+"]\n"
    observed = call([lean,"-DwarningAsError=true","--stdin"],code,tmp,env).splitlines()
    audit, static, values = {}, [], []
    for line in observed:
        if line.startswith("plan|"):
            static.append(line.split("|")[1:])
        elif line.startswith("value|"):
            values.append(line.removeprefix("value|"))
        else:
            m = re.fullmatch(r"'ReservationWorkflow\.(\w+)' (?:depends on axioms: \[([^\]]+)\]|does not depend on any axioms)",line)
            require(m is not None and m[1] not in audit,"unexpected Lean axiom report")
            audit[m[1]] = [] if m[2] is None else m[2].split(", ")
            require(set(audit[m[1]]) <= AXIOMS,"unexpected Lean axiom")
    require(audit.keys()==CLAIMS and len(static)==len(plans),"incomplete Lean check")
    return toolchain,audit,static,values


def rust_source_hashes(*, legacy=False):
    original = SOURCE.read_bytes()
    body = original.replace(b"\r\n",b"\n").replace(b"\r",b"\n") if legacy else original
    require(body.count(b"next <= capacity")==1 and body.count(b"used.checked_add(request)")==1,
            "Rust source no longer matches deliberate controls")
    texts = {"checked":body, "strict":body.replace(b"next <= capacity",b"next < capacity"),
             "wrap":body.replace(b"used.checked_add(request)",b"Some(used.wrapping_add(request))")}
    return original,texts,{k:sha(v) for k,v in texts.items()}


def rust_capture(rust, tmp):
    version = call([rust,"-vV"]).strip()
    original,texts,variants = rust_source_hashes()
    transcripts = {}
    for label,body in texts.items():
        source = tmp / (label+".rs")
        binary = tmp / (label + (".exe" if os.name == "nt" else ""))
        source.write_bytes(body)
        call([rust,"--edition=2021","-Dwarnings","-C","overflow-checks=yes",
              str(source),"-o",str(binary)])
        transcripts[label] = call([str(binary)],WIRE).splitlines()
        if label=="checked":
            too_wide = subprocess.run([str(binary)],input=f"{MAX+1} 0 0\n".encode("ascii"),
                                      capture_output=True,timeout=10)
            refused = (too_wide.returncode != 0 and not too_wide.stdout
                       and b"expected three unsigned u64 decimals" in too_wide.stderr)
            require(refused,"Rust did not reject input outside the declared wire domain")
    return {"format":CAPTURE_V2,"byte_transport":CAPTURE_BYTES,"compiler":version,
            "source_sha256":sha(original),"wire_sha256":sha(WIRE.encode("ascii")),
            "variant_sha256":variants,"out_of_domain_refused":refused,"results":transcripts}


def check_capture(data):
    require(type(data) is dict and data.get("format") in (CAPTURE_V1,CAPTURE_V2),
            "unexpected Rust capture format")
    legacy = data["format"]==CAPTURE_V1
    fields = {"format","compiler","source_sha256","wire_sha256",
              "variant_sha256","out_of_domain_refused","results"}
    if not legacy:
        fields.add("byte_transport")
        require(data.get("byte_transport")==CAPTURE_BYTES,"unexpected Rust byte transport declaration")
    require(data.keys()==fields,"unexpected Rust capture shape")
    original,_,expected_variants = rust_source_hashes(legacy=legacy)
    require(
            type(data["compiler"]) is str and data["compiler"].startswith("rustc ") and
            "\nhost:" in data["compiler"] and data["source_sha256"]==sha(original) and
            data["wire_sha256"]==sha(WIRE.encode("ascii")) and
            data["variant_sha256"]==expected_variants and data["out_of_domain_refused"] is True and
            type(data["results"]) is dict and data["results"].keys()==VARIANTS,
            "Rust capture did not bind to source, fixture and controls")
    for values in data["results"].values():
        require(type(values) is list and len(values)==len(CASES) and
                all(type(x) is str and (x=="reject" or
                    (re.fullmatch(r"0|[1-9][0-9]{0,19}",x) and int(x)<=MAX)) for x in values),
                "invalid Rust capture output")
    return data


def unique_json_object(pairs):
    result = {}
    for name,value in pairs:
        require(name not in result,"duplicate JSON object field in Rust capture")
        result[name] = value
    return result


def reject_json_constant(_value):
    raise RuntimeError("nonstandard JSON constant in Rust capture")


def load_capture(path, expected_sha256=None):
    # Read once: compare the exact delivered bytes, then parse that same byte string.
    raw = path.read_bytes()
    digest = sha(raw)
    require(expected_sha256 is None or digest==expected_sha256,
            "Rust capture SHA-256 does not match expected bytes")
    require(not raw.startswith(b"\xef\xbb\xbf"),"Rust capture must be UTF-8 without a BOM")
    try:
        data = json.loads(raw.decode("utf-8"),object_pairs_hook=unique_json_object,
                          parse_constant=reject_json_constant)
    except (UnicodeDecodeError,json.JSONDecodeError) as error:
        raise RuntimeError("Rust capture must be a valid UTF-8 JSON document") from error
    return check_capture(data),digest


def compare(language, expected, rows):
    if len(rows) != len(expected):
        return {"layer":"L3","step":language,"predicate":"case-count",
                "actual_count":len(rows),"expected_count":len(expected),"receipt":None}
    for i,(want,got) in enumerate(zip(expected,rows)):
        if want != got:
            return {"layer":"L3","step":language,"predicate":"runtime-equals-oracle",
                    "tuple":[str(x) for x in CASES[i]],"expected":want,"actual":got,"receipt":None}
    return None


def available(executable):
    found = shutil.which(executable)
    # Preserve argv[0] for rustup and elan proxy symlinks.
    return str(Path(found).absolute()) if found else None


def report_file(document):
    print(json.dumps(document,indent=2,sort_keys=True))


def main():
    p = argparse.ArgumentParser(description=__doc__, epilog=
        "Exit 0: native success (or Rust-only capture). Exit 2: missing Rust/compiler or CLI input. "
        "Exit 3: explicit split-host comparison only, with no live three-language receipt. "
        "Other failures exit 1.")
    modes = p.add_mutually_exclusive_group()
    modes.add_argument("--capture-rust",action="store_true",help="execute only native Rust and emit a capture on stdout")
    modes.add_argument("--rust-evidence",type=Path,help="explicitly compare a trusted capture; no native Rust receipt for this run")
    p.add_argument("--rust-evidence-sha256", metavar="HEX",
                   help="optional expected SHA-256 of the exact imported file bytes; not host authentication")
    args = p.parse_args()
    pin = args.rust_evidence_sha256
    if pin is not None and (args.rust_evidence is None or not re.fullmatch(r"[0-9a-fA-F]{64}",pin)):
        p.error("--rust-evidence-sha256 requires --rust-evidence and a 64-digit hexadecimal SHA-256")
    imported = None
    if args.rust_evidence is not None:
        try:
            imported = load_capture(args.rust_evidence,None if pin is None else pin.lower())
        except (OSError,RuntimeError) as error:
            p.exit(1,f"Rust evidence refused: {error}\n")
    require(all(0<=x<=MAX for t in CASES for x in t),"fixture outside u64 domain")
    rust = available(os.environ.get("RUSTC","rustc"))
    if args.capture_rust:
        if rust is None:
            p.exit(2,"Rust compiler unavailable\n")
        with tempfile.TemporaryDirectory(prefix="reservation-rust-") as name:
            report_file(check_capture(rust_capture(rust,Path(name))))
        return
    lean = available(os.environ.get("LEAN","lean"))
    node = available(os.environ.get("NODE","node"))
    require(lean and node,"Lean 4.19.0 and Node.js 24+ are required")
    # Independent reference uses remaining capacity; Lean uses a natural sum.
    expected = [str(u+r) if u<=a and r<=a-u else "reject" for a,u,r in CASES]
    bad_shape = structure(["oracle","python","typescript","python","receipt"])
    require(bad_shape == {"layer":"L1","step":"plan","predicate":"unique-required-stages"},
            "invalid plan did not fail structurally")
    early_receipt = ["oracle","python","typescript","receipt","rust"]
    require(structure(ORDER) is None and structure(early_receipt) is None,
            "both complete linear plans should pass only the structural check")
    with tempfile.TemporaryDirectory(prefix="reservation-workflow-") as name:
        tmp = Path(name)
        toolchain,audit,static,typed = checked_lean(lean,[ORDER,early_receipt],tmp)
        require(static==[["pass"],["3","all-three-results-declared"]],"unexpected static readback")
        require(compare("lean",expected,typed) is None,"Lean and independent oracle disagree")

        py = call([sys.executable,"-B","-c",PYTHON_ADAPTER,str(EXAMPLE)],WIRE).splitlines()
        ts = call([node,str(EXAMPLE/"reserve.ts")],WIRE).splitlines()
        for language,rows in (("python",py),("typescript",ts)):
            failure = compare(language,typed,rows)
            if failure:
                report_file(failure)
                return 1
        summary = {
            "experiment":"reservation-workflow-u64-v1","cases":len(CASES),
            "toolchain":toolchain,"proof_axioms":audit,"passed_layers":["L1","L2"],
            "python":sys.version.split()[0],"node":call([node,"--version"]).strip(),
            "live_matched":{"python":len(CASES),"typescript":len(CASES)},
            "receipt":None,"split_host_comparison":None,
            "controls":{"structure":bad_shape,
                        "early_receipt":{"layer":"L2","step":"receipt","predicate":"all-three-results-declared"}},
        }
        if args.rust_evidence is None and rust is None:
            summary.update({"status":"blocked","layer":"L3","step":"rust","predicate":"rustc-unavailable"})
            report_file(summary)
            return 2
        if imported is not None:
            capture, capture_sha256 = imported
        else:
            capture = check_capture(rust_capture(rust,tmp))
        for variant in ("strict","wrap"):
            error = compare("rust",typed,capture["results"][variant])
            require(error is not None,"Rust negative control survived")
            witness = (["10","7","3"],"10","reject") if variant=="strict" else (
                [str(MAX),str(MAX),"1"],"reject","0")
            require((error["tuple"],error["expected"],error["actual"])==witness,"wrong negative-control witness")
            summary["controls"][variant]=error
        failure = compare("rust",typed,capture["results"]["checked"])
        if failure:
            report_file(failure)
            return 1
        summary["rust"] = {k:capture[k] for k in ("compiler","source_sha256","wire_sha256","out_of_domain_refused")}
        summary["rust"]["in_domain_addition_overflow_cases_rejected"] = sum(u+r>MAX for _,u,r in CASES)
        summary["rust"]["capture_format"] = capture["format"]
        summary["rust"]["byte_transport"] = capture.get("byte_transport",LEGACY_BYTES)
        if args.rust_evidence is None:
            summary["live_matched"]["rust"] = len(CASES)
            summary.update({"status":"ok","passed_layers":["L1","L2","L3"],
                            "receipt":{"source":"same-host live execution","runtimes":LANGUAGES}})
        else:
            summary.update({"status":"split-host-results-match",
                            "split_host_comparison":{"rust_matched_cases":len(CASES),
                                "capture_sha256":capture_sha256,
                                "expected_sha256_matched":None if pin is None else True,
                                "not_live_here":True,"capture_authentication":"not provided by hashes"}})
        report_file(summary)
    return 3 if args.rust_evidence is not None else 0


if __name__ == "__main__":
    sys.exit(main())

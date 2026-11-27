"""Opt-in persisted receipt import check; synthetic manifests are not native Rust runs."""
import base64
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

import check_reservation_workflow as h


def file_sha(data):
    return hashlib.new("sha256", data).hexdigest()


def synthetic_envelope():
    source, _, variants = h.rust_source_hashes()
    return {
        "format":h.CAPTURE_V2,
        "byte_transport":h.CAPTURE_BYTES,
        "compiler":"rustc synthetic-import-test\nhost: synthetic",
        "source_sha256":file_sha(source),
        "wire_sha256":file_sha(h.WIRE.encode("ascii")),
        "variant_sha256":variants,
        "out_of_domain_refused":True,
        "results":{label:["reject"]*len(h.CASES) for label in sorted(h.VARIANTS)},
    }


def zip_roundtrip(data):
    mem = io.BytesIO()
    with zipfile.ZipFile(mem,"w",compression=zipfile.ZIP_DEFLATED) as out:
        out.writestr("capture.json",data)
    with zipfile.ZipFile(io.BytesIO(mem.getvalue())) as received:
        return received.read("capture.json")


def refused(path, pin, message):
    cli = h.ROOT/"scripts"/"check_reservation_workflow.py"
    opts = ["--rust-evidence",str(path)]
    if pin is not None:
        opts += ["--rust-evidence-sha256",pin]
    # A refused import should not even probe the external tools. The real
    # entry point checks its evidence before an expensive Lean replay.
    env = {**os.environ,"LEAN":"/nonexistent-lean","NODE":"/nonexistent-node","RUSTC":"/nonexistent-rustc"}
    proc = subprocess.run([sys.executable,"-B",str(cli),*opts],env=env,
                          capture_output=True,timeout=10)
    assert proc.returncode==1 and not proc.stdout, (proc.returncode,proc.stdout,proc.stderr)
    assert proc.stderr.decode().strip()=="Rust evidence refused: "+message, proc.stderr


def main():
    if not __debug__:
        raise SystemExit("run without Python optimization")
    manifest = synthetic_envelope()
    original = (json.dumps(manifest,indent=2,sort_keys=True)+"\n").encode("utf-8")
    pinned = file_sha(original)
    results = {"raw":original,"zip-deflate":zip_roundtrip(original),
               "base64":base64.b64decode(base64.b64encode(original),validate=True)}
    rewritten = {"crlf":original.replace(b"\n",b"\r\n"),
                 "compact":json.dumps(manifest,separators=(",",":")).encode()}
    malformed = {
        "top-level-duplicate": (b'{"format":"discarded",'+original[1:],
            "duplicate JSON object field in Rust capture"),
        "escaped-top-level-duplicate": (b'{"\\u0066ormat":"discarded",'+original[1:],
            "duplicate JSON object field in Rust capture"),
        "nested-duplicate": (original.replace(b'"results": {',b'"results": {"checked": [],',1),
            "duplicate JSON object field in Rust capture"),
        "utf8-bom": (b'\xef\xbb\xbf'+original,
            "Rust capture must be UTF-8 without a BOM"),
        "utf16": (original.decode().encode("utf-16"),
            "Rust capture must be a valid UTF-8 JSON document"),
        "nonstandard-constant": (b'{"_unused":NaN,'+original[1:],
            "nonstandard JSON constant in Rust capture"),
    }
    with tempfile.TemporaryDirectory(prefix="reservation-capture-import-") as d:
        target = Path(d)/"delivered-capture.json"
        for data in results.values():
            target.write_bytes(data)
            assert data==original and h.load_capture(target,pinned)==(manifest,pinned)
        for data in rewritten.values():
            target.write_bytes(data)
            assert file_sha(data)!=pinned
            assert h.load_capture(target)==(manifest,file_sha(data))
            refused(target,pinned,"Rust capture SHA-256 does not match expected bytes")
        for data,error in malformed.values():
            target.write_bytes(data)
            # Even the correct digest of ambiguous bytes can't make the import valid.
            refused(target,file_sha(data),error)
    print(json.dumps({
        "case":"reservation-capture-file-import-v2",
        "exact-byte-roundtrips":sorted(results),
        "equivalent-unpinned-only":{k:file_sha(v) for k,v in rewritten.items()},
        "malformed-refused-at-real-cli":sorted(malformed),
        "rewritten-refused-at-real-cli":sorted(rewritten),
        "native-rust-runs":0,
        "positive-capture-provenance":"synthetic manifest; parser validation only",
        "rust-capture-authenticated":False,
        "synthetic-file-sha256":pinned,
    },indent=2,sort_keys=True))


if __name__=="__main__":
    main()

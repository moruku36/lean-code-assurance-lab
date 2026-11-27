"""Opt-in raw source/pipe byte checks; no compiler or remote observation is simulated as live."""
from copy import deepcopy
import io
import json
import os
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

import check_reservation_workflow as h

PY_ECHO = "import hashlib,sys; print(hashlib.sha256(sys.stdin.buffer.read()).hexdigest())"
NODE_ECHO = "process.stdout.write(require('node:crypto').createHash('sha256').update(require('node:fs').readFileSync(0)).digest('hex'))"
SAMPLE = "17 8 9\n19 1 17\n23 15 11\n"


def refused(change, why):
    try:
        h.check_capture(change)
    except RuntimeError as error:
        if why not in str(error):
            raise
    else:
        raise AssertionError("binding control was not refused")


def main():
    if not __debug__:
        raise SystemExit("run without Python optimization")
    node = h.available(os.environ.get("NODE","node"))
    if node is None:
        raise SystemExit("Node.js is required for this opt-in check")
    endings = {"lf":SAMPLE,"crlf":SAMPLE.replace("\n","\r\n"),"mixed":SAMPLE.replace("\n","\r\n",1)}
    got = {}
    for name,data in endings.items():
        raw = data.encode("ascii")
        expected = h.sha(raw)
        assert h.call([sys.executable,"-B","-c",PY_ECHO],data).strip()==expected
        assert h.call([node,"-e",NODE_ECHO],raw).strip()==expected
        got[name]=expected
    assert len(set(got.values()))==len(got)
    # A host text layer translating LF to CRLF changes the hashed stream;
    # model the adapter only, not a personal Windows machine.
    stream = io.BytesIO()
    wrapper = io.TextIOWrapper(stream,encoding="utf-8",newline="\r\n")
    wrapper.write(SAMPLE)
    wrapper.flush()
    assert h.sha(stream.getvalue())==got["crlf"] and got["crlf"]!=got["lf"]
    wrapper.detach()

    old = json.loads((h.ROOT/"evidence/reservation-rust-macos-capture.json").read_text())
    assert h.check_capture(old)["format"]==h.CAPTURE_V1
    with tempfile.TemporaryDirectory(prefix="rust-transport-check-") as scratch:
        src = Path(scratch)/"reserve-crlf.rs"
        src.write_bytes(h.SOURCE.read_bytes().replace(b"\n",b"\r\n"))
        with patch.object(h,"SOURCE",src):
            original,variants,raw_hashes = h.rust_source_hashes()
            assert b"\r\n" in original
            assert variants["checked"]==original
            for name,variant in variants.items():
                out = Path(scratch)/(name+".rs")
                out.write_bytes(variant)
                assert b"\r\n" in out.read_bytes()
                assert h.sha(out.read_bytes())==raw_hashes[name]
            _,_,legacy_hashes = h.rust_source_hashes(legacy=True)
            assert raw_hashes["checked"] != legacy_hashes["checked"]
            # Only declared envelope handling is tested: this is not a real v2
            # run. The result payload is held constant and isn't graded here.
            v2 = deepcopy(old)
            v2.update(format=h.CAPTURE_V2,byte_transport=h.CAPTURE_BYTES,
                      source_sha256=h.sha(original),variant_sha256=raw_hashes)
            assert h.check_capture(v2)["format"]==h.CAPTURE_V2
            altered = deepcopy(v2)
            altered["variant_sha256"]=legacy_hashes
            refused(altered,"did not bind")
            altered = deepcopy(v2)
            altered["byte_transport"]="translated"
            refused(altered,"transport declaration")
            altered = deepcopy(v2)
            altered["wire_sha256"]=got["crlf"]
            refused(altered,"did not bind")
            refused(old,"did not bind")
    print(json.dumps({
        "case":"reservation-transport-bytes-v2","real_child_pipe_checks":2*len(got),
        "pipe_fixture_sha256":got,"exact_crlf_variant_file_checks":len(raw_hashes),
        "false_capture_controls_refused":4,"legacy_real_capture_format_accepted":h.CAPTURE_V1,
        "new_capture_schema_tested_with_metadata_only":h.CAPTURE_V2,
        "native_rust_runs_by_this_test":0,"text_newline_translation_changes_sha":True,
    },indent=2,sort_keys=True))


if __name__=="__main__":
    main()

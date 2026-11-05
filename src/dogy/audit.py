"""Prototype append-only hash chain. Not tamper-proof against an attacker who can rewrite the whole file."""
import hashlib
import json
import os
from pathlib import Path
from datetime import datetime, timezone

ZERO = "0" * 64

def _canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

def append_event(path: Path, event: str, details: dict | None = None):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    # Single-process PoC only; concurrent writers require a lock or central audit service.
    previous = ZERO
    if path.exists():
        ok, previous = verify(path)
        if not ok:
            raise ValueError("Audit chain invalid: refusing to append")
    record = {"timestamp": datetime.now(timezone.utc).isoformat(), "event": event,
              "details": details or {}, "previous_hash": previous}
    record["hash"] = hashlib.sha256(_canonical(record)).hexdigest()
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    try:
        with os.fdopen(fd, "a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
    finally:
        pass
    return record["hash"]

def verify(path: Path):
    previous = ZERO
    if not path.exists():
        return True, previous
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            record = json.loads(line)
            digest = record.pop("hash")
            if record["previous_hash"] != previous or hashlib.sha256(_canonical(record)).hexdigest() != digest:
                return False, previous
            previous = digest
    except (OSError, ValueError, KeyError, TypeError):
        return False, previous
    return True, previous

"""Persistence for derived window metadata (never source BIN payloads)."""
import json
import os
import tempfile

SCHEMA = "sismoai-windows"
VERSION = 1


def default_path():
    if os.name == "nt":
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
    else:
        base = os.environ.get("XDG_CONFIG_HOME", os.path.join(os.path.expanduser("~"), ".config"))
    return os.path.join(base, "SismoAI Trainer", "windows.json")


def load(path):
    try:
        with open(path, encoding="utf-8") as stream:
            data = json.load(stream)
        if (not isinstance(data, dict) or data.get("schema") != SCHEMA
                or data.get("schema_version") != VERSION
                or not isinstance(data.get("windows"), list)):
            return [], 0
        records = data["windows"]
        sequence = int(data.get("sequence", 0))
        if sequence < 0 or not all(isinstance(item, dict) for item in records):
            return [], 0
        return records, sequence
    except (OSError, ValueError, TypeError):
        return [], 0


def save(path, records, sequence):
    folder = os.path.dirname(path) or "."
    os.makedirs(folder, exist_ok=True)
    payload = {"schema": SCHEMA, "schema_version": VERSION,
               "sequence": int(sequence), "windows": records}
    fd, temporary = tempfile.mkstemp(prefix=".windows-", suffix=".tmp", dir=folder)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write("")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return os.path.abspath(path)

"""Atomic persistence for the Phase 7 labeling workspace."""
import json
import os
import tempfile

SCHEMA = "sismoai-labeling"
VERSION = 1


def default_path():
    if os.name == "nt":
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
    else:
        base = os.environ.get("XDG_CONFIG_HOME", os.path.join(os.path.expanduser("~"), ".config"))
    return os.path.join(base, "SismoAI Trainer", "labeling.json")


def load(path):
    try:
        with open(path, encoding="utf-8") as stream:
            data = json.load(stream)
        if (not isinstance(data, dict) or data.get("schema") != SCHEMA
                or data.get("schema_version") != VERSION
                or not isinstance(data.get("workspace"), dict)
                or not isinstance(data.get("labels"), dict)):
            return None
        return data
    except (OSError, ValueError, TypeError):
        return None


def save(path, workspace, labels):
    """Persist a manifest and annotations; signal arrays/BIN payloads stay out."""
    folder = os.path.dirname(path) or "."
    os.makedirs(folder, exist_ok=True)
    payload = {
        "schema": SCHEMA,
        "schema_version": VERSION,
        "workspace": workspace,
        "labels": labels,
    }
    fd, temporary = tempfile.mkstemp(prefix=".labeling-", suffix=".tmp", dir=folder)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return os.path.abspath(path)

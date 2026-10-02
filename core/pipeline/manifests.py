"""Named, immutable pipeline manifests for phase-to-phase handoff.

Each phase writes a standalone JSON artifact. IDs are stable; display names are
editable metadata and never determine identity or overwrite behavior.
"""
import json
import os
import re
import tempfile
import uuid
from datetime import datetime, timezone

SCHEMAS = {
    "windows": ("sismoai-window-selection", 1),
    "labels": ("sismoai-label-batch", 1),
}


class ManifestError(ValueError):
    pass


def _now():
    return datetime.now(timezone.utc).isoformat()


def _safe_name(name):
    value = str(name or "").strip()
    if not value or len(value) > 80:
        raise ManifestError("El nombre es obligatorio y debe tener hasta 80 caracteres.")
    if value in (".", "..") or re.search(r'[<>:"/\\|?*]', value):
        raise ManifestError("El nombre contiene caracteres no permitidos.")
    return value


def _atomic_json(path, payload):
    folder = os.path.dirname(path) or "."
    os.makedirs(folder, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".manifest-", suffix=".tmp", dir=folder)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def create_manifest(folder, kind, name, records, source_id=None):
    if kind not in SCHEMAS:
        raise ManifestError("Tipo de manifiesto no reconocido.")
    if not isinstance(records, list) or not records:
        raise ManifestError("No hay registros para guardar.")
    schema, version = SCHEMAS[kind]
    manifest_id = str(uuid.uuid4())
    payload = {
        "schema": schema,
        "schema_version": version,
        "id": manifest_id,
        "name": _safe_name(name),
        "created_at": _now(),
        "source_id": source_id,
        "records": records,
    }
    os.makedirs(folder, exist_ok=True)
    filename_name = re.sub(r"[^A-Za-z0-9_-]+", "_", payload["name"]).strip("_-") or kind
    path = os.path.join(folder, filename_name + "_" + manifest_id + ".json")
    _atomic_json(path, payload)
    return payload, os.path.abspath(path)


def list_manifests(folder, kind):
    if kind not in SCHEMAS:
        raise ManifestError("Tipo de manifiesto no reconocido.")
    schema, version = SCHEMAS[kind]
    result = []
    if not os.path.isdir(folder):
        return result
    for filename in sorted(os.listdir(folder), key=str.casefold):
        if not filename.lower().endswith(".json"):
            continue
        path = os.path.join(folder, filename)
        try:
            with open(path, encoding="utf-8") as stream:
                data = json.load(stream)
            if (isinstance(data, dict) and data.get("schema") == schema
                    and data.get("schema_version") == version
                    and isinstance(data.get("records"), list) and data.get("id")):
                result.append({
                    "filename": filename, "id": data["id"],
                    "name": data.get("name") or filename,
                    "created_at": data.get("created_at", ""),
                    "count": len(data["records"]), "path": os.path.abspath(path),
                })
        except (OSError, ValueError, TypeError):
            continue
    return result


def load_manifest(folder, kind, filename):
    safe = os.path.basename(str(filename or "").strip())
    if not safe or safe != filename or not safe.lower().endswith(".json"):
        raise ManifestError("Archivo de manifiesto no válido.")
    path = os.path.abspath(os.path.join(folder, safe))
    if os.path.commonpath([os.path.abspath(folder), path]) != os.path.abspath(folder):
        raise ManifestError("Ruta de manifiesto no permitida.")
    schema, version = SCHEMAS[kind]
    with open(path, encoding="utf-8") as stream:
        data = json.load(stream)
    if (not isinstance(data, dict) or data.get("schema") != schema
            or data.get("schema_version") != version
            or not isinstance(data.get("records"), list)):
        raise ManifestError("El archivo no es compatible con esta fase.")
    return data

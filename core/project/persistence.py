"""Project persistence (Phase 4): minimal folder-context format.

File (JSON, UTF-8): ``<AppConfigLocation>/SismoAI Trainer/project.json``

.. code-block:: json

    {
      "schema": "sismoai-project",
      "schema_version": 1,
      "folder": "F:/datos/Estacion_001"
    }

Only the selected source folder is persisted — never BIN contents.
Missing or invalid files fall back to "no folder" explicitly instead
of inventing state.
"""

import json
import os


SCHEMA_VERSION = 1
SCHEMA_NAME = "sismoai-project"
PROJECT_FILENAME = "project.json"


class ProjectPersistenceError(Exception):
    """Stored project context is invalid or unreadable."""


def default_path() -> str:
    """Get default project file path (cross-platform)."""
    # Use APPDATA on Windows, ~/.config on Linux/Mac
    if os.name == 'nt':
        base = os.environ.get('APPDATA', os.path.expanduser('~'))
    else:
        base = os.environ.get('XDG_CONFIG_HOME', os.path.join(os.path.expanduser('~'), '.config'))
    return os.path.join(base, "SismoAI Trainer", PROJECT_FILENAME)


def save_folder(path: str, folder: str) -> str:
    data = {"schema": SCHEMA_NAME, "schema_version": SCHEMA_VERSION,
            "folder": folder}
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")
    return os.path.abspath(path)


def load_folder(path: str) -> str:
    """Stored folder path, or "" when absent/invalid (never raises)."""
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return ""
    if not isinstance(data, dict):
        return ""
    if data.get("schema") != SCHEMA_NAME:
        return ""
    if data.get("schema_version") != SCHEMA_VERSION:
        return ""
    folder = data.get("folder", "")
    return folder if isinstance(folder, str) else ""
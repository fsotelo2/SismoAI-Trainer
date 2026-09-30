"""Project service package (Phase 4): folder-based project context.

The project owns the selected data folder and the session parsed from
it. Only the folder path is persisted (see persistence.py); BIN files
on disk stay the authoritative source and are only ever read.
"""

from .persistence import load_folder, save_folder
from .service import ProjectService

__all__ = ["ProjectService", "load_folder", "save_folder"]

"""Python-backed models for valid analysis source files (no Qt)."""

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class AnalysisFile:
    path: str
    name: str


class AnalysisFileListModel:
    """Simple list model for analysis files - no Qt, just data."""
    
    def __init__(self):
        self._rows: List[AnalysisFile] = []
        self._changed_callbacks: List[callable] = []

    def add_changed_callback(self, callback: callable):
        self._changed_callbacks.append(callback)

    def set_rows(self, rows: List[AnalysisFile]):
        rows = list(rows)
        if rows == self._rows:
            return False
        self._rows = rows
        for callback in self._changed_callbacks:
            callback()
        return True

    def path_at(self, row: int) -> str:
        return self._rows[row].path if 0 <= row < len(self._rows) else ""

    def index_of_path(self, path: str) -> int:
        return next((i for i, row in enumerate(self._rows)
                     if row.path == path), -1)

    def __len__(self):
        return len(self._rows)

    def __getitem__(self, index):
        return self._rows[index]


@dataclass(frozen=True)
class StaltaCandidateRow:
    sensor: str
    start_text: str
    end_text: str
    duration_text: str
    peak_ratio_text: str


class StaltaCandidateListModel:
    """Simple list model for STA/LTA candidates - no Qt, just data."""
    
    def __init__(self):
        self._rows: List[StaltaCandidateRow] = []
        self._changed_callbacks: List[callable] = []

    def add_changed_callback(self, callback: callable):
        self._changed_callbacks.append(callback)

    def set_rows(self, rows: List[StaltaCandidateRow]):
        rows = list(rows)
        if rows == self._rows:
            return False
        self._rows = rows
        for callback in self._changed_callbacks:
            callback()
        return True

    def __len__(self):
        return len(self._rows)

    def __getitem__(self, index):
        return self._rows[index]
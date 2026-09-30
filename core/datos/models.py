"""Python-backed data models for BIN files and their events (no Qt)."""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class BinFileTableModel:
    """Simple table model for file list - no Qt, just data."""
    rows: List['BinFileRow'] = None
    selected_path: str = ""
    selected_path_changed_callbacks: List[callable] = None

    def __post_init__(self):
        if self.rows is None:
            self.rows = []
        if self.selected_path_changed_callbacks is None:
            self.selected_path_changed_callbacks = []

    def set_rows(self, rows: List['BinFileRow'], selected_path: str = ""):
        self.rows = list(rows)
        self.selected_path = selected_path
        self._notify_selected_changed()

    def set_selected_path(self, path: str):
        if path == self.selected_path:
            return
        self.selected_path = path
        self._notify_selected_changed()

    def add_selected_path_changed_callback(self, callback: callable):
        self.selected_path_changed_callbacks.append(callback)

    def _notify_selected_changed(self):
        for callback in self.selected_path_changed_callbacks:
            callback(self.selected_path)


@dataclass
class EventTableModel:
    """Simple table model for events - no Qt, just data."""
    rows: List['EventRow'] = None

    def __post_init__(self):
        if self.rows is None:
            self.rows = []

    def set_rows(self, rows: List['EventRow']):
        self.rows = list(rows)
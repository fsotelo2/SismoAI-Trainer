"""Project source-folder state and read-only asynchronous inspection (no Qt)."""

import datetime
import os
import threading
from typing import List, Callable, Optional

from dataengine import load_session
from .persistence import default_path, load_folder, save_folder


def _display_time(value: datetime.datetime) -> str:
    return value.astimezone().strftime("%Y-%m-%d %H:%M")


class ProjectService:
    """Python-owned source folder, inspection state, and real summary."""

    STATE_EMPTY = "empty"
    STATE_INSPECTING = "inspecting"
    STATE_AVAILABLE = "available"
    STATE_NO_BIN = "no_bin"
    STATE_UNAVAILABLE = "unavailable"
    STATE_ERROR = "error"

    def __init__(self, persist_path=None, auto_restore=True):
        self._folder = ""
        self._summary = None
        self._last_scan = None
        self._error = ""
        self._state = self.STATE_EMPTY
        self._persist_path = persist_path or default_path()
        self._request_id = 0
        self._changed_callbacks: List[Callable] = []
        self._session_changed_callbacks: List[Callable[[Optional[object]], None]] = []
        
        if auto_restore:
            self.restore()

    # -- Callback registration -------------------------------------------
    def add_changed_callback(self, callback: Callable):
        self._changed_callbacks.append(callback)

    def add_session_changed_callback(self, callback: Callable[[Optional[object]], None]):
        self._session_changed_callbacks.append(callback)

    def _emit_changed(self):
        for callback in self._changed_callbacks:
            callback()

    def _emit_session_changed(self, summary):
        for callback in self._session_changed_callbacks:
            callback(summary)

    # -- state ---------------------------------------------------------
    @property
    def folder_path(self):
        return self._folder

    @property
    def has_folder(self):
        return bool(self._folder)

    @property
    def available(self):
        return self._state in (self.STATE_AVAILABLE, self.STATE_NO_BIN)

    @property
    def inspecting(self):
        return self._state == self.STATE_INSPECTING

    @property
    def state(self):
        return self._state

    @property
    def available_text(self):
        return {
            self.STATE_EMPTY: "Sin carpeta seleccionada",
            self.STATE_INSPECTING: "Inspeccionando carpeta…",
            self.STATE_AVAILABLE: "Carpeta disponible",
            self.STATE_NO_BIN: "Carpeta vacía (sin BIN)",
            self.STATE_UNAVAILABLE: "Carpeta no disponible",
            self.STATE_ERROR: "Error al inspeccionar la carpeta",
        }.get(self._state, "Estado desconocido")

    @property
    def file_count_text(self):
        return str(self._summary.file_count) if self._summary is not None else "—"

    @property
    def event_count_text(self):
        return str(self._summary.event_count) if self._summary is not None else "—"

    @property
    def windows_count_text(self):
        # No windowing module exists yet; do not imply the count is zero.
        return "Pendiente"

    @property
    def labels_count_text(self):
        # No labeling module exists yet; do not imply the count is zero.
        return "Pendiente"

    @property
    def last_scan_text(self):
        return _display_time(self._last_scan) if self._last_scan else "—"

    @property
    def error_text(self):
        return self._error

    @property
    def summary(self):
        return self._summary

    # -- persistence and inspection -----------------------------------
    def restore(self):
        """Restore the saved path and inspect it once at application start."""
        folder = load_folder(self._persist_path)
        if not folder:
            return
        self._folder = os.path.abspath(os.path.expanduser(folder))
        if not os.path.isdir(self._folder):
            self._state = self.STATE_UNAVAILABLE
            self._error = "La carpeta guardada ya no existe o no está disponible."
            self._emit_changed()
            return
        self._start_scan(self._folder)

    def _start_scan(self, folder):
        self._request_id += 1
        request_id = self._request_id
        self._folder = folder
        self._summary = None
        self._error = ""
        self._state = self.STATE_INSPECTING
        self._emit_changed()
        
        # Run scan in background thread
        thread = threading.Thread(target=self._scan_worker, args=(request_id, folder))
        thread.daemon = True
        thread.start()

    def _scan_worker(self, request_id, folder):
        try:
            summary = load_session(folder)
        except Exception as exc:
            self._scan_finished(request_id, folder, None, "No se pudo inspeccionar la carpeta: %s" % exc)
        else:
            self._scan_finished(request_id, folder, summary, "")

    def _scan_finished(self, request_id, folder, summary, error):
        # Ignore stale results if the user selected another folder meanwhile.
        if request_id != self._request_id or folder != self._folder:
            return
        if error:
            self._error = error
            self._summary = None
            self._state = self.STATE_UNAVAILABLE
        else:
            self._summary = summary
            self._last_scan = datetime.datetime.now().astimezone()
            self._error = ""
            self._state = (
                self.STATE_NO_BIN if summary.file_count == 0
                else self.STATE_AVAILABLE
            )
        self._emit_changed()
        self._emit_session_changed(summary)

    def select_folder(self, path_or_url):
        """Persist a chosen directory and start a read-only inspection."""
        value = path_or_url or ""
        # Handle file:// URLs
        if value.startswith("file://"):
            from urllib.parse import unquote
            import urllib.parse
            path = unquote(urllib.parse.urlparse(value).path)
            # On Windows, file:///C:/path -> /C:/path, need to fix
            if os.name == 'nt' and path.startswith('/'):
                path = path[1:]
        else:
            path = value
        path = os.path.abspath(os.path.expanduser(path)) if path else ""
        if not path or not os.path.isdir(path):
            self._error = "La carpeta seleccionada no existe o no está disponible."
            self._state = self.STATE_UNAVAILABLE if path else self.STATE_EMPTY
            self._emit_changed()
            return False
        try:
            save_folder(self._persist_path, path)
        except OSError as exc:
            self._error = "No se pudo guardar la carpeta seleccionada: %s" % exc
            self._state = self.STATE_ERROR
            self._emit_changed()
            return False
        self._last_scan = None
        self._start_scan(path)
        return True

    def rescan(self):
        """Reinspect the selected source."""
        if not self._folder:
            self._error = "No hay una carpeta seleccionada."
            self._state = self.STATE_EMPTY
            self._emit_changed()
            return False
        if not os.path.isdir(self._folder):
            self._error = "La carpeta seleccionada ya no está disponible."
            self._state = self.STATE_UNAVAILABLE
            self._emit_changed()
            return False
        self._start_scan(self._folder)
        return True

    def clear(self):
        self._request_id += 1
        self._folder = ""
        self._summary = None
        self._last_scan = None
        self._error = ""
        self._state = self.STATE_EMPTY
        try:
            if os.path.exists(self._persist_path):
                os.remove(self._persist_path)
        except OSError as exc:
            self._error = "No se pudo borrar la carpeta guardada: %s" % exc
            self._state = self.STATE_ERROR
        self._emit_changed()
        self._emit_session_changed(None)
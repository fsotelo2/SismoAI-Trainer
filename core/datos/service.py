"""Data workflow: BIN summaries, filtering, selection, and validation (no Qt)."""

import datetime
import hashlib
import os
from dataclasses import replace
from typing import List, Optional, Callable

from dataengine import parse_file
from dataengine.analysis import aggregate_observed_frequency
from dataengine.session import FileEntry

from .models import BinFileTableModel, EventTableModel
from .records import BinFileRow, EventRow


SENSOR_MPU = 1
SENSOR_GEOFONO = 2


def _date_text(epoch_us, with_seconds=False):
    if not epoch_us:
        return "—"
    try:
        value = datetime.datetime.fromtimestamp(epoch_us / 1_000_000).astimezone()
    except (OverflowError, OSError, ValueError):
        return "—"
    return value.strftime("%Y-%m-%d %H:%M:%S" if with_seconds
                          else "%Y-%m-%d %H:%M")


def _duration_seconds(start_us, end_us):
    if end_us < start_us:
        return None
    return (end_us - start_us) / 1_000_000.0


def _seconds_text(value, suffix=" s", decimals=1):
    return "—" if value is None else ("%.*f%s" % (decimals, value, suffix))


def _frequency_text(stats, suffix=" Hz"):
    if stats is None or stats.sample_count < 2 or stats.observed_hz <= 0:
        return "—"
    return "%.2f%s" % (stats.observed_hz, suffix)


def _file_frequency_text(quality, sensor):
    if quality is None:
        return "—"
    stats = [event.frequency[sensor] for event in quality.events
             if sensor in event.frequency]
    observed_hz = aggregate_observed_frequency(stats)
    return "%.2f Hz" % observed_hz if observed_hz > 0 else "—"


def _status_for_event(event_quality):
    if event_quality.crc_valido is False or event_quality.commit_valido is False:
        return "error", "Error"
    if event_quality.truncado:
        return "review", "Revisar"
    if not event_quality.valido:
        return "error", "Error"
    if event_quality.findings:
        return "review", "Revisar"
    return "valid", "OK"


def _status_for_file(entry):
    quality = entry.quality
    if entry.status != "ok" or quality is None:
        return "error", "Error"
    if quality.crc_failures or quality.commit_failures or quality.invalid_count:
        return "error", "Error"
    if quality.razones:
        return "error", "Error"
    if quality.truncated_count or quality.findings:
        return "review", "Revisar"
    if not quality.valido:
        return "error", "Error"
    return "valid", "Válido"


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _build_file_row(entry, result):
    quality = entry.quality
    status_code, status_text = _status_for_file(entry)
    try:
        stat = os.stat(entry.path)
        size = stat.st_size
        modified = datetime.datetime.fromtimestamp(stat.st_mtime).astimezone()
        modified_text = modified.strftime("%Y-%m-%d %H:%M:%S")
        size_text = "%.1f MB" % (size / (1024 * 1024))
        size_detail = "%.1f MB (%s bytes)" % (
            size / (1024 * 1024), format(size, ","))
    except OSError:
        size = None
        modified_text = "—"
        size_text = size_detail = "—"
    try:
        digest_text = _sha256(entry.path)
    except OSError:
        digest_text = "—"

    metadata = result.metadata if result is not None else None
    container = result.container if result is not None else None
    events = result.events if result is not None else []
    capture_text = _date_text(metadata.inicio_unix_us, with_seconds=True) \
        if metadata is not None else "—"
    capture_short = _date_text(metadata.inicio_unix_us) \
        if metadata is not None else "—"

    intervals = [
        _duration_seconds(event.inicio_us, event.fin_us)
        for event in events
    ]
    intervals = [value for value in intervals if value is not None]
    if events and intervals:
        file_duration = max(event.fin_us for event in events) - min(
            event.inicio_us for event in events)
        file_duration = max(0, file_duration) / 1_000_000.0
        duration_text = _seconds_text(file_duration)
    else:
        duration_text = "—"

    event_rows = []
    origin_us = min((event.inicio_us for event in events), default=None)
    for index, event in enumerate(events):
        event_quality = (
            quality.events[index]
            if quality is not None and index < len(quality.events) else None
        )
        if event_quality is None:
            geo_text = mpu_text = "—"
            event_status, event_status_text = "error", "Error"
        else:
            geo_text = _frequency_text(
                event_quality.frequency.get(SENSOR_GEOFONO), suffix="")
            mpu_text = _frequency_text(
                event_quality.frequency.get(SENSOR_MPU), suffix="")
            event_status, event_status_text = _status_for_event(event_quality)
        start = (
            (event.inicio_us - origin_us) / 1_000_000.0
            if origin_us is not None else None
        )
        event_rows.append(EventRow(
            number=index + 1,
            sequence=event.secuencia,
            start_text=_seconds_text(start, suffix="", decimals=3),
            duration_text=_seconds_text(
                _duration_seconds(event.inicio_us, event.fin_us),
                suffix="", decimals=2),
            geophone_hz_text=geo_text,
            mpu_hz_text=mpu_text,
            status_code=event_status,
            status_text=event_status_text,
        ))

    geo_frequency = _file_frequency_text(quality, SENSOR_GEOFONO)
    mpu_frequency = _file_frequency_text(quality, SENSOR_MPU)
    errors = []
    if quality is not None:
        errors.extend(quality.razones)
    if result is not None:
        errors.extend(reason for event in result.events for reason in event.razones)
    if entry.error:
        errors.append(entry.error)
    return BinFileRow(
        path=entry.path,
        name=os.path.basename(entry.path),
        sequence=entry.sequence,
        capture_date_text=capture_short,
        event_count_text=(str(quality.event_count) if quality is not None else "—"),
        duration_text=duration_text,
        size_text=size_text,
        size_detail_text=size_detail,
        status_code=status_code,
        status_text=status_text,
        format_version_text=(str(container.version) if container is not None else "—"),
        capture_detail_text=capture_text,
        geophone_frequency_text=geo_frequency,
        mpu_frequency_text=mpu_frequency,
        sha256_text=digest_text,
        modified_text=modified_text,
        errors=list(dict.fromkeys(error for error in errors if error)),
        events=event_rows,
    )


def _read_entry(entry):
    if entry.status != "ok":
        return _build_file_row(entry, None)
    result = parse_file(entry.path)
    return _build_file_row(entry, result)


class DataService:
    """Python-owned data table state, selected file, and event details."""

    EMPTY = "empty"
    LOADING = "loading"
    READY = "ready"
    UNAVAILABLE = "unavailable"
    ERROR = "error"

    PAGE_SIZES = (25, 50, 100)

    def __init__(self, project_service):
        self._project = project_service
        self._file_model = BinFileTableModel()
        self._event_model = EventTableModel()
        self._records = []
        self._selected_path = ""
        self._state = self.EMPTY
        self._error = ""
        self._query = ""
        self._status_filter = "all"
        self._page_size = 50
        self._page = 0
        self._request_id = 0
        
        # Callbacks for UI updates
        self._changed_callbacks: List[Callable] = []
        self._analysis_requested_callbacks: List[Callable[[str], None]] = []

        # Subscribe to project changes
        self._project.add_changed_callback(self._project_changed)
        self._project.add_session_changed_callback(self._session_changed)
        if self._project.inspecting:
            self._state = self.LOADING
        elif self._project.state in (self._project.STATE_UNAVAILABLE,
                                     self._project.STATE_ERROR):
            self._state = self.UNAVAILABLE

    # -- Callback registration -------------------------------------------
    def add_changed_callback(self, callback: Callable):
        self._changed_callbacks.append(callback)

    def add_analysis_requested_callback(self, callback: Callable[[str], None]):
        self._analysis_requested_callbacks.append(callback)

    def _emit_changed(self):
        for callback in self._changed_callbacks:
            callback()

    def _emit_analysis_requested(self, path: str):
        for callback in self._analysis_requested_callbacks:
            callback(path)

    # -- Models and state -------------------------------------------
    @property
    def file_model(self):
        return self._file_model

    @property
    def event_model(self):
        return self._event_model

    @property
    def state(self):
        return self._state

    @property
    def loading(self):
        return self._state == self.LOADING

    @property
    def error_text(self):
        return self._error

    @property
    def empty_text(self):
        if self._state == self.LOADING:
            return "Cargando y validando archivos BIN…"
        if self._state == self.UNAVAILABLE:
            return self._error or "La carpeta de datos no está disponible."
        if not self._project.has_folder:
            return "Selecciona una carpeta de datos en Proyecto."
        if not self._records:
            return "La carpeta de datos no contiene archivos BIN."
        if not self._filtered_rows():
            return "No hay archivos BIN que coincidan con el filtro."
        return ""

    @property
    def search_text(self):
        return self._query

    @property
    def status_filter(self):
        return self._status_filter

    @property
    def page_size(self):
        return self._page_size

    @property
    def current_page(self):
        return self._page + 1 if self.page_count else 0

    @property
    def page_count(self):
        count = self.filtered_file_count
        return (count + self._page_size - 1) // self._page_size

    @property
    def current_page_text(self):
        return "%d" % self.current_page if self.current_page else "—"

    @property
    def file_count(self):
        return len(self._records)

    @property
    def filtered_file_count(self):
        return len(self._filtered_rows())

    @property
    def file_count_text(self):
        return str(self.filtered_file_count)

    @property
    def selected_count_text(self):
        return "1 archivo seleccionado" if self._selected_path else "0 archivos seleccionados"

    @property
    def selected_file_path(self):
        return self._selected_path

    @property
    def selected_file_name(self):
        record = self._selected_record()
        return record.name if record else ""

    @property
    def selected_file_status_text(self):
        record = self._selected_record()
        return record.status_text if record else "—"

    @property
    def selected_file_status_code(self):
        record = self._selected_record()
        return record.status_code if record else "unknown"

    @property
    def can_analyze(self):
        record = self._selected_record()
        return record is not None and record.status_code == "valid"

    @property
    def selected_reason_text(self):
        record = self._selected_record()
        return "; ".join(record.errors) if record and record.errors else ""

    @property
    def selected_format_version_text(self):
        record = self._selected_record()
        return record.format_version_text if record else "—"

    @property
    def selected_capture_date_text(self):
        record = self._selected_record()
        return record.capture_detail_text if record else "—"

    @property
    def selected_size_text(self):
        record = self._selected_record()
        return record.size_detail_text if record else "—"

    @property
    def selected_event_count_text(self):
        record = self._selected_record()
        return str(len(record.events)) if record else "—"

    @property
    def selected_duration_text(self):
        record = self._selected_record()
        return record.duration_text if record else "—"

    @property
    def selected_geophone_frequency_text(self):
        record = self._selected_record()
        return record.geophone_frequency_text if record else "—"

    @property
    def selected_mpu_frequency_text(self):
        record = self._selected_record()
        return record.mpu_frequency_text if record else "—"

    @property
    def selected_sha256_text(self):
        record = self._selected_record()
        return record.sha256_text if record else "—"

    @property
    def selected_modified_text(self):
        record = self._selected_record()
        return record.modified_text if record else "—"

    @property
    def selected_events_title(self):
        record = self._selected_record()
        return "Eventos del archivo (%d)" % len(record.events) \
            if record else "Eventos del archivo (—)"

    def _selected_record(self):
        return next((row for row in self._records
                     if row.path == self._selected_path), None)

    def analysis_sources(self):
        """Return valid BINs with valid events for the Analysis workflow."""
        if self._state != self.READY:
            return []
        return [
            (row.path, row.name)
            for row in self._records
            if row.status_code == "valid"
            and any(event.status_code == "valid" for event in row.events)
        ]

    def _filtered_rows(self):
        query = self._query.casefold().strip()
        return [
            row for row in self._records
            if (not query or query in row.name.casefold())
            and (self._status_filter == "all"
                 or row.status_code == self._status_filter)
        ]

    def _refresh_models(self):
        rows = self._filtered_rows()
        count = len(rows)
        page_count = (count + self._page_size - 1) // self._page_size
        self._page = min(self._page, max(0, page_count - 1))
        self._file_model.set_rows(self._visible_rows(), self._selected_path)
        selected = self._selected_record()
        self._event_model.set_rows(selected.events if selected else [])
        self._emit_changed()

    def _visible_rows(self):
        rows = self._filtered_rows()
        start = self._page * self._page_size
        return rows[start:start + self._page_size]

    # -- project updates and asynchronous loading ---------------------
    def _project_changed(self):
        if self._project.inspecting:
            self._request_id += 1
            self._records = []
            self._selected_path = ""
            self._error = ""
            self._state = self.LOADING
            self._refresh_models()
        elif self._project.state in (self._project.STATE_EMPTY,
                                     self._project.STATE_UNAVAILABLE,
                                     self._project.STATE_ERROR):
            self._request_id += 1
            self._records = []
            self._selected_path = ""
            self._error = self._project.error_text
            self._state = (self.UNAVAILABLE if self._project.has_folder
                           else self.EMPTY)
            self._refresh_models()

    def _session_changed(self, summary):
        self._request_id += 1
        request_id = self._request_id
        if summary is None:
            self._records = []
            self._selected_path = ""
            self._error = self._project.error_text
            self._state = (self.UNAVAILABLE if self._project.has_folder
                           else self.EMPTY)
            self._refresh_models()
            return
        self._records = []
        self._selected_path = ""
        self._error = ""
        self._state = self.LOADING
        self._refresh_models()
        # In web version, load synchronously for simplicity
        # For large datasets, could use threading
        self._load_files_sync(request_id, summary.files)

    def _load_files_sync(self, request_id, entries):
        rows = []
        try:
            for entry in entries:
                try:
                    rows.append(_read_entry(entry))
                except Exception as exc:
                    failed = replace(
                        entry, status="error",
                        error="No se pudo leer: %s" % exc,
                    )
                    rows.append(_build_file_row(failed, None))
        except Exception as exc:
            self._records = []
            self._error = "No se pudieron cargar los archivos BIN: %s" % exc
            self._state = self.ERROR
        else:
            self._records = list(rows)
            self._state = self.READY
            self._error = ""
        self._page = 0
        self._refresh_models()

    # -- Python-owned search, filters, paging, and selection ------------
    def set_search_text(self, text):
        self._query = text or ""
        self._page = 0
        self._refresh_models()

    def set_status_filter(self, status):
        if status not in ("all", "valid", "review", "error"):
            return
        self._status_filter = status
        self._page = 0
        self._refresh_models()

    def set_page_size(self, size):
        size = int(size)
        if size not in self.PAGE_SIZES:
            return
        self._page_size = size
        self._page = 0
        self._refresh_models()

    def set_page(self, page):
        self._page = max(0, int(page) - 1)
        self._refresh_models()

    def select_file(self, path):
        if not any(row.path == path for row in self._records):
            return
        self._selected_path = path
        self._file_model.set_selected_path(path)
        self._refresh_models()

    def select_file_at_row(self, row):
        rows = self._visible_rows()
        if 0 <= row < len(rows):
            self.select_file(rows[row].path)

    def clear_selection(self):
        self._selected_path = ""
        self._file_model.set_selected_path("")
        self._refresh_models()

    def copy_selected_hash(self):
        record = self._selected_record()
        if not record or record.sha256_text == "—":
            return
        # Clipboard access would be handled by JS side
        return record.sha256_text

    def open_analysis(self):
        if self.can_analyze:
            self._emit_analysis_requested(self._selected_path)
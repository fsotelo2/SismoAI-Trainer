"""ApiBridge: Python methods exposed to JavaScript via pywebview.

This class acts as the contract between the web UI (HTML/CSS/JS) and the
Python core. All methods return JSON-serializable structures (dicts, lists,
strings, numbers, booleans, None).

Usage in JavaScript:
    const result = await window.pywebview.api.select_data_folder();
"""

import os
import json
import math
import re
from typing import Optional

from core.project.service import ProjectService
from core.datos.service import DataService
from core.analysis.service import AnalysisService
from core.dataengine import parse_file
from core.dataengine.series import CHANNEL_VELOCITY, CHANNEL_MAGNITUDE
from core.analysis.stalta import calculate_stalta
from core.analysis.spectrum import calculate_spectrum
from core.analysis.spectrogram import calculate_spectrogram
from core.windowing import (
    WindowSpec, WindowingError, build_window, evaluate_structure,
    generate_intervals, seconds_to_us, validate_sensors,
)
from core.windowing.models import ORIGIN_FIXED, ORIGIN_SLIDING, ORIGIN_MANUAL, WindowRecord, WindowQuality
from core.windowing import persistence as window_persistence
from core.labeling.service import LabelingService
from core.labeling.models import LabelingError
from core.dataset.service import build_manifest, save_manifest, DatasetError
from core.pipeline import manifests as pipeline_manifests


def _sanitize_nan(obj):
    """Recursively convert NaN floats to None for valid JSON serialization."""
    if isinstance(obj, float) and math.isnan(obj):
        return None
    if isinstance(obj, list):
        return [_sanitize_nan(item) for item in obj]
    if isinstance(obj, dict):
        return {key: _sanitize_nan(value) for key, value in obj.items()}
    return obj


class ApiBridge:
    """Bridge between Python core and JavaScript UI."""

    def __init__(self):
        self._project = ProjectService()
        self._data = DataService(self._project)
        self._analysis = AnalysisService(self._data)
        self._window_path = window_persistence.default_path()
        self._window_records = []
        self._window_sequence = 0
        self._restore_windows()
        self._labeling = LabelingService()
        self._window_selection_dir = os.path.join(os.path.dirname(self._window_path), 'window_selections')
        self._active_window_selection = None
        self._active_label_batch = None
        self._active_label_items = []
        self._legacy_global_dataset_path = os.path.join(os.path.dirname(self._window_path), 'dataset.json')
        self._dataset_dir = ""
        self._dataset_path = ""
        self._legacy_dataset_path = ""
        self._active_dataset = None
        self._configure_dataset_paths()
        self._restore_dataset()

        # Wire callbacks for potential future async notifications
        self._project.add_changed_callback(self._on_project_changed)
        self._data.add_changed_callback(self._on_data_changed)

    # ------------------------------------------------------------------
    # Internal callbacks (reserved for future push notifications)
    # ------------------------------------------------------------------

    def _on_project_changed(self):
        """Called when project state changes (reserved for future use)."""
        pass

    def _on_data_changed(self):
        """Called when data state changes (reserved for future use)."""
        pass

    # ------------------------------------------------------------------
    # 1. Project Management
    # ------------------------------------------------------------------

    def select_data_folder(self) -> dict:
        """Open native directory picker and return selected folder info.

        Returns:
            dict with keys: path, file_count, status
            status is one of: "ok", "error", "cancelled"
        """
        try:
            import webview
            result = webview.windows[0].create_file_dialog(
                webview.FOLDER_DIALOG
            )
            if not result:
                return {"path": "", "file_count": 0, "status": "cancelled"}

            folder = result[0] if isinstance(result, tuple) else result
            if not folder or not os.path.isdir(folder):
                return {"path": "", "file_count": 0, "status": "error"}

            self._project.select_folder(folder)
            self._configure_dataset_paths()
            self._active_dataset = None
            self._restore_dataset()

            # Wait for scan to complete (simplified: synchronous check)
            import time
            max_wait = 30  # seconds
            waited = 0
            while self._project.inspecting and waited < max_wait:
                time.sleep(0.1)
                waited += 0.1

            summary = self._project.summary
            file_count = summary.file_count if summary else 0

            return {
                "path": folder,
                "file_count": file_count,
                "status": "ok" if self._project.available else "error"
            }
        except Exception as exc:
            return {"path": "", "file_count": 0, "status": "error", "error": str(exc)}

    def get_project_state(self) -> dict:
        """Return current project state.

        Returns:
            dict with keys: state, folder_path, file_count, event_count,
                           available_text, error_text, last_scan_text
        """
        try:
            summary = self._project.summary
            return {
                "state": self._project.state,
                "folder_path": self._project.folder_path,
                "dataset_manifest_path": self._dataset_path,
                "file_count": self._project.file_count_text,
                "event_count": self._project.event_count_text,
                "available_text": self._project.available_text,
                "error_text": self._project.error_text,
                "last_scan_text": self._project.last_scan_text,
            }
        except Exception as exc:
            return {
                "state": "error",
                "folder_path": "",
                "file_count": "—",
                "event_count": "—",
                "available_text": "Error al obtener estado del proyecto",
                "error_text": str(exc),
                "last_scan_text": "—",
            }

    def rescan_project(self) -> dict:
        """Re-inspect the selected source folder.

        Returns:
            dict with keys: success, state, file_count
        """
        try:
            success = self._project.rescan()
            return {
                "success": success,
                "state": self._project.state,
                "file_count": self._project.file_count_text,
            }
        except Exception as exc:
            return {"success": False, "state": "error", "file_count": "—", "error": str(exc)}

    # ------------------------------------------------------------------
    # 2. Data Service
    # ------------------------------------------------------------------

    def scan_files(self) -> list:
        """Return list of BIN files with metadata.

        Returns:
            list of dicts, each with keys: path, name, status_code, status_text,
            size_text, event_count_text, duration_text, sha256_text,
            format_version_text, capture_date_text, size_detail_text,
            geophone_frequency_text, mpu_frequency_text, modified_text
        """
        try:
            rows = self._data.file_model.rows
            result = []
            for row in rows:
                result.append({
                    "path": row.path,
                    "name": row.name,
                    "status_code": row.status_code,
                    "status_text": row.status_text,
                    "size_text": row.size_text,
                    "size_detail_text": row.size_detail_text,
                    "event_count_text": row.event_count_text,
                    "duration_text": row.duration_text,
                    "sha256_text": row.sha256_text,
                    "format_version_text": row.format_version_text,
                    "capture_date_text": row.capture_date_text,
                    "geophone_frequency_text": row.geophone_frequency_text,
                    "mpu_frequency_text": row.mpu_frequency_text,
                    "modified_text": row.modified_text,
                })
            return result
        except Exception as exc:
            return [{"error": str(exc)}]

    def get_quality_summary(self, file_name: str) -> dict:
        """Return quality metrics and continuity for a specific file.

        Args:
            file_name: Name of the BIN file (not full path)

        Returns:
            dict with quality metrics
        """
        try:
            # Find the record by name
            record = None
            for row in self._data.file_model.rows:
                if row.name == file_name:
                    record = row
                    break

            if record is None:
                return {"error": f"Archivo no encontrado: {file_name}"}

            return {
                "name": record.name,
                "status_code": record.status_code,
                "status_text": record.status_text,
                "format_version_text": record.format_version_text,
                "capture_date_text": record.capture_date_text,
                "size_text": record.size_text,
                "event_count_text": record.event_count_text,
                "duration_text": record.duration_text,
                "geophone_frequency_text": record.geophone_frequency_text,
                "mpu_frequency_text": record.mpu_frequency_text,
                "sha256_text": record.sha256_text,
                "modified_text": record.modified_text,
                "errors": record.errors,
            }
        except Exception as exc:
            return {"error": str(exc)}

    def get_file_events(self, file_name: str) -> list:
        """Return events for a specific file.

        Args:
            file_name: Name of the BIN file

        Returns:
            list of event dicts
        """
        try:
            record = None
            for row in self._data.file_model.rows:
                if row.name == file_name:
                    record = row
                    break

            if record is None:
                return []

            return [
                {
                    "number": event.number,
                    "sequence": event.sequence,
                    "start_text": event.start_text,
                    "duration_text": event.duration_text,
                    "geophone_hz_text": event.geophone_hz_text,
                    "mpu_hz_text": event.mpu_hz_text,
                    "status_code": event.status_code,
                    "status_text": event.status_text,
                }
                for event in record.events
            ]
        except Exception as exc:
            return [{"error": str(exc)}]

    def select_file(self, file_name: str) -> dict:
        """Select a file by name.

        Args:
            file_name: Name of the BIN file

        Returns:
            dict with success status
        """
        try:
            for row in self._data.file_model.rows:
                if row.name == file_name:
                    self._data.select_file(row.path)
                    return {"success": True}
            return {"success": False, "error": f"Archivo no encontrado: {file_name}"}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def get_data_state(self) -> dict:
        """Return current data service state.

        Returns:
            dict with state information
        """
        try:
            return {
                "state": self._data.state,
                "loading": self._data.loading,
                "file_count": self._data.file_count_text,
                "selected_file_name": self._data.selected_file_name,
                "selected_file_status_text": self._data.selected_file_status_text,
                "can_analyze": self._data.can_analyze,
                "error_text": self._data.error_text,
            }
        except Exception as exc:
            return {"state": "error", "error_text": str(exc)}

    # ------------------------------------------------------------------
    # 3. Seismic Analysis Service
    # ------------------------------------------------------------------

    def get_channel_series(self, file_name: str, event_index: int, channel: str) -> dict:
        """Return time series for a specific channel.

        Args:
            file_name: Name of the BIN file
            event_index: 0-based event index
            channel: One of "velocity" (geophone), "magnitude" (MPU)

        Returns:
            dict with keys: times, amplitudes, sampling_rate
        """
        try:
            # Find the file path
            file_path = None
            for row in self._data.file_model.rows:
                if row.name == file_name:
                    file_path = row.path
                    break

            if file_path is None:
                return {"error": f"Archivo no encontrado: {file_name}"}

            # Parse the file
            result = parse_file(file_path)
            events = result.events

            if event_index < 0 or event_index >= len(events):
                return {"error": f"Índice de evento fuera de rango: {event_index}"}

            event = events[event_index]
            if not event.valido:
                return {"error": f"El evento {event_index} no es válido"}

            # Get analysis and series
            from core.dataengine.analysis import analyze_event
            from core.dataengine.series import event_series

            analysis = analyze_event(event)
            series_by_channel = event_series(event, analysis)

            if channel == "velocity":
                series = series_by_channel[CHANNEL_VELOCITY]
            elif channel == "magnitude":
                series = series_by_channel[CHANNEL_MAGNITUDE]
            else:
                return {"error": f"Canal no soportado: {channel}"}

            # Build ordered series
            ordered = sorted(series.samples,
                             key=lambda s: (s.timestamp_us, s.source_index))

            # Get event start for relative times
            origin_us = event.inicio_us
            times = [(s.timestamp_us - origin_us) / 1_000_000.0 for s in ordered]
            amplitudes = [s.value for s in ordered]

            # Determine sampling rate
            sampling_rate = 0.0
            if len(times) > 1:
                duration = times[-1] - times[0]
                if duration > 0:
                    sampling_rate = (len(times) - 1) / duration

            return {
                "times": times,
                "amplitudes": amplitudes,
                "sampling_rate": sampling_rate,
            }
        except Exception as exc:
            return {"error": str(exc)}

    def run_stalta(self, params: dict) -> dict:
        """Execute STA/LTA calculation.

        Args:
            params: dict with keys:
                - file_name: str
                - event_index: int
                - channel: "velocity" or "magnitude"
                - sta_window_seconds: float
                - lta_window_seconds: float
                - activation_threshold: float
                - deactivation_threshold: float
                - method: "absolute" or "rms"

        Returns:
            dict with keys: cfs, triggers, sta, lta, ratio
        """
        try:
            file_name = params.get("file_name", "")
            event_index = int(params.get("event_index", 0))
            channel = params.get("channel", "velocity")
            sta_window = float(params.get("sta_window_seconds", 0.5))
            lta_window = float(params.get("lta_window_seconds", 5.0))
            activation = float(params.get("activation_threshold", 3.0))
            deactivation = float(params.get("deactivation_threshold", 1.5))
            method = params.get("method", "absolute")

            # Get series data
            series_data = self.get_channel_series(file_name, event_index, channel)
            if "error" in series_data:
                return series_data

            times = series_data["times"]
            amplitudes = series_data["amplitudes"]
            sampling_rate = series_data["sampling_rate"]

            if sampling_rate <= 0:
                return {"error": "No se pudo determinar la frecuencia de muestreo"}

            # Calculate STA/LTA
            result = calculate_stalta(
                times,
                amplitudes,
                sampling_rate,
                sta_window,
                lta_window,
                activation,
                deactivation,
                method,
            )

            return {
                "cfs": result.cfs,
                "triggers": result.triggers,
                "sta": result.sta,
                "lta": result.lta,
                "ratio": result.ratio,
            }
        except Exception as exc:
            return {"error": str(exc)}

    def run_spectrum(self, params: dict) -> dict:
        """Execute spectrum calculation.

        Args:
            params: dict with keys:
                - file_name: str
                - event_index: int
                - channel: "velocity" or "magnitude"
                - window: "hann", "hamming", or "rectangular"
                - range_hz: float or None for Nyquist

        Returns:
            dict with keys: frequencies, magnitudes
        """
        try:
            file_name = params.get("file_name", "")
            event_index = int(params.get("event_index", 0))
            channel = params.get("channel", "velocity")
            window = params.get("window", "hann")
            range_hz = params.get("range_hz", None)

            if range_hz is not None:
                range_hz = float(range_hz)

            # Get series data
            series_data = self.get_channel_series(file_name, event_index, channel)
            if "error" in series_data:
                return series_data

            times = series_data["times"]
            amplitudes = series_data["amplitudes"]
            sampling_rate = series_data["sampling_rate"]

            if sampling_rate <= 0:
                return {"error": "No se pudo determinar la frecuencia de muestreo"}

            # Calculate spectrum
            result = calculate_spectrum(
                times,
                amplitudes,
                sampling_rate,
                window,
                range_hz,
            )

            return {
                "frequencies": result.freqs,
                "magnitudes": result.amps,
            }
        except Exception as exc:
            return {"error": str(exc)}

    def run_spectrogram(self, params: dict) -> dict:
        """Execute spectrogram calculation.

        Args:
            params: dict with keys:
                - file_name: str
                - event_index: int
                - channel: "velocity" or "magnitude"
                - window: "hann", "hamming", or "rectangular"
                - duration_seconds: float
                - overlap: float (0.0 to 1.0)
                - range_hz: float or None for Nyquist

        Returns:
            dict with keys: times, frequencies, intensities (2D matrix)
        """
        try:
            file_name = params.get("file_name", "")
            event_index = int(params.get("event_index", 0))
            channel = params.get("channel", "velocity")
            window = params.get("window", "hann")
            duration = float(params.get("duration_seconds", 1.0))
            overlap = float(params.get("overlap", 0.5))
            range_hz = params.get("range_hz", None)

            if range_hz is not None:
                range_hz = float(range_hz)

            # Get series data
            series_data = self.get_channel_series(file_name, event_index, channel)
            if "error" in series_data:
                return series_data

            times = series_data["times"]
            amplitudes = series_data["amplitudes"]
            sampling_rate = series_data["sampling_rate"]

            if sampling_rate <= 0:
                return {"error": "No se pudo determinar la frecuencia de muestreo"}

            # Calculate spectrogram
            result = calculate_spectrogram(
                times,
                amplitudes,
                sampling_rate,
                window,
                duration,
                overlap,
                range_hz,
            )

            return {
                "times": result.times,
                "frequencies": result.freqs,
                "intensities": result.amps,
            }
        except Exception as exc:
            return {"error": str(exc)}

    def get_analysis_state(self) -> dict:
        """Return current analysis state.

        Returns:
            dict with analysis state information
        """
        try:
            return _sanitize_nan({
                "state": self._analysis.state,
                "loading": self._analysis.loading,
                "state_text": self._analysis.state_text,
                "error_text": self._analysis.error_text,
                "has_selection": self._analysis.has_selection,
                "selected_file_name": self._analysis.selected_file_name,
                "selected_event_index": self._analysis._selected_index,
                "total_events": len(self._analysis._events),
                "can_select_previous_event": self._analysis.can_select_previous_event,
                "can_select_next_event": self._analysis.can_select_next_event,
                "event_counter_text": self._analysis.event_counter_text,
                "event_start_text": self._analysis.event_start_text,
                "event_end_text": self._analysis.event_end_text,
                "event_duration_text": self._analysis.event_duration_text,
                "event_sample_count_text": self._analysis.event_sample_count_text,
                "geophone_frequency_text": self._analysis.geophone_frequency_text,
                "mpu_frequency_text": self._analysis.mpu_frequency_text,
                "active_submenu": self._analysis.active_submenu,
                "selected_metric_sensor": self._analysis.selected_metric_sensor,
                "cursor_time": self._analysis.cursor_time,
                "geophone_cursor_text": self._analysis.geophone_cursor_text,
                "mpu_cursor_text": self._analysis.mpu_cursor_text,
                "dominant_frequency_text": self._analysis.dominant_frequency_text,
                "maximum_amplitude_text": self._analysis.maximum_amplitude_text,
                "rms_text": self._analysis.rms_text,
                "snr_text": self._analysis.snr_text,
                "jitter_text": self._analysis.jitter_text,
                "saturated_samples_text": self._analysis.saturated_samples_text,
                "signal_findings_text": self._analysis.signal_findings_text,
                "geophone_times": self._analysis.geophone_times,
                "geophone_values": self._analysis.geophone_values,
                "mpu_times": self._analysis.mpu_times,
                "mpu_values": self._analysis.mpu_values,
                "geophone_sta_values": self._analysis.geophone_sta_values,
                "geophone_lta_values": self._analysis.geophone_lta_values,
                "geophone_ratio_values": self._analysis.geophone_ratio_values,
                "mpu_sta_values": self._analysis.mpu_sta_values,
                "mpu_lta_values": self._analysis.mpu_lta_values,
                "mpu_ratio_values": self._analysis.mpu_ratio_values,
                "geophone_ratio_peak_text": self._analysis.geophone_ratio_peak_text,
                "geophone_mean_lta_text": self._analysis.geophone_mean_lta_text,
                "mpu_ratio_peak_text": self._analysis.mpu_ratio_peak_text,
                "mpu_mean_lta_text": self._analysis.mpu_mean_lta_text,
                "geophone_spectrum_freqs": self._analysis.geophone_spectrum_freqs,
                "geophone_spectrum_amps": self._analysis.geophone_spectrum_amps,
                "mpu_spectrum_freqs": self._analysis.mpu_spectrum_freqs,
                "mpu_spectrum_amps": self._analysis.mpu_spectrum_amps,
                "spectral_dominant_frequency_text": self._analysis.spectral_dominant_frequency_text,
                "spectral_dominant_amplitude_text": self._analysis.spectral_dominant_amplitude_text,
                "spectral_centroid_text": self._analysis.spectral_centroid_text,
                "spectral_bandwidth_text": self._analysis.spectral_bandwidth_text,
                "geophone_spectrogram_times": self._analysis.geophone_spectrogram_times,
                "geophone_spectrogram_freqs": self._analysis.geophone_spectrogram_freqs,
                "geophone_spectrogram_amps": self._analysis.geophone_spectrogram_amps,
                "geophone_spectrogram_frame_count": self._analysis.geophone_spectrogram_frame_count,
                "geophone_spectrogram_bin_count": self._analysis.geophone_spectrogram_bin_count,
                "mpu_spectrogram_times": self._analysis.mpu_spectrogram_times,
                "mpu_spectrogram_freqs": self._analysis.mpu_spectrogram_freqs,
                "mpu_spectrogram_amps": self._analysis.mpu_spectrogram_amps,
                "mpu_spectrogram_frame_count": self._analysis.mpu_spectrogram_frame_count,
                "mpu_spectrogram_bin_count": self._analysis.mpu_spectrogram_bin_count,
                "spectrogram_resolution_text": self._analysis.spectrogram_resolution_text,
                "spectrogram_dominant_band_text": self._analysis.spectrogram_dominant_band_text,
            })
        except Exception as exc:
            return {"state": "error", "error_text": str(exc)}

    def get_analysis_files(self) -> list:
        """Return list of valid files available for analysis.

        Returns:
            list of dicts with keys: path, name
        """
        try:
            # Opening the Windows file list also activates Analysis. This ensures
            # its default valid BIN/event is loaded even when the user never
            # visited the Analysis view first.
            self._analysis.activate()
            sources = self._data.analysis_sources()
            return [{"path": path, "name": name} for path, name in sources]
        except Exception as exc:
            return [{"error": str(exc)}]

    def select_analysis_file(self, file_name: str) -> dict:
        """Select a file for analysis.

        Args:
            file_name: Name of the BIN file

        Returns:
            dict with success status
        """
        try:
            self._analysis.activate()
            sources = self._data.analysis_sources()
            for path, name in sources:
                if name == file_name:
                    self._analysis.select_file(path)
                    return {"success": True}
            return {"success": False, "error": f"Archivo no encontrado: {file_name}"}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def select_analysis_event(self, event_index: int) -> dict:
        """Select an event by index.

        Args:
            event_index: 0-based event index

        Returns:
            dict with success status
        """
        try:
            if event_index < 0:
                return {"success": False, "error": "Índice inválido"}

            # Use the analysis service's internal methods
            current = self._analysis._selected_index
            if event_index < current:
                for _ in range(current - event_index):
                    self._analysis.previous_event()
            elif event_index > current:
                for _ in range(event_index - current):
                    self._analysis.next_event()

            return {"success": True}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def get_analysis_event_data(self) -> dict:
        """Return data for the currently selected event.

        Returns:
            dict with event data including times, values, metrics
        """
        try:
            if not self._analysis.has_selection:
                return {"error": "No hay evento seleccionado"}

            return {
                "geophone_times": self._analysis.geophone_times,
                "geophone_values": self._analysis.geophone_values,
                "mpu_times": self._analysis.mpu_times,
                "mpu_values": self._analysis.mpu_values,
                "plot_x_minimum": self._analysis.plot_x_minimum,
                "plot_x_maximum": self._analysis.plot_x_maximum,
                "view_x_minimum": self._analysis.view_x_minimum,
                "view_x_maximum": self._analysis.view_x_maximum,
                "geophone_view_y_minimum": self._analysis.geophone_view_y_minimum,
                "geophone_view_y_maximum": self._analysis.geophone_view_y_maximum,
                "mpu_view_y_minimum": self._analysis.mpu_view_y_minimum,
                "mpu_view_y_maximum": self._analysis.mpu_view_y_maximum,
            }
        except Exception as exc:
            return {"error": str(exc)}

    def get_analysis_metrics(self) -> dict:
        """Return signal metrics for the selected event.

        Returns:
            dict with metrics for geophone and MPU
        """
        try:
            if not self._analysis.has_selection:
                return {"error": "No hay evento seleccionado"}

            return {
                "geophone": self._analysis._metrics.get("geophone"),
                "mpu": self._analysis._metrics.get("mpu"),
                "selected_sensor": self._analysis.selected_metric_sensor,
            }
        except Exception as exc:
            return {"error": str(exc)}

    def get_stalta_results(self) -> dict:
        """Return STA/LTA results for the selected event.

        Returns:
            dict with STA/LTA data
        """
        try:
            if not self._analysis.has_selection:
                return {"error": "No hay evento seleccionado"}

            return {
                "geophone_sta": self._analysis.geophone_sta_values,
                "geophone_lta": self._analysis.geophone_lta_values,
                "geophone_ratio": self._analysis.geophone_ratio_values,
                "mpu_sta": self._analysis.mpu_sta_values,
                "mpu_lta": self._analysis.mpu_lta_values,
                "mpu_ratio": self._analysis.mpu_ratio_values,
                "sta_window_text": self._analysis.sta_window_text,
                "lta_window_text": self._analysis.lta_window_text,
                "activation_threshold_text": self._analysis.activation_threshold_text,
                "deactivation_threshold_text": self._analysis.deactivation_threshold_text,
            }
        except Exception as exc:
            return {"error": str(exc)}

    def get_spectrum_results(self) -> dict:
        """Return spectrum results for the selected event.

        Returns:
            dict with spectrum data
        """
        try:
            if not self._analysis.has_selection:
                return {"error": "No hay evento seleccionado"}

            return {
                "geophone_freqs": self._analysis.geophone_spectrum_freqs,
                "geophone_amps": self._analysis.geophone_spectrum_amps,
                "mpu_freqs": self._analysis.mpu_spectrum_freqs,
                "mpu_amps": self._analysis.mpu_spectrum_amps,
                "spectrum_window_text": self._analysis.spectrum_window_text,
                "spectrum_range_text": self._analysis.spectrum_range_text,
            }
        except Exception as exc:
            return {"error": str(exc)}

    def get_spectrogram_results(self) -> dict:
        """Return spectrogram results for the selected event.

        Returns:
            dict with spectrogram data
        """
        try:
            if not self._analysis.has_selection:
                return {"error": "No hay evento seleccionado"}

            return {
                "geophone_times": self._analysis.geophone_spectrogram_times,
                "geophone_freqs": self._analysis.geophone_spectrogram_freqs,
                "geophone_amps": self._analysis.geophone_spectrogram_amps,
                "mpu_times": self._analysis.mpu_spectrogram_times,
                "mpu_freqs": self._analysis.mpu_spectrogram_freqs,
                "mpu_amps": self._analysis.mpu_spectrogram_amps,
                "spectrogram_window_text": self._analysis.spectrogram_window_text,
                "spectrogram_duration_text": self._analysis.spectrogram_duration_text,
                "spectrogram_overlap_text": self._analysis.spectrogram_overlap_text,
                "spectrogram_range_text": self._analysis.spectrogram_range_text,
            }
        except Exception as exc:
            return {"error": str(exc)}

    def set_stalta_parameters(self, params: dict) -> dict:
        """Update STA/LTA parameters.

        Args:
            params: dict with keys: sta_window, lta_window, activation_threshold,
                           deactivation_threshold, method

        Returns:
            dict with success status
        """
        try:
            if "sta_window" in params:
                self._analysis.set_stalta_parameter("sta", float(params["sta_window"]))
            if "lta_window" in params:
                self._analysis.set_stalta_parameter("lta", float(params["lta_window"]))
            if "activation_threshold" in params:
                self._analysis.set_stalta_parameter("activation", float(params["activation_threshold"]))
            if "deactivation_threshold" in params:
                self._analysis.set_stalta_parameter("deactivation", float(params["deactivation_threshold"]))
            if "method" in params:
                self._analysis.set_stalta_method(params["method"])

            return {"success": True}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def set_spectrum_parameters(self, params: dict) -> dict:
        """Update spectrum parameters.

        Args:
            params: dict with keys: window, range_hz

        Returns:
            dict with success status
        """
        try:
            if "window" in params:
                self._analysis.set_spectrum_window(params["window"])
            if "range_hz" in params:
                self._analysis.set_spectrum_range_hz(float(params["range_hz"]))

            return {"success": True}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def set_spectrogram_parameters(self, params: dict) -> dict:
        """Update spectrogram parameters.

        Args:
            params: dict with keys: window, duration_seconds, overlap, range_hz

        Returns:
            dict with success status
        """
        try:
            if "window" in params:
                self._analysis.set_spectrogram_window(params["window"])
            if "duration_seconds" in params:
                self._analysis.set_spectrogram_duration(float(params["duration_seconds"]))
            if "overlap" in params:
                self._analysis.set_spectrogram_overlap(float(params["overlap"]))
            if "range_hz" in params:
                self._analysis.set_spectrogram_range_hz(float(params["range_hz"]))

            return {"success": True}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def set_metric_sensor(self, sensor: str) -> dict:
        """Set the active metric sensor.

        Args:
            sensor: "geophone" or "mpu"

        Returns:
            dict with success status
        """
        try:
            self._analysis.set_metric_sensor(sensor)
            return {"success": True}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def select_submenu(self, submenu: str) -> dict:
        """Select analysis submenu.

        Args:
            submenu: "senales", "espectrograma", "frecuencia", "sta_lta"

        Returns:
            dict with success status
        """
        try:
            self._analysis.select_submenu(submenu)
            return {"success": True}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def set_cursor_time(self, time_seconds: float) -> dict:
        """Set cursor time for inspection.

        Args:
            time_seconds: Time in seconds

        Returns:
            dict with success status
        """
        try:
            self._analysis.set_cursor_time(float(time_seconds))
            return {"success": True}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def clear_cursor(self) -> dict:
        """Clear cursor selection.

        Returns:
            dict with success status
        """
        try:
            self._analysis.clear_cursor()
            return {"success": True}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def get_cursor_texts(self) -> dict:
        """Return cursor text information.

        Returns:
            dict with cursor texts
        """
        try:
            return {
                "geophone_cursor_text": self._analysis.geophone_cursor_text,
                "mpu_cursor_text": self._analysis.mpu_cursor_text,
                "geophone_stalta_cursor_text": self._analysis.geophone_stalta_cursor_text,
                "mpu_stalta_cursor_text": self._analysis.mpu_stalta_cursor_text,
            }
        except Exception as exc:
            return {"error": str(exc)}

    def zoom_time(self, factor: float, anchor_ratio: float) -> dict:
        """Zoom time axis.

        Args:
            factor: Zoom factor
            anchor_ratio: Anchor position ratio (0-1)

        Returns:
            dict with success status
        """
        try:
            self._analysis.zoom_time(float(factor), float(anchor_ratio))
            return {"success": True}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def pan_viewport(self, sensor: str, horizontal_fraction: float, vertical_fraction: float) -> dict:
        """Pan viewport.

        Args:
            sensor: "geophone" or "mpu"
            horizontal_fraction: Horizontal pan fraction
            vertical_fraction: Vertical pan fraction

        Returns:
            dict with success status
        """
        try:
            self._analysis.pan_viewport(sensor, float(horizontal_fraction), float(vertical_fraction))
            return {"success": True}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def reset_viewport(self) -> dict:
        """Reset viewport to default.

        Returns:
            dict with success status
        """
        try:
            self._analysis.reset_viewport()
            return {"success": True}
        except Exception as exc:
            return {"success": False, "error": str(exc)}


    # ------------------------------------------------------------------
    # 8. Phase 6 — Windowing
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # 7. Human window labeling
    # ------------------------------------------------------------------

    def _configure_dataset_paths(self):
        """Use the selected project folder as root; manifests are named after datasets."""
        project_root = self._project.folder_path
        if project_root:
            root = os.path.abspath(os.path.expanduser(project_root))
            self._dataset_dir = os.path.join(root, "Dataset")
            self._window_selection_dir = os.path.join(root, "ventanas")
            self._legacy_dataset_path = os.path.join(root, "dataset.json")
        else:
            base = os.path.dirname(self._window_path)
            self._dataset_dir = os.path.join(base, "Dataset")
            self._window_selection_dir = os.path.join(base, "ventanas")
            self._legacy_dataset_path = os.path.join(base, "dataset.json")
        os.makedirs(self._window_selection_dir, exist_ok=True)
        self._dataset_path = os.path.join(self._dataset_dir, "dataset_activo.json")

    @staticmethod
    def _dataset_filename(name):
        """Convert a display name into a safe, portable JSON filename."""
        value = str(name or "").strip()[:80]
        invalid = set('<>:"/\\|?*')
        value = "".join("_" if char in invalid or ord(char) < 32 else char for char in value)
        value = value.rstrip(" .")
        return (value or "Dataset_sin_nombre") + ".json"

    def _restore_dataset(self):
        # Load the most recently created valid named manifest in this project.
        candidates = []
        try:
            if os.path.isdir(self._dataset_dir):
                candidates = [
                    os.path.join(self._dataset_dir, filename)
                    for filename in os.listdir(self._dataset_dir)
                    if filename.lower().endswith(".json")
                ]
        except OSError:
            candidates = []
        candidates.extend([self._legacy_dataset_path])
        if not self._project.folder_path:
            candidates.append(self._legacy_global_dataset_path)
        valid = []
        for candidate in candidates:
            try:
                with open(candidate, encoding="utf-8") as stream:
                    data = json.load(stream)
                if not isinstance(data, dict):
                    continue
                if data.get("schema") == "sismoai-dataset" and data.get("schema_version") == 1:
                    valid.append((str(data.get("created_at", "")), candidate, data))
            except (OSError, ValueError, TypeError):
                continue
        if not valid:
            self._active_dataset = None
            self._dataset_path = os.path.join(self._dataset_dir, "dataset_activo.json")
            return
        _, candidate, data = max(valid, key=lambda item: item[0])
        self._active_dataset = data
        desired = os.path.join(self._dataset_dir, self._dataset_filename(data.get("name")))
        if os.path.abspath(candidate) != os.path.abspath(desired):
            save_manifest(desired, data)
        self._dataset_path = desired

    def get_dataset_catalog(self) -> dict:
        """Return saved Dataset manifests without depending on labeling/window workspace."""
        try:
            datasets = self._list_dataset_manifests()
            active = self._active_dataset
            active_path = self._dataset_path
            # Restore from disk if the in-memory selection is absent or stale.
            if not active or not active.get("dataset_id"):
                self._restore_dataset()
                active = self._active_dataset
                active_path = self._dataset_path
            return {
                "success": True,
                "datasets": datasets,
                "active_dataset": active,
                "manifest_path": active_path,
                "dataset_dir": self._dataset_dir,
            }
        except Exception as exc:
            return {"success": False, "error": str(exc), "datasets": [], "active_dataset": None}

    def create_label_batch(self, name):
        try:
            workspace = self.get_labeling_workspace()
            items = workspace.get("items", [])
            if not items or any(not x.get("label") for x in items):
                return {"success": False, "error": "Todas las ventanas deben estar etiquetadas antes de guardar."}
            source_id = (self._active_window_selection or {}).get("id")
            if not source_id and self._active_label_batch:
                source_id = self._active_label_batch.get("source_id")
            manifest, path = pipeline_manifests.create_manifest(
                os.path.join(os.path.dirname(self._window_selection_dir), "Etiquetados"),
                "labels", name, items, source_id=source_id)
            self._active_label_batch = manifest
            return {"success": True, "batch": manifest, "filename": os.path.basename(path)}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def get_label_batches(self):
        folder = os.path.join(os.path.dirname(self._window_selection_dir), "Etiquetados")
        return {"success": True, "items": pipeline_manifests.list_manifests(folder, "labels")}

    def select_label_batch(self, filename):
        try:
            folder = os.path.join(os.path.dirname(self._window_selection_dir), "Etiquetados")
            self._active_label_batch = pipeline_manifests.load_manifest(folder, "labels", filename)
            self._active_label_items = self._active_label_batch.get("records", [])
            return {"success": True, "batch": self._active_label_batch}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def get_dataset_workspace(self) -> dict:
        try:
            if self._active_label_batch:
                items = [dict(x) for x in self._active_label_batch.get("records", [])]
            else:
                items = []
            counts = {"total": len(items), "labeled": 0, "pending": 0, "classes": {"0": 0, "1": 0}, "events": 0}
            events = set()
            for item in items:
                label = item.get("label") or {}
                code = label.get("class_code")
                if code in (0, 1) and label.get("quality_review") == "confirmed":
                    counts["labeled"] += 1
                    counts["classes"][str(code)] += 1
                else:
                    counts["pending"] += 1
                w = item["window"]
                if w.get("source_event_id") is not None:
                    events.add((w.get("source_file"), str(w.get("source_event_id"))))
            counts["events"] = len(events)
            return {"success": True, "items": items, "counts": counts, "active_dataset": self._active_dataset, "datasets": self._list_dataset_manifests(), "label_batches": self.get_label_batches().get("items", []), "active_label_batch": self._active_label_batch, "manifest_path": self._dataset_path}
        except Exception as exc:
            return {"success": False, "error": str(exc), "items": [], "counts": {}}

    def _list_dataset_manifests(self):
        """List valid named manifests saved in the selected project's Dataset folder."""
        datasets = []
        try:
            os.makedirs(self._dataset_dir, exist_ok=True)
            for filename in sorted(os.listdir(self._dataset_dir), key=str.casefold):
                if not filename.lower().endswith(".json"):
                    continue
                path = os.path.join(self._dataset_dir, filename)
                if not os.path.isfile(path):
                    continue
                try:
                    with open(path, encoding="utf-8") as stream:
                        data = json.load(stream)
                    if not isinstance(data, dict):
                        continue
                    if data.get("schema") != "sismoai-dataset" or data.get("schema_version") != 1:
                        continue
                    if not data.get("dataset_id") or not isinstance(data.get("splits"), dict):
                        continue
                    datasets.append({
                        "filename": filename,
                        "name": data.get("name") or os.path.splitext(filename)[0],
                        "dataset_id": data["dataset_id"],
                        "created_at": data.get("created_at", ""),
                        "windows": (data.get("summary") or {}).get("all", {}).get("windows", 0),
                        "active": bool(self._active_dataset and self._active_dataset.get("dataset_id") == data.get("dataset_id")),
                    })
                except (OSError, ValueError, TypeError):
                    continue
        except OSError:
            pass
        return datasets

    def delete_dataset(self, filename: str) -> dict:
        """Delete a saved Dataset manifest; preserve source data and refuse dangling experiment references."""
        try:
            safe_name = os.path.basename(str(filename or "").strip())
            if not safe_name or safe_name != filename or not safe_name.lower().endswith(".json"):
                raise ValueError("Nombre de archivo de Dataset no válido.")
            path = os.path.abspath(os.path.join(self._dataset_dir, safe_name))
            if os.path.dirname(path) != os.path.abspath(self._dataset_dir):
                raise ValueError("Ruta de Dataset no válida.")
            with open(path, encoding="utf-8") as stream:
                manifest = json.load(stream)
            if (not isinstance(manifest, dict) or manifest.get("schema") != "sismoai-dataset"
                    or manifest.get("schema_version") != 1 or not manifest.get("dataset_id")):
                raise ValueError("El archivo no contiene un manifiesto SismoAI válido.")
            dataset_id = str(manifest["dataset_id"])
            experiments = self.get_model_experiments()
            if experiments.get("success"):
                linked = [x for x in experiments.get("experiments", [])
                          if isinstance(x, dict) and str(x.get("dataset_id")) == dataset_id]
                if linked:
                    raise ValueError("Este Dataset está asociado a " + str(len(linked)) +
                                     " experimento(s). Elimina primero esos experimentos desde MODELOS.")
            os.remove(path)
            snapshot_dir = os.path.join(self._dataset_dir, "dataset_" + dataset_id + "_data")
            if os.path.isdir(snapshot_dir):
                import shutil
                shutil.rmtree(snapshot_dir)
            was_active = bool(self._active_dataset and str(self._active_dataset.get("dataset_id")) == dataset_id)
            if was_active:
                self._active_dataset = None
                self._dataset_path = ""
                remaining = self._list_dataset_manifests()
                if remaining:
                    selected = self.select_dataset(remaining[0]["filename"])
                    if not selected.get("success"):
                        return {"success": True, "deleted": safe_name, "active_dataset": None,
                                "warning": selected.get("error")}
            return {"success": True, "deleted": safe_name, "active_dataset": self._active_dataset,
                    "datasets": self._list_dataset_manifests()}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def select_dataset(self, filename: str) -> dict:
        """Select one saved manifest by filename from the current project's Dataset folder."""
        try:
            safe_name = os.path.basename(str(filename or "").strip())
            if safe_name != filename or not safe_name.lower().endswith(".json"):
                return {"success": False, "error": "Nombre de archivo de Dataset no válido."}
            path = os.path.join(self._dataset_dir, safe_name)
            with open(path, encoding="utf-8") as stream:
                data = json.load(stream)
            if (data.get("schema") != "sismoai-dataset" or data.get("schema_version") != 1
                    or not data.get("dataset_id") or not isinstance(data.get("splits"), dict)):
                return {"success": False, "error": "El archivo no contiene un manifiesto SismoAI válido."}
            self._active_dataset = data
            self._dataset_path = path
            return {"success": True, "active_dataset": data, "manifest_path": path,
                    "datasets": self._list_dataset_manifests()}
        except (OSError, ValueError, TypeError) as exc:
            return {"success": False, "error": "No se pudo cargar el Dataset: " + str(exc)}

    def generate_dataset(self, ratios=None, seed=42, name=None) -> dict:
        try:
            workspace = self.get_dataset_workspace()
            if not workspace.get("success"):
                raise DatasetError(workspace.get("error", "No se pudo leer Etiquetado."))
            ratios = ratios or [0.70, 0.15, 0.15]
            manifest = build_manifest(workspace["items"], tuple(ratios), seed)
            manifest["source_label_batch_id"] = (self._active_label_batch or {}).get("id")
            manifest["source_selection_id"] = (self._active_label_batch or {}).get("source_id")
            if name is not None:
                manifest["name"] = str(name).strip()[:80] or "Dataset_sin_nombre"
            else:
                manifest["name"] = "Dataset_sin_nombre"
            # Persist an immutable physical snapshot of every included window's signals.
            import numpy as np
            snapshot_dirname = "dataset_" + str(manifest["dataset_id"]) + "_data"
            snapshot_dir = os.path.join(self._dataset_dir, snapshot_dirname)
            os.makedirs(snapshot_dir, exist_ok=False)
            items_by_id = {str((x.get("window") or {}).get("window_id")): x
                           for x in workspace["items"]}
            try:
                for split_name, rows in manifest["splits"].items():
                    for row_index, row in enumerate(rows):
                        wid = str(row["window_id"])
                        signal = self.get_window_signal(wid)
                        if not signal.get("success"):
                            raise DatasetError("No se pudo capturar la ventana " + wid + ": " +
                                               str(signal.get("error", "error desconocido")))
                        payload = {}
                        for sensor in ("GEO", "MPU"):
                            channel = (signal.get("signals") or {}).get(sensor) or {}
                            times = channel.get("times") or []
                            amplitudes = channel.get("amplitudes") or []
                            if sensor in (row.get("sensors") or []) and (len(times) < 2 or len(times) != len(amplitudes)):
                                raise DatasetError("La ventana " + wid + " no tiene señales válidas para " + sensor + ".")
                            payload[sensor + "_times"] = np.asarray(times, dtype=np.float64)
                            payload[sensor + "_amplitudes"] = np.asarray(amplitudes, dtype=np.float32)
                        snapshot_name = split_name + "_" + str(row_index).zfill(5) + ".npz"
                        np.savez_compressed(os.path.join(snapshot_dir, snapshot_name), **payload)
                        row["snapshot"] = os.path.join(snapshot_dirname, snapshot_name)
                manifest["snapshot"] = {"format": "npz_per_window", "version": 1,
                                         "immutable": True, "window_count": sum(len(v) for v in manifest["splits"].values())}
            except Exception:
                import shutil
                shutil.rmtree(snapshot_dir, ignore_errors=True)
                raise
            # Source locator and reconstruction semantics for consumers of this manifest.
            manifest["source"] = {
                "root_path": os.path.abspath(self._project.folder_path) if self._project.folder_path else None,
                "file_field": "source_file",
                "event_field": "event_index",
                "event_index_base": 0,
                "time_unit": "microseconds",
                "time_reference": "event_relative",
                "interval_convention": "[start_us, end_us)",
                "reconstruction": "Load source_file from root_path, parse BIN, select event_index, then crop each listed sensor to the window interval.",
            }
            # Explicit contract consumed by Phase 9 Modelos/trainer.
            manifest["model_contract"] = {
                "task": "binary_classification",
                "framework": "pytorch",
                "input_shape": ["samples", "channels", "points"],
                "supported_inputs": ["geo_mpu", "geo", "mpu"],
                "points_per_window": 256,
                "normalization": "per_window_z_score",
                "label_field": "class_code",
                "classes": {"0": "TEMBLOR", "1": "NO_SISMICO"},
                "required_splits": ["train", "validation", "test"],
            }
            self._dataset_path = os.path.join(self._dataset_dir, self._dataset_filename(manifest["name"]))
            save_manifest(self._dataset_path, manifest)
            self._active_dataset = manifest
            return {"success": True, "dataset": manifest, "manifest_path": self._dataset_path}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def create_window_selection(self, name):
        try:
            records = [item.to_dict() for item in self._window_records
                       if item.selection_status == "include"]
            manifest_id = None
            # IDs are local to the immutable selection; the composite ref is globally unique.
            for record in records:
                record["window_ref"] = None
            manifest, path = pipeline_manifests.create_manifest(
                self._window_selection_dir, "windows", name, records)
            for record in manifest["records"]:
                record["selection_id"] = manifest["id"]
                record["window_ref"] = manifest["id"] + "::" + str(record.get("window_id"))
            # Persist the refs in the saved file after UUID creation.
            from core.pipeline.manifests import _atomic_json
            _atomic_json(path, manifest)
            self._active_window_selection = manifest
            self._active_label_batch = None
            self._active_label_items = [{"window": dict(w), "label": None} for w in manifest["records"]]
            return {"success": True, "selection": manifest, "filename": os.path.basename(path)}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def get_window_selections(self):
        try:
            return {"success": True, "items": pipeline_manifests.list_manifests(
                self._window_selection_dir, "windows")}
        except Exception as exc:
            return {"success": False, "error": str(exc), "items": []}

    def select_window_selection(self, filename):
        try:
            manifest = pipeline_manifests.load_manifest(
                self._window_selection_dir, "windows", filename)
            self._active_window_selection = manifest
            self._active_label_batch = None
            self._active_label_items = [{"window": dict(w), "label": None} for w in manifest["records"]]
            return {"success": True, "selection": manifest}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def get_labeling_workspace(self) -> dict:
        """Return the records of the selected immutable window selection."""
        try:
            if self._active_label_batch:
                items = [dict(x) for x in self._active_label_batch.get("records", [])]
            elif self._active_window_selection:
                items = self._active_label_items
            else:
                items = []
            counts = {"total": len(items), "pending": 0, "labeled": 0, "review": 0}
            for item in items:
                label = item.get("label")
                if not label or label.get("class_code") is None:
                    counts["pending"] += 1
                else:
                    counts["labeled"] += 1
                if label and label.get("quality_review") == "pending" and label.get("class_code") is not None:
                    counts["review"] += 1
            return {"success": True, "items": items, "counts": counts}
        except Exception as exc:
            return {"success": False, "error": str(exc), "items": [], "counts": {}}

    def get_window_signal(self, window_id: str) -> dict:
        """Load the source event channels and crop them to one window interval."""
        try:
            window = next((w for w in self._window_records if w.window_id == window_id), None)
            if window is None:
                return {"success": False, "error": "Ventana no encontrada."}
            try:
                event_index = int(window.source_event_id)
            except (TypeError, ValueError):
                return {"success": False, "error": "La ventana no tiene un índice de evento válido."}
            start, end = window.start_us / 1_000_000.0, window.end_us / 1_000_000.0
            result = {}
            for sensor, channel in (("GEO", "velocity"), ("MPU", "magnitude")):
                if sensor not in window.sensors:
                    result[sensor] = {"times": [], "amplitudes": []}
                    continue
                series = self.get_channel_series(window.source_file, event_index, channel)
                if "error" in series:
                    result[sensor] = {"times": [], "amplitudes": [], "error": series["error"]}
                    continue
                pairs = [(t, y) for t, y in zip(series["times"], series["amplitudes"])
                         if start <= t < end]
                result[sensor] = {"times": [p[0] for p in pairs],
                                  "amplitudes": [p[1] for p in pairs]}
            return {"success": True, "window_id": window_id, "signals": result}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def save_window_label(self, window_id: str, payload: dict, window_ref=None) -> dict:
        """Save annotation in the active batch, using the selection-scoped reference."""
        try:
            target_items = (self._active_label_batch or {}).get("records", []) or self._active_label_items
            entry = next((x for x in target_items
                          if (x.get("window") or {}).get("window_id") == window_id
                          and (not window_ref or (x.get("window") or {}).get("window_ref") == window_ref)), None)
            window = dict(entry.get("window")) if entry else None
            if window is None:
                return {"success": False, "error": "Ventana no encontrada en el conjunto activo."}
            label = self._labeling.save_label(window, payload)
            if entry is not None:
                entry["label"] = label
            return {"success": True, "label": label}
        except (LabelingError, TypeError, ValueError) as exc:
            return {"success": False, "error": str(exc)}
        except Exception as exc:
            return {"success": False, "error": "No se pudo guardar la etiqueta: " + str(exc)}

    def _restore_windows(self):
        raw_records, sequence = window_persistence.load(self._window_path)
        restored = []
        for raw in raw_records:
            try:
                item = dict(raw)
                q = item.get("quality") or {}
                item["quality"] = WindowQuality(q.get("status", "accepted"), tuple(q.get("findings", ())))
                item["sensors"] = tuple(item.get("sensors", ()))
                item["sample_ranges"] = {k: tuple(v) for k, v in (item.get("sample_ranges") or {}).items()}
                restored.append(WindowRecord(**item))
            except (TypeError, ValueError):
                continue
        self._window_records = restored
        self._window_sequence = max(sequence, len(restored))

    def _persist_windows(self):
        window_persistence.save(self._window_path, [item.to_dict() for item in self._window_records], self._window_sequence)

    @staticmethod
    def _window_sample_count(times, start_seconds, end_seconds):
        """Count samples in the half-open interval [start, end)."""
        import bisect
        left = bisect.bisect_left(times, start_seconds)
        right = bisect.bisect_left(times, end_seconds)
        return max(0, right - left)

    def get_window_context(self) -> dict:
        """Expose the selected Analysis event as windowing source context."""
        try:
            state = self.get_analysis_state()
            if not state.get("has_selection"):
                return {"ready": False, "message": "Seleccione un archivo y evento válido en Análisis."}
            geo_times = list(state.get("geophone_times") or [])
            mpu_times = list(state.get("mpu_times") or [])
            geo_values = list(state.get("geophone_values") or [])
            mpu_values = list(state.get("mpu_values") or [])
            selected = self._analysis._selected_event()
            origin_us = self._analysis._origin_us
            event_start = ((selected.start_us - origin_us) / 1_000_000.0
                           if selected is not None and origin_us is not None else 0.0)
            geo_times = [t - event_start for t in geo_times]
            mpu_times = [t - event_start for t in mpu_times]
            event_end = ((selected.end_us - origin_us) / 1_000_000.0
                         if selected is not None and origin_us is not None else event_start)
            duration = max(0.0, event_end - event_start)
            available = []
            if geo_times and geo_values:
                available.append("GEO")
            if mpu_times and mpu_values:
                available.append("MPU")
            return {
                "ready": bool(available),
                "message": "" if available else "El evento no contiene series utilizables.",
                "file_name": state.get("selected_file_name", ""),
                "event_index": state.get("selected_event_index", -1),
                "event_counter_text": state.get("event_counter_text", ""),
                "can_select_previous_event": state.get("can_select_previous_event", False),
                "can_select_next_event": state.get("can_select_next_event", False),
                "duration_seconds": duration,
                "geophone_frequency_text": state.get("geophone_frequency_text", "—"),
                "mpu_frequency_text": state.get("mpu_frequency_text", "—"),
                "available_sensors": available,
                "geophone_times": geo_times,
                "geophone_values": geo_values,
                "mpu_times": mpu_times,
                "mpu_values": mpu_values,
            }
        except Exception as exc:
            return {"ready": False, "message": str(exc)}

    def _add_window(self, start_seconds, end_seconds, mode, sensors, config):
        context = self.get_window_context()
        if not context.get("ready"):
            raise WindowingError(context.get("message", "No hay evento seleccionado."))
        chosen = validate_sensors(sensors, context["available_sensors"])
        bounds = (0, seconds_to_us(context["duration_seconds"]))
        start_us, end_us = seconds_to_us(start_seconds), seconds_to_us(end_seconds)
        from core.windowing import validate_interval
        validate_interval(start_us, end_us, bounds)
        counts, ranges = {}, {}
        import bisect
        for sensor in chosen:
            times = context["geophone_times"] if sensor == "GEO" else context["mpu_times"]
            left = bisect.bisect_left(times, start_seconds)
            right = bisect.bisect_left(times, end_seconds)
            counts[sensor] = max(0, right - left)
            ranges[sensor] = (left, right)
        quality = evaluate_structure(start_us, end_us, bounds, chosen, counts)
        if quality.status == "blocked":
            raise WindowingError("; ".join(quality.findings))
        self._window_sequence += 1
        record = build_window(
            "W-%03d" % self._window_sequence, context["file_name"],
            str(context["event_index"]), mode, start_us, end_us, chosen,
            config, counts, quality,
        )
        record.sample_ranges = ranges
        self._window_records.append(record)
        self._persist_windows()
        return record.to_dict()

    def generate_windows(self, params: dict) -> dict:
        """Generate fixed or sliding windows for the selected Analysis event."""
        try:
            context = self.get_window_context()
            if not context.get("ready"):
                return {"success": False, "error": context.get("message")}
            mode = str(params.get("mode", "fixed")).lower()
            duration = float(params.get("duration_seconds", 5.0))
            step = float(params.get("step_seconds", duration))
            sensors = params.get("sensors", context["available_sensors"])
            spec = WindowSpec(seconds_to_us(duration),
                              seconds_to_us(step), mode, discard_partial=True)
            intervals = generate_intervals(0, seconds_to_us(context["duration_seconds"]), spec)
            # Keep generation atomic: a rejected interval must not leave a partial batch.
            previous_records = list(self._window_records)
            previous_sequence = self._window_sequence
            created = []
            try:
                for start_us, end_us in intervals:
                    created.append(self._add_window(
                        start_us / 1_000_000.0, end_us / 1_000_000.0,
                        mode, sensors, {
                            "mode": mode, "duration_seconds": duration,
                            "step_seconds": step, "discard_partial": True,
                        }))
            except Exception:
                self._window_records = previous_records
                self._window_sequence = previous_sequence
                self._persist_windows()
                raise
            return {"success": True, "created": len(created), "windows": created}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def add_manual_window(self, params: dict) -> dict:
        """Add a manually selected interval in event-relative seconds."""
        try:
            record = self._add_window(
                float(params["start_seconds"]), float(params["end_seconds"]),
                ORIGIN_MANUAL, params.get("sensors", ["GEO", "MPU"]),
                {"reference": "event_relative_seconds"},
            )
            return {"success": True, "window": record}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def get_windows(self) -> list:
        """Return the complete persisted window registry across files and events."""
        return [item.to_dict() for item in self._window_records]

    def clear_windows(self) -> dict:
        """Clear extracted windows and restart their visible IDs from W-001."""
        previous_records = self._window_records
        previous_sequence = self._window_sequence
        cleared_ids = [item.window_id for item in previous_records]
        self._window_records = []
        self._window_sequence = 0
        try:
            self._persist_windows()
            # Remove annotations for cleared IDs so reused IDs cannot inherit
            # labels from the previous set of extracted windows.
            self._labeling.remove_labels(cleared_ids)
            return {"success": True}
        except Exception as exc:
            self._window_records = previous_records
            self._window_sequence = previous_sequence
            try:
                self._persist_windows()
            except Exception:
                pass
            return {"success": False, "error": str(exc)}

    def set_window_selection(self, window_id: str, status: str) -> dict:
        """Set include/review/exclude workflow status."""
        from core.windowing.models import SELECTION_EXCLUDE, SELECTION_INCLUDE, SELECTION_REVIEW
        allowed = {SELECTION_INCLUDE, SELECTION_REVIEW, SELECTION_EXCLUDE}
        if status not in allowed:
            return {"success": False, "error": "Estado de selección no reconocido."}
        for item in self._window_records:
            if item.window_id == window_id:
                item.selection_status = status
                try:
                    self._persist_windows()
                    return {"success": True}
                except Exception as exc:
                    return {"success": False, "error": str(exc)}
        return {"success": False, "error": "Ventana no encontrada."}


    # ------------------------------------------------------------------
    # 8. Model experiments — configuration registry (training not yet wired)
    # ------------------------------------------------------------------

    def _models_registry_path(self):
        """Store model experiment configurations in the project's Modelos folder."""
        project_root = self._project.folder_path
        if project_root:
            root = os.path.abspath(os.path.expanduser(project_root))
        else:
            root = os.path.dirname(self._window_path)
        return os.path.join(root, "Modelos", "model_experiments.json")

    def _legacy_models_registry_path(self):
        """Previous registry location, kept for one-time migration."""
        return os.path.join(os.path.dirname(self._dataset_path), "model_experiments.json")

    def get_model_experiments(self) -> dict:
        """Return saved experiment configurations; does not imply trained models."""
        try:
            path = self._models_registry_path()
            if not os.path.isfile(path):
                legacy_path = self._legacy_models_registry_path()
                if not os.path.isfile(legacy_path):
                    return {"success": True, "experiments": []}
                # Migrate existing records so changing the location does not hide them.
                with open(legacy_path, "r", encoding="utf-8") as stream:
                    data = json.load(stream)
                data = data if isinstance(data, list) else []
                os.makedirs(os.path.dirname(path), exist_ok=True)
                temp_path = path + ".tmp"
                with open(temp_path, "w", encoding="utf-8") as stream:
                    json.dump(data, stream, ensure_ascii=False, indent=2)
                os.replace(temp_path, path)
                return {"success": True, "experiments": data}
            with open(path, "r", encoding="utf-8") as stream:
                data = json.load(stream)
            return {"success": True, "experiments": data if isinstance(data, list) else []}
        except Exception as exc:
            return {"success": False, "experiments": [], "error": str(exc)}

    def save_model_experiment(self, config: dict, dataset_id: str, dataset_name: str) -> dict:
        """Validate and persist a reproducible experiment configuration."""
        try:
            if not isinstance(config, dict):
                raise ValueError("La configuración debe ser un objeto.")
            name = str(config.get("name", "")).strip()
            if not name or len(name) > 80:
                raise ValueError("El nombre es obligatorio y debe tener máximo 80 caracteres.")
            if not self._active_dataset or str(self._active_dataset.get("dataset_id", "")) != str(dataset_id):
                raise ValueError("El dataset activo cambió. Actualiza la vista y vuelve a intentar.")
            training = config.get("training")
            if not isinstance(training, dict):
                raise ValueError("La configuración de entrenamiento no es válida.")
            epochs_raw = training.get("epochs", 0)
            batch_raw = training.get("batch_size", 0)
            seed_raw = training.get("seed", -1)
            lr_raw = training.get("learning_rate", 0)
            if any(isinstance(v, bool) or not isinstance(v, int) for v in (epochs_raw, batch_raw, seed_raw)):
                raise ValueError("Épocas, batch size y semilla deben ser enteros.")
            epochs, batch_size, seed = epochs_raw, batch_raw, seed_raw
            try:
                learning_rate = float(lr_raw)
            except (TypeError, ValueError):
                raise ValueError("Learning rate no válido.")
            if not math.isfinite(learning_rate):
                raise ValueError("Learning rate debe ser finito.")
            if training.get("optimizer", "adam") not in ("adam", "adamw", "sgd"):
                raise ValueError("Optimizador no reconocido.")
            if training.get("loss", "cross_entropy") != "cross_entropy":
                raise ValueError("La única función de pérdida implementada es cross_entropy.")
            if not 1 <= epochs <= 10000:
                raise ValueError("Épocas fuera del rango permitido (1–10000).")
            if not 1 <= batch_size <= 4096:
                raise ValueError("Batch size fuera del rango permitido (1–4096).")
            if not 0 < learning_rate <= 1:
                raise ValueError("Learning rate fuera del rango permitido (0–1].")
            if seed < 0:
                raise ValueError("La semilla debe ser no negativa.")
            allowed_arch = {"1d_cnn", "feature_classifier", "baseline"}
            if config.get("architecture") not in allowed_arch:
                raise ValueError("Arquitectura no reconocida.")
            registry_result = self.get_model_experiments()
            if not registry_result.get("success"):
                raise ValueError("No se pudo leer el registro de experimentos: " + registry_result.get("error", "error desconocido"))
            registry = registry_result.get("experiments", [])
            # Reuse the existing experiment when the dataset and full configuration match.
            existing = next((item for item in reversed(registry)
                if isinstance(item, dict)
                and item.get("dataset_id") == str(dataset_id)
                and item.get("config") == config), None)
            if existing is not None:
                return {"success": True, "experiment_id": existing.get("experiment_id"), "existing": True}
            import uuid
            from datetime import datetime
            record = {
                "experiment_id": str(uuid.uuid4()),
                "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
                "status": "configuration",
                "dataset_id": str(dataset_id),
                "dataset_name": str(dataset_name),
                "config": config,
                "runs": [],
            }
            registry.append(record)
            path = self._models_registry_path()
            os.makedirs(os.path.dirname(path), exist_ok=True)
            temp_path = path + ".tmp"
            with open(temp_path, "w", encoding="utf-8") as stream:
                json.dump(registry, stream, ensure_ascii=False, indent=2)
            os.replace(temp_path, path)
            return {"success": True, "experiment_id": record["experiment_id"]}
        except Exception as exc:
            return {"success": False, "error": str(exc)}


    def delete_model_experiment(self, experiment_id: str) -> dict:
        """Delete one saved experiment record without deleting model weight files."""
        try:
            experiment_id = str(experiment_id or "").strip()
            if not experiment_id:
                raise ValueError("Identificador de experimento no válido.")
            thread = getattr(self, "_model_training_thread", None)
            state = getattr(self, "_model_training_state", {}) or {}
            if thread and thread.is_alive() and state.get("experiment_id") == experiment_id:
                raise ValueError("No se puede eliminar un experimento mientras está entrenando.")
            lock = getattr(self, "_model_registry_lock", None)
            if lock is None:
                import threading
                self._model_registry_lock = threading.RLock()
                lock = self._model_registry_lock
            with lock:
                result = self.get_model_experiments()
                if not result.get("success"):
                    raise ValueError("No se pudo leer el registro: " + result.get("error", "error desconocido"))
                registry = result.get("experiments", [])
                updated = [item for item in registry
                           if not isinstance(item, dict) or item.get("experiment_id") != experiment_id]
                if len(updated) == len(registry):
                    raise ValueError("Experimento no encontrado.")
                path = self._models_registry_path()
                os.makedirs(os.path.dirname(path), exist_ok=True)
                temp = path + ".tmp"
                with open(temp, "w", encoding="utf-8") as stream:
                    json.dump(updated, stream, ensure_ascii=False, indent=2, allow_nan=False)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(temp, path)
            return {"success": True, "experiment_id": experiment_id}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def get_model_training_state(self) -> dict:
        state = getattr(self, "_model_training_state", None)
        if state is None:
            return {"success": True, "status": "idle", "epoch": 0, "epochs": 0}
        return {"success": True, **state}

    def start_model_training(self, config: dict, dataset_id: str) -> dict:
        """Launch preparation and training in a worker so the UI remains responsive."""
        import threading
        try:
            lock = getattr(self, "_model_training_lock", None)
            if lock is None:
                self._model_training_lock = threading.RLock()
                lock = self._model_training_lock
            with lock:
                thread = getattr(self, "_model_training_thread", None)
                if thread and thread.is_alive():
                    return {"success": False, "error": "Ya existe un entrenamiento en ejecución."}
                if not self._active_dataset or str(self._active_dataset.get("dataset_id")) != str(dataset_id):
                    raise ValueError("El dataset activo cambió. Actualiza la vista.")
                if not isinstance(config, dict):
                    raise ValueError("Configuración no válida.")
                registry_result = self.get_model_experiments()
                if not registry_result.get("success"):
                    raise ValueError("No se pudo leer el registro de experimentos: " + registry_result.get("error", "error desconocido"))
                registry = registry_result.get("experiments", [])
                record = next((x for x in reversed(registry)
                               if x.get("dataset_id") == str(dataset_id)
                               and x.get("config") == config), None)
                if record is None:
                    saved = self.save_model_experiment(config, dataset_id,
                        self._active_dataset.get("name", "Dataset"))
                    if not saved.get("success"):
                        raise ValueError(saved.get("error", "No se pudo registrar el experimento."))
                    registry_result = self.get_model_experiments()
                    if not registry_result.get("success"):
                        raise ValueError("No se pudo confirmar el registro del experimento.")
                    record = next((x for x in reversed(registry_result.get("experiments", []))
                                   if x.get("experiment_id") == saved.get("experiment_id")), None)
                if record is None:
                    raise ValueError("No se encontró el experimento recién registrado.")
                # Freeze the manifest/config references for this run. Window records are
                # copied as a lookup; signal loading remains in the worker.
                import copy
                manifest = copy.deepcopy(self._active_dataset)
                manifest_path_snapshot = os.path.abspath(self._dataset_path)
                config_snapshot = copy.deepcopy(config)
                window_by_id = {w.window_id: w for w in list(self._window_records)}
                experiment_id = record["experiment_id"]
                self._update_model_record(experiment_id, {"status": "running", "error": None})
                output_dir = os.path.join(os.path.dirname(os.path.dirname(self._dataset_path)), "Modelos", str(experiment_id))
                os.makedirs(output_dir, exist_ok=True)
                self._model_training_state = {
                    "status": "preparing", "epoch": 0,
                    "epochs": int((config.get("training") or {}).get("epochs", 0)),
                    "experiment_id": experiment_id, "error": None, "progress": None,
                }

                def worker():
                    try:
                        import numpy as np
                        splits = manifest.get("splits") or {}
                        sensor_mode = config_snapshot.get("input", "geo_mpu")
                        sensors = {"geo_mpu": ("GEO", "MPU"), "geo": ("GEO",), "mpu": ("MPU",)}.get(sensor_mode)
                        if not sensors:
                            raise ValueError("Selección de señales no reconocida.")
                        points, arrays = 256, {}
                        for split_name in ("train", "validation", "test"):
                            rows = splits.get(split_name, [])
                            if not isinstance(rows, list):
                                raise ValueError("Partición inválida en el manifiesto: " + split_name)
                            xs, ys = [], []
                            for item in rows:
                                wid = item.get("window_id")
                                snapshot_rel = item.get("snapshot")
                                if not snapshot_rel:
                                    raise ValueError("El Dataset no contiene una copia física de la ventana " + str(wid) +
                                                     ". Genere nuevamente el Dataset desde Etiquetado.")
                                snapshot_base = os.path.abspath(os.path.dirname(manifest_path_snapshot))
                                snapshot_path = os.path.abspath(os.path.join(snapshot_base, snapshot_rel))
                                if os.path.commonpath([snapshot_base, snapshot_path]) != snapshot_base:
                                    raise ValueError("Ruta de snapshot inválida para la ventana " + str(wid))
                                if not os.path.isfile(snapshot_path):
                                    raise ValueError("No se encontró el archivo físico de la ventana " + str(wid) +
                                                     ": " + snapshot_path)
                                with np.load(snapshot_path, allow_pickle=False) as stored:
                                    channels = []
                                    for sensor in sensors:
                                        values_key, times_key = sensor + "_amplitudes", sensor + "_times"
                                        if values_key not in stored or times_key not in stored:
                                            raise ValueError("El snapshot de " + str(wid) + " no contiene " + sensor + ".")
                                        values = np.asarray(stored[values_key], dtype=np.float32)
                                        times = np.asarray(stored[times_key], dtype=np.float64)
                                        if len(values) < 2 or len(times) != len(values):
                                            raise ValueError("La ventana " + str(wid) + " no tiene muestras válidas de " + sensor + ".")
                                    if (not np.all(np.isfinite(values)) or not np.all(np.isfinite(times))
                                            or len(times) != len(values)):
                                        raise ValueError("Datos no finitos o desalineados en ventana " + str(wid) + ".")
                                    if np.any(np.diff(times) <= 0):
                                        raise ValueError("Los tiempos deben ser estrictamente crecientes en ventana " + str(wid) + ".")
                                    code = item.get("class_code")
                                    if isinstance(code, bool) or not isinstance(code, (int, np.integer)) or code not in (0, 1):
                                        raise ValueError("Código de clase inválido en ventana " + str(wid) + ".")
                                    target = np.linspace(float(times[0]), float(times[-1]), points)
                                    values = np.interp(target, times, values).astype(np.float32)
                                    std = float(values.std())
                                    values = (values - float(values.mean())) / (std if std > 1e-8 else 1.0)
                                    channels.append(values)
                                xs.append(np.stack(channels))
                                ys.append(int(item.get("class_code")))
                            arrays[split_name] = (
                                np.stack(xs).astype(np.float32) if xs else np.empty((0, len(sensors), points), dtype=np.float32),
                                np.asarray(ys, dtype=np.int64))
                        with self._model_training_lock:
                            self._model_training_state.update(status="running",
                                samples={k: len(v[1]) for k, v in arrays.items()})
                        from core.models.trainer import train_experiment
                        def on_progress(progress):
                            with self._model_training_lock:
                                self._model_training_state.update(status="running",
                                    epoch=progress["epoch"], progress=progress)
                        result = train_experiment(config_snapshot, arrays, output_dir, on_progress)
                        finished_at = __import__("datetime").datetime.now().astimezone().isoformat(timespec="seconds")
                        current = self.get_model_experiments().get("experiments", [])
                        prior = next((x for x in current if x.get("experiment_id") == experiment_id), {})
                        runs = list(prior.get("runs", []))
                        runs.append({"run_number": len(runs) + 1, "finished_at": finished_at, "training_result": result})
                        self._update_model_record(experiment_id, {"status": "trained", "training_result": result, "runs": runs, "error": None})
                        with self._model_training_lock:
                            self._model_training_state.update(status="completed", result=result,
                                epoch=result["epochs_completed"], error=None)
                    except Exception as exc:
                        try:
                            self._update_model_record(experiment_id, {"status": "error", "error": str(exc)})
                        except Exception:
                            pass
                        with self._model_training_lock:
                            self._model_training_state.update(status="error", error=str(exc))
                self._model_training_thread = threading.Thread(
                    target=worker, name="SismoAI-ModelTraining", daemon=True)
                self._model_training_thread.start()
                return {"success": True, "experiment_id": experiment_id, "status": "preparing"}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def _update_model_record(self, experiment_id: str, changes: dict) -> None:
        """Update one experiment atomically; never replace a corrupt registry with an empty one."""
        lock = getattr(self, "_model_registry_lock", None)
        if lock is None:
            import threading
            self._model_registry_lock = threading.RLock()
            lock = self._model_registry_lock
        with lock:
            result = self.get_model_experiments()
            if not result.get("success"):
                raise ValueError("No se pudo leer el registro de experimentos: " + result.get("error", "error desconocido"))
            registry = result.get("experiments", [])
            found = False
            for item in registry:
                if item.get("experiment_id") == experiment_id:
                    item.update(changes)
                    found = True
                    break
            if not found:
                raise ValueError("Experimento no encontrado en el registro: " + str(experiment_id))
            path = self._models_registry_path()
            os.makedirs(os.path.dirname(path), exist_ok=True)
            temp = path + ".tmp"
            with open(temp, "w", encoding="utf-8") as stream:
                json.dump(registry, stream, ensure_ascii=False, indent=2, allow_nan=False)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp, path)

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
            duration = max(geo_times[-1] if geo_times else 0.0,
                           mpu_times[-1] if mpu_times else 0.0)
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
        """Return windows belonging to the currently selected source event."""
        context = self.get_window_context()
        if not context.get("ready"):
            return []
        file_name = context.get("file_name")
        event_id = str(context.get("event_index", -1))
        return [
            item.to_dict() for item in self._window_records
            if item.source_file == file_name
            and str(item.source_event_id) == event_id
        ]

    def clear_windows(self) -> dict:
        self._window_records = []
        self._window_sequence = 0
        try:
            self._persist_windows()
            return {"success": True}
        except Exception as exc:
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

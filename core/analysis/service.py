"""Analysis service: event context, selection, and UI states (no Qt).

This module provides the analysis workflow for the web UI. It loads
validated event context from Data and exposes signal plots and scientific
calculations. All Qt dependencies have been removed; threading is handled
via Python's standard library.
"""

import bisect
import math
import os
import threading
from dataclasses import dataclass
from typing import Callable, List, Optional

from dataengine import parse_file
from dataengine import layout as L
from dataengine.analysis import analyze_event, check_magnitude
from dataengine.series import (
    CHANNEL_MAGNITUDE, CHANNEL_VELOCITY, event_series,
)

from .models import (
    AnalysisFile, AnalysisFileListModel, StaltaCandidateListModel,
    StaltaCandidateRow,
)
from .signal_metrics import SignalMetrics, calculate_signal_metrics
from .spectrogram import (
    OVERLAPS as SPECTROGRAM_OVERLAPS,
    RANGES_HZ as SPECTROGRAM_RANGES,
    WINDOW_SECONDS as SPECTROGRAM_WINDOW_SECONDS,
    SpectrogramResult,
    calculate_spectrogram,
)
from .spectrum import SpectrumResult, calculate_spectrum
from .stalta import StaltaResult, calculate_stalta

#: Frequency ranges offered by the spectrum view, in Hz.
#: ``None`` renders each sensor up to its own Nyquist limit.
SPECTRUM_RANGES = (20.0, 40.0, None)

#: Window functions offered by the spectrum view.
SPECTRUM_WINDOWS = ("hann", "hamming", "rectangular")


@dataclass(frozen=True)
class _SelectedEvent:
    original_number: int
    total_events: int
    sequence: int
    start_us: int
    end_us: int
    sample_count: int
    geophone_samples: int
    mpu_samples: int
    geophone_hz: float
    mpu_hz: float


class AnalysisService:
    """Selected valid BIN/event context exposed to the web UI."""

    EMPTY = "empty"
    LOADING = "loading"
    READY = "ready"
    UNAVAILABLE = "unavailable"
    ERROR = "error"

    def __init__(self, data_service):
        self._data = data_service
        self._file_model = AnalysisFileListModel()
        self._stalta_candidate_model = StaltaCandidateListModel()
        self._state = self.EMPTY
        self._error = ""
        self._selected_path = ""
        self._file_result = None
        self._events = []
        self._selected_index = -1
        self._origin_us = None
        self._request_id = 0
        self._loading_path = ""
        self._tasks = {}
        self._lock = threading.Lock()
        self._changed_callbacks: List[Callable] = []
        self._cursor_changed_callbacks: List[Callable] = []
        self._viewport_changed_callbacks: List[Callable] = []
        self._data_changed_callbacks: List[Callable] = []
        self._geophone_times = []
        self._geophone_values = []
        self._geophone_breaks = []
        self._geophone_sequences = []
        self._mpu_times = []
        self._mpu_values = []
        self._mpu_breaks = []
        self._mpu_sequences = []
        self._plot_x_minimum = 0.0
        self._plot_x_maximum = 1.0
        self._view_x_minimum = 0.0
        self._view_x_maximum = 1.0
        self._geophone_full_y_minimum = -1.0
        self._geophone_full_y_maximum = 1.0
        self._mpu_full_y_minimum = -1.0
        self._mpu_full_y_maximum = 1.0
        self._geophone_view_y_minimum = -1.0
        self._geophone_view_y_maximum = 1.0
        self._mpu_view_y_minimum = -1.0
        self._mpu_view_y_maximum = 1.0
        self._cursor_time = -1.0
        self._geophone_cursor_text = "Mueve el cursor sobre una señal para inspeccionar muestras."
        self._mpu_cursor_text = "Mueve el cursor sobre una señal para inspeccionar muestras."
        self._geophone_stalta_cursor_text = self._geophone_cursor_text
        self._mpu_stalta_cursor_text = self._mpu_cursor_text
        self._metric_sensor = "geophone"
        self._active_submenu = "senales"
        self._activated = False
        self._metrics = {"geophone": None, "mpu": None}
        self._sta_window_seconds = 0.5
        self._lta_window_seconds = 5.0
        self._stalta_activation_threshold = 3.0
        self._stalta_deactivation_threshold = 1.5
        self._stalta_method = "absolute"
        self._geophone_stalta = self._empty_stalta()
        self._mpu_stalta = self._empty_stalta()
        self._spectrum_window = "hann"
        self._spectrum_range_hz = 40.0
        self._geophone_spectrum = self._empty_spectrum()
        self._mpu_spectrum = self._empty_spectrum()
        self._spectrum_cursor_freq = -1.0
        self._geophone_spectrum_cursor_text = (
            "Mueve el cursor sobre un espectro para inspeccionar bins.")
        self._mpu_spectrum_cursor_text = self._geophone_spectrum_cursor_text
        self._spectrogram_window = "hann"
        self._spectrogram_duration_seconds = 1.0
        self._spectrogram_overlap = 0.5
        self._spectrogram_range_hz = 40.0
        self._geophone_spectrogram = self._empty_spectrogram()
        self._mpu_spectrogram = self._empty_spectrogram()
        self._spectrogram_cursor_time = -1.0
        self._spectrogram_cursor_freq = -1.0
        self._geophone_spectrogram_cursor_text = (
            "Mueve el cursor sobre un espectrograma para inspeccionar celdas.")
        self._mpu_spectrogram_cursor_text = (
            self._geophone_spectrogram_cursor_text)
        self._data_changed()

    # -- Callback registration -------------------------------------------

    def add_changed_callback(self, callback: Callable):
        self._changed_callbacks.append(callback)

    def add_cursor_changed_callback(self, callback: Callable):
        self._cursor_changed_callbacks.append(callback)

    def add_viewport_changed_callback(self, callback: Callable):
        self._viewport_changed_callbacks.append(callback)

    def add_data_changed_callback(self, callback: Callable):
        self._data_changed_callbacks.append(callback)

    # -- Signal emission (replaces pyqtSignal) ---------------------------

    def _emit_changed(self):
        for callback in self._changed_callbacks:
            callback()

    def _emit_cursor_changed(self):
        for callback in self._cursor_changed_callbacks:
            callback()

    def _emit_viewport_changed(self):
        for callback in self._viewport_changed_callbacks:
            callback()

    def _emit_data_changed(self):
        for callback in self._data_changed_callbacks:
            callback()

    # -- Static helpers ---------------------------------------------------

    @staticmethod
    def _empty_stalta():
        return StaltaResult([], [], [], [], None, None, None, 0, 0)

    @staticmethod
    def _empty_spectrum():
        return SpectrumResult([], [], 0.0, "hann", 0, 0.0, None,
                               None, None, None, None, None, None, None)

    @staticmethod
    def _empty_spectrogram():
        return SpectrogramResult()

    # -- Public properties (replaces pyqtProperty) ------------------------

    @property
    def file_model(self):
        return self._file_model

    @property
    def stalta_candidate_model(self):
        return self._stalta_candidate_model

    @property
    def state(self):
        return self._state

    @property
    def loading(self):
        return self._state == self.LOADING

    @property
    def state_text(self):
        if self._state == self.LOADING:
            return "Cargando eventos BIN validados…"
        if self._state == self.READY:
            return "Señales temporales del evento validadas y listas."
        if self._state == self.UNAVAILABLE:
            return "No hay eventos válidos disponibles para Análisis."
        if self._state == self.ERROR:
            return self._error or "No se pudo cargar el evento."
        return "Selecciona un archivo BIN válido desde Datos para comenzar."

    @property
    def error_text(self):
        return self._error

    @property
    def has_selection(self):
        return self._selected_event() is not None

    @property
    def selected_file_index(self):
        return self._file_model.index_of_path(self._selected_path)

    @property
    def selected_file_path(self):
        return self._selected_path

    @property
    def selected_file_name(self):
        return os.path.basename(self._selected_path) if self._selected_path else "—"

    @property
    def event_counter_text(self):
        event = self._selected_event()
        if event is None:
            return "— / —"
        return "%03d / %03d" % (event.original_number, event.total_events)

    @property
    def can_select_previous_event(self):
        return self._selected_index > 0

    @property
    def can_select_next_event(self):
        return 0 <= self._selected_index < len(self._events) - 1

    @property
    def event_sequence_text(self):
        event = self._selected_event()
        return str(event.sequence) if event is not None else "—"

    @property
    def event_start_text(self):
        event = self._selected_event()
        if event is None or self._origin_us is None:
            return "—"
        return self._seconds_text((event.start_us - self._origin_us) / 1_000_000.0)

    @property
    def event_end_text(self):
        event = self._selected_event()
        if event is None or self._origin_us is None:
            return "—"
        return self._seconds_text((event.end_us - self._origin_us) / 1_000_000.0)

    @property
    def event_duration_text(self):
        event = self._selected_event()
        if event is None or event.end_us < event.start_us:
            return "—"
        return self._seconds_text((event.end_us - event.start_us) / 1_000_000.0)

    @property
    def event_sample_count_text(self):
        event = self._selected_event()
        return str(event.sample_count) if event is not None else "—"

    @property
    def geophone_sample_count_text(self):
        event = self._selected_event()
        return str(event.geophone_samples) if event is not None else "—"

    @property
    def mpu_sample_count_text(self):
        event = self._selected_event()
        return str(event.mpu_samples) if event is not None else "—"

    @property
    def geophone_frequency_text(self):
        event = self._selected_event()
        return self._frequency_text(event.geophone_hz) if event is not None else "—"

    @property
    def mpu_frequency_text(self):
        event = self._selected_event()
        return self._frequency_text(event.mpu_hz) if event is not None else "—"

    @property
    def geophone_times(self):
        return list(self._geophone_times)

    @property
    def geophone_values(self):
        return list(self._geophone_values)

    @property
    def geophone_breaks(self):
        return list(self._geophone_breaks)

    @property
    def mpu_times(self):
        return list(self._mpu_times)

    @property
    def mpu_values(self):
        return list(self._mpu_values)

    @property
    def mpu_breaks(self):
        return list(self._mpu_breaks)

    @property
    def plot_x_minimum(self):
        return self._plot_x_minimum

    @property
    def plot_x_maximum(self):
        return self._plot_x_maximum

    @property
    def view_x_minimum(self):
        return self._view_x_minimum

    @property
    def view_x_maximum(self):
        return self._view_x_maximum

    @property
    def geophone_view_y_minimum(self):
        return self._geophone_view_y_minimum

    @property
    def geophone_view_y_maximum(self):
        return self._geophone_view_y_maximum

    @property
    def mpu_view_y_minimum(self):
        return self._mpu_view_y_minimum

    @property
    def mpu_view_y_maximum(self):
        return self._mpu_view_y_maximum

    @property
    def cursor_time(self):
        return self._cursor_time

    @property
    def geophone_cursor_text(self):
        return self._geophone_cursor_text

    @property
    def mpu_cursor_text(self):
        return self._mpu_cursor_text

    @property
    def geophone_stalta_cursor_text(self):
        return self._geophone_stalta_cursor_text

    @property
    def mpu_stalta_cursor_text(self):
        return self._mpu_stalta_cursor_text

    @property
    def selected_metric_sensor(self):
        return self._metric_sensor

    @property
    def active_submenu(self):
        return self._active_submenu

    @property
    def active_submenu_title(self):
        return {
            "senales": "Señales",
            "espectrograma": "Espectrograma",
            "frecuencia": "Frecuencia",
            "sta_lta": "STA-LTA",
        }[self._active_submenu]

    @property
    def active_submenu_implemented(self):
        return self._active_submenu in ("senales", "sta_lta", "frecuencia",
                                        "espectrograma")

    @property
    def sta_window_text(self):
        return self._parameter_number_text(self._sta_window_seconds)

    @property
    def lta_window_text(self):
        return self._parameter_number_text(self._lta_window_seconds)

    @property
    def activation_threshold_text(self):
        return self._parameter_number_text(self._stalta_activation_threshold)

    @property
    def deactivation_threshold_text(self):
        return self._parameter_number_text(self._stalta_deactivation_threshold)

    @staticmethod
    def _parameter_number_text(value):
        return ("%.3f" % value).rstrip("0").rstrip(".")

    @property
    def stalta_method_id(self):
        return self._stalta_method

    @property
    def stalta_method_text(self):
        return ("Amplitud absoluta" if self._stalta_method == "absolute"
                else "Energía (RMS)")

    @property
    def stalta_activation_value(self):
        return self._stalta_activation_threshold

    @property
    def stalta_deactivation_value(self):
        return self._stalta_deactivation_threshold

    @property
    def geophone_sta_values(self):
        return list(self._geophone_stalta.sta)

    @property
    def geophone_lta_values(self):
        return list(self._geophone_stalta.lta)

    @property
    def geophone_ratio_values(self):
        return list(self._geophone_stalta.ratio)

    @property
    def mpu_sta_values(self):
        return list(self._mpu_stalta.sta)

    @property
    def mpu_lta_values(self):
        return list(self._mpu_stalta.lta)

    @property
    def mpu_ratio_values(self):
        return list(self._mpu_stalta.ratio)

    @property
    def geophone_ratio_maximum(self):
        return self._ratio_axis_maximum(self._geophone_stalta)

    @property
    def mpu_ratio_maximum(self):
        return self._ratio_axis_maximum(self._mpu_stalta)

    @property
    def geophone_ratio_peak_text(self):
        return self._ratio_peak_text(self._geophone_stalta)

    @property
    def mpu_ratio_peak_text(self):
        return self._ratio_peak_text(self._mpu_stalta)

    @property
    def geophone_ratio_peak_time_text(self):
        return self._ratio_peak_time_text(self._geophone_stalta)

    @property
    def mpu_ratio_peak_time_text(self):
        return self._ratio_peak_time_text(self._mpu_stalta)

    @property
    def geophone_mean_lta_text(self):
        return self._mean_lta_text(self._geophone_stalta, "mm/s")

    @property
    def mpu_mean_lta_text(self):
        return self._mean_lta_text(self._mpu_stalta, "m/s²")

    @property
    def geophone_candidate_count_text(self):
        return str(len(self._geophone_stalta.candidates))

    @property
    def mpu_candidate_count_text(self):
        return str(len(self._mpu_stalta.candidates))

    @property
    def stalta_candidate_count(self):
        return len(self._stalta_candidate_model)

    @staticmethod
    def _ratio_axis_maximum(result):
        finite = [value for value in result.ratio if math.isfinite(value)]
        return max(1.0, math.ceil(max(finite) / 5.0) * 5.0) if finite else 1.0

    @staticmethod
    def _ratio_peak_text(result):
        return "%.2f" % result.peak_ratio if result.peak_ratio is not None else "No disponible"

    @staticmethod
    def _ratio_peak_time_text(result):
        return "%.3f s" % result.peak_seconds if result.peak_seconds is not None else "No disponible"

    @staticmethod
    def _mean_lta_text(result, unit):
        return "%.4g %s" % (result.mean_lta, unit) if result.mean_lta is not None else "No disponible"

    def _selected_spectrum(self):
        return (self._geophone_spectrum if self._metric_sensor == "geophone"
                else self._mpu_spectrum)

    def _selected_spectrum_unit(self):
        return "mm/s" if self._metric_sensor == "geophone" else "m/s²"

    @staticmethod
    def _spectrum_hz_text(value):
        return "%.2f Hz" % value if value is not None else "No disponible"

    @property
    def geophone_spectrum_freqs(self):
        return list(self._geophone_spectrum.freqs)

    @property
    def geophone_spectrum_amps(self):
        return list(self._geophone_spectrum.amps)

    @property
    def mpu_spectrum_freqs(self):
        return list(self._mpu_spectrum.freqs)

    @property
    def mpu_spectrum_amps(self):
        return list(self._mpu_spectrum.amps)

    @property
    def geophone_spectrum_x_max(self):
        return self._spectrum_x_max(self._geophone_spectrum)

    @property
    def mpu_spectrum_x_max(self):
        return self._spectrum_x_max(self._mpu_spectrum)

    @staticmethod
    def _spectrum_x_max(result):
        if result.freqs:
            return result.freqs[-1]
        if result.sample_rate_hz > 0:
            return result.sample_rate_hz / 2.0
        return 1.0

    @property
    def geophone_spectrum_y_max(self):
        return self._spectrum_y_max(self._geophone_spectrum)

    @property
    def mpu_spectrum_y_max(self):
        return self._spectrum_y_max(self._mpu_spectrum)

    @staticmethod
    def _spectrum_y_max(result):
        finite = [value for value in result.amps if math.isfinite(value)]
        if not finite:
            return 1.0
        return max(finite) * 1.1 or 1.0

    @property
    def spectrum_cursor_freq(self):
        return self._spectrum_cursor_freq

    @property
    def geophone_spectrum_cursor_text(self):
        return self._geophone_spectrum_cursor_text

    @property
    def mpu_spectrum_cursor_text(self):
        return self._mpu_spectrum_cursor_text

    @property
    def spectrum_window_id(self):
        return self._spectrum_window

    @property
    def spectrum_window_text(self):
        return {"hann": "Hann", "hamming": "Hamming",
                "rectangular": "Rectangular"}.get(self._spectrum_window,
                                                  self._spectrum_window)

    @property
    def spectrum_range_hz(self):
        return self._spectrum_range_hz if self._spectrum_range_hz else -1.0

    @property
    def spectrum_range_text(self):
        if not self._spectrum_range_hz:
            return "Nyquist"
        return "0 – %d Hz" % int(self._spectrum_range_hz)

    @property
    def spectral_dominant_frequency_text(self):
        return self._spectrum_hz_text(
            self._selected_spectrum().dominant_freq_hz)

    @property
    def spectral_dominant_amplitude_text(self):
        result = self._selected_spectrum()
        if result.dominant_amp is None:
            return "No disponible"
        return "%.4g %s" % (result.dominant_amp,
                            self._selected_spectrum_unit())

    @property
    def spectral_centroid_text(self):
        return self._spectrum_hz_text(
            self._selected_spectrum().centroid_freq_hz)

    @property
    def spectral_bandwidth_text(self):
        value = self._selected_spectrum().bandwidth_3db_hz
        if value is None:
            return "No disponible (límite de rango)"
        return "%.2f Hz" % value

    @property
    def spectral_energy_text(self):
        result = self._selected_spectrum()
        if result.energy_in_range is None:
            return "No disponible"
        return "%.4g %s²" % (result.energy_in_range,
                             self._selected_spectrum_unit())

    @property
    def spectral_secondary_peak_text(self):
        result = self._selected_spectrum()
        if result.secondary_freq_hz is None:
            return "No disponible"
        return "%.2f Hz (%.3g %s)" % (
            result.secondary_freq_hz, result.secondary_amp,
            self._selected_spectrum_unit())

    @property
    def spectral_resolution_text(self):
        result = self._selected_spectrum()
        if result.freq_resolution_hz <= 0 or result.window_samples <= 0:
            return "No disponible"
        return "Δf = %.3f Hz · N = %d · %s" % (
            result.freq_resolution_hz, result.window_samples,
            {"hann": "Hann", "hamming": "Hamming",
             "rectangular": "Rectangular"}.get(result.window_id,
                                               result.window_id))

    def set_spectrum_window(self, window_id):
        if window_id not in SPECTRUM_WINDOWS or window_id == self._spectrum_window:
            return
        self._spectrum_window = window_id
        self._calculate_spectrum_for_selected_event()
        self._emit_changed()

    def set_spectrum_range_hz(self, range_hz):
        value = float(range_hz)
        if value <= 0:
            target = None
        elif value in SPECTRUM_RANGES and value is not None:
            target = value
        else:
            return
        if target == self._spectrum_range_hz:
            return
        self._spectrum_range_hz = target
        self._calculate_spectrum_for_selected_event()
        self._emit_changed()

    def _selected_spectrogram(self):
        return (self._geophone_spectrogram
                if self._metric_sensor == "geophone"
                else self._mpu_spectrogram)

    def _selected_spectrogram_unit(self):
        return "mm/s" if self._metric_sensor == "geophone" else "m/s²"

    @staticmethod
    def _spectrogram_time_bounds(result):
        if result.frame_starts and result.frame_ends:
            return result.frame_starts[0], result.frame_ends[-1]
        return None

    @property
    def geophone_spectrogram_times(self):
        return list(self._geophone_spectrogram.times)

    @property
    def geophone_spectrogram_freqs(self):
        return list(self._geophone_spectrogram.freqs)

    @property
    def geophone_spectrogram_amps(self):
        return list(self._geophone_spectrogram.amps)

    @property
    def mpu_spectrogram_times(self):
        return list(self._mpu_spectrogram.times)

    @property
    def mpu_spectrogram_freqs(self):
        return list(self._mpu_spectrogram.freqs)

    @property
    def mpu_spectrogram_amps(self):
        return list(self._mpu_spectrogram.amps)

    @property
    def geophone_spectrogram_frame_count(self):
        return self._geophone_spectrogram.frame_count

    @property
    def geophone_spectrogram_bin_count(self):
        return self._geophone_spectrogram.bin_count

    @property
    def mpu_spectrogram_frame_count(self):
        return self._mpu_spectrogram.frame_count

    @property
    def mpu_spectrogram_bin_count(self):
        return self._mpu_spectrogram.bin_count

    @property
    def geophone_spectrogram_x_minimum(self):
        bounds = self._spectrogram_time_bounds(self._geophone_spectrogram)
        return bounds[0] if bounds else self._plot_x_minimum

    @property
    def geophone_spectrogram_x_maximum(self):
        bounds = self._spectrogram_time_bounds(self._geophone_spectrogram)
        return bounds[1] if bounds else self._plot_x_maximum

    @property
    def mpu_spectrogram_x_minimum(self):
        bounds = self._spectrogram_time_bounds(self._mpu_spectrogram)
        return bounds[0] if bounds else self._plot_x_minimum

    @property
    def mpu_spectrogram_x_maximum(self):
        bounds = self._spectrogram_time_bounds(self._mpu_spectrogram)
        return bounds[1] if bounds else self._plot_x_maximum

    @property
    def geophone_spectrogram_freq_maximum(self):
        result = self._geophone_spectrogram
        if result.freqs:
            return result.freqs[-1]
        if result.sample_rate_hz > 0:
            return result.sample_rate_hz / 2.0
        return 1.0

    @property
    def mpu_spectrogram_freq_maximum(self):
        result = self._mpu_spectrogram
        if result.freqs:
            return result.freqs[-1]
        if result.sample_rate_hz > 0:
            return result.sample_rate_hz / 2.0
        return 1.0

    @property
    def geophone_spectrogram_max_amp(self):
        return self._geophone_spectrogram.peak_amp or 0.0

    @property
    def mpu_spectrogram_max_amp(self):
        return self._mpu_spectrogram.peak_amp or 0.0

    @property
    def spectrogram_cursor_time(self):
        return self._spectrogram_cursor_time

    @property
    def spectrogram_cursor_freq(self):
        return self._spectrogram_cursor_freq

    @property
    def geophone_spectrogram_cursor_text(self):
        return self._geophone_spectrogram_cursor_text

    @property
    def mpu_spectrogram_cursor_text(self):
        return self._mpu_spectrogram_cursor_text

    @property
    def spectrogram_window_id(self):
        return self._spectrogram_window

    @property
    def spectrogram_window_text(self):
        return {"hann": "Hann", "hamming": "Hamming",
                "rectangular": "Rectangular"}.get(self._spectrogram_window,
                                                  self._spectrogram_window)

    @property
    def spectrogram_duration_seconds(self):
        return self._spectrogram_duration_seconds

    @property
    def spectrogram_duration_text(self):
        return "%.1f s" % self._spectrogram_duration_seconds

    @property
    def spectrogram_overlap(self):
        return self._spectrogram_overlap

    @property
    def spectrogram_overlap_text(self):
        return "%d%%" % int(round(self._spectrogram_overlap * 100.0))

    @property
    def spectrogram_range_hz(self):
        return self._spectrogram_range_hz if self._spectrogram_range_hz else -1.0

    @property
    def spectrogram_range_text(self):
        if not self._spectrogram_range_hz:
            return "Nyquist"
        return "0 – %d Hz" % int(self._spectrogram_range_hz)

    @property
    def spectrogram_resolution_text(self):
        result = self._selected_spectrogram()
        if result.window_samples <= 0 or result.frame_count <= 0:
            return "No disponible"
        return ("Δf = %.3f Hz · Δt = %.3f s · N = %d · %s · %d ventanas"
                % (result.freq_resolution_hz, result.time_step_s,
                   result.window_samples,
                   {"hann": "Hann", "hamming": "Hamming",
                    "rectangular": "Rectangular"}.get(result.window_id,
                                                      result.window_id),
                   result.frame_count))

    @property
    def spectrogram_peak_energy_text(self):
        result = self._selected_spectrogram()
        if (result.peak_energy_start is None
                or result.peak_energy_end is None):
            return "No disponible"
        return "%.3f – %.3f s" % (result.peak_energy_start,
                                  result.peak_energy_end)

    @property
    def spectrogram_dominant_band_text(self):
        result = self._selected_spectrogram()
        if (result.dominant_band_lo is None
                or result.dominant_band_hi is None):
            return "No disponible"
        return "%.1f – %.1f Hz" % (result.dominant_band_lo,
                                   result.dominant_band_hi)

    @property
    def spectrogram_change_text(self):
        result = self._selected_spectrogram()
        if result.change_label is None:
            if (self._selected_event() is not None
                    and result.frame_count <= 1):
                return "No disponible (una sola ventana)"
            return "No disponible"
        return result.change_label

    def set_spectrogram_window(self, window_id):
        if (window_id not in SPECTRUM_WINDOWS
                or window_id == self._spectrogram_window):
            return
        self._spectrogram_window = window_id
        self._calculate_spectrogram_for_selected_event()
        self._emit_changed()

    def set_spectrogram_duration(self, seconds):
        value = float(seconds)
        if value not in SPECTROGRAM_WINDOW_SECONDS:
            return
        if value == self._spectrogram_duration_seconds:
            return
        self._spectrogram_duration_seconds = value
        self._calculate_spectrogram_for_selected_event()
        self._emit_changed()

    def set_spectrogram_overlap(self, overlap):
        value = float(overlap)
        if value not in SPECTROGRAM_OVERLAPS:
            return
        if value == self._spectrogram_overlap:
            return
        self._spectrogram_overlap = value
        self._calculate_spectrogram_for_selected_event()
        self._emit_changed()

    def set_spectrogram_range_hz(self, range_hz):
        value = float(range_hz)
        if value <= 0:
            target = None
        elif value in SPECTRUM_RANGES and value is not None:
            target = value
        else:
            return
        if target == self._spectrogram_range_hz:
            return
        self._spectrogram_range_hz = target
        self._calculate_spectrogram_for_selected_event()
        self._emit_changed()

    def set_spectrogram_cursor(self, time_seconds, frequency_hz):
        time_value = float(time_seconds)
        freq_value = float(frequency_hz)
        if (not math.isfinite(time_value) or not math.isfinite(freq_value)
                or freq_value < 0):
            return
        if (abs(self._spectrogram_cursor_time - time_value) < 1e-9
                and abs(self._spectrogram_cursor_freq - freq_value) < 1e-9):
            return
        self._spectrogram_cursor_time = time_value
        self._spectrogram_cursor_freq = freq_value
        self._update_spectrogram_cursor_texts()
        self._emit_cursor_changed()

    def clear_spectrogram_cursor(self):
        if self._spectrogram_cursor_time < 0 and self._spectrogram_cursor_freq < 0:
            return
        self._spectrogram_cursor_time = -1.0
        self._spectrogram_cursor_freq = -1.0
        self._update_spectrogram_cursor_texts()
        self._emit_cursor_changed()

    def _update_spectrogram_cursor_text(self, result, unit):
        if (self._spectrogram_cursor_time < 0
                or self._spectrogram_cursor_freq < 0
                or not result.times or not result.freqs
                or not result.amps):
            return ("Mueve el cursor sobre un espectrograma para "
                    "inspeccionar celdas.")
        frame = min(range(result.frame_count),
                    key=lambda i: abs(result.times[i]
                                      - self._spectrogram_cursor_time))
        nearby = min(range(result.bin_count),
                     key=lambda j: abs(result.freqs[j]
                                       - self._spectrogram_cursor_freq))
        amp = result.amps[frame * result.bin_count + nearby]
        peak = result.peak_amp or 0.0
        intensity = (100.0 * amp / peak) if peak > 0 else 0.0
        return ("t = %.3f s   f = %.2f Hz   Amplitud = %.4g %s (%d%%)"
                % (result.times[frame], result.freqs[nearby], amp, unit,
                   int(round(intensity))))

    def _update_spectrogram_cursor_texts(self):
        self._geophone_spectrogram_cursor_text = (
            self._update_spectrogram_cursor_text(self._geophone_spectrogram,
                                                "mm/s"))
        self._mpu_spectrogram_cursor_text = (
            self._update_spectrogram_cursor_text(self._mpu_spectrogram,
                                                "m/s²"))

    def _calculate_spectrogram_for_selected_event(self):
        # Short events yield tens of frames at most; numpy completes in
        # milliseconds, so no worker round-trip is needed here.
        selected = self._selected_event()
        if selected is None:
            self._geophone_spectrogram = self._empty_spectrogram()
            self._mpu_spectrogram = self._empty_spectrogram()
            return
        _, context = self._events[self._selected_index]
        self._geophone_spectrogram = calculate_spectrogram(
            self._geophone_times,
            self._geophone_values,
            self._geophone_sequences,
            self._geophone_breaks,
            context.geophone_hz,
            self._spectrogram_window,
            self._spectrogram_duration_seconds,
            self._spectrogram_overlap,
            self._spectrogram_range_hz,
        )
        self._mpu_spectrogram = calculate_spectrogram(
            self._mpu_times,
            self._mpu_values,
            self._mpu_sequences,
            self._mpu_breaks,
            context.mpu_hz,
            self._spectrogram_window,
            self._spectrogram_duration_seconds,
            self._spectrogram_overlap,
            self._spectrogram_range_hz,
        )

    @property
    def dominant_frequency_text(self):
        value = self._selected_spectrum().dominant_freq_hz
        if value is None:
            return "Se calcula en el submenú Frecuencia"
        return "%.2f Hz" % value

    @property
    def maximum_amplitude_text(self):
        metrics = self._selected_metrics()
        event = self._selected_event()
        if metrics is None or metrics.peak_amplitude is None or event is None:
            return "No disponible"
        unit = "mm/s" if self._metric_sensor == "geophone" else "m/s²"
        return "%.4g %s" % (metrics.peak_amplitude, unit)

    @property
    def rms_text(self):
        metrics = self._selected_metrics()
        event = self._selected_event()
        if metrics is None or metrics.rms is None or event is None:
            return "No disponible"
        unit = "mm/s" if self._metric_sensor == "geophone" else "m/s²"
        return "%.4g %s" % (metrics.rms, unit)

    @property
    def snr_text(self):
        metrics = self._selected_metrics()
        if metrics is None or metrics.snr_db is None:
            return "No disponible: falta referencia pre-evento"
        return "%.2f dB (estimado)" % metrics.snr_db

    @property
    def jitter_text(self):
        metrics = self._selected_metrics()
        if metrics is None or metrics.jitter_ms is None:
            return "No disponible"
        return "%.4g ms" % metrics.jitter_ms

    @property
    def saturated_samples_text(self):
        return "No definido en BIN v2"

    @property
    def signal_findings_text(self):
        metrics = self._selected_metrics()
        return metrics.findings_text if metrics is not None else "—"

    def _selected_metrics(self):
        return self._metrics.get(self._metric_sensor)

    def _selected_event(self):
        if self._state != self.READY or not 0 <= self._selected_index < len(self._events):
            return None
        return self._events[self._selected_index][1]

    @staticmethod
    def _seconds_text(seconds):
        return "%.3f s" % seconds

    @staticmethod
    def _frequency_text(value):
        return "%.2f Hz" % value if value > 0 else "—"

    def _set_empty_context(self, state, error=""):
        self._request_id += 1
        self._loading_path = ""
        self._selected_path = ""
        self._file_result = None
        self._events = []
        self._selected_index = -1
        self._origin_us = None
        self._clear_signal_data()
        self._error = error
        self._state = state
        self._emit_changed()

    def _clear_signal_data(self):
        self._geophone_times = []
        self._geophone_values = []
        self._geophone_breaks = []
        self._geophone_sequences = []
        self._mpu_times = []
        self._mpu_values = []
        self._mpu_breaks = []
        self._mpu_sequences = []
        self._plot_x_minimum = 0.0
        self._plot_x_maximum = 1.0
        self._view_x_minimum = 0.0
        self._view_x_maximum = 1.0
        self._geophone_full_y_minimum = -1.0
        self._geophone_full_y_maximum = 1.0
        self._mpu_full_y_minimum = -1.0
        self._mpu_full_y_maximum = 1.0
        self._geophone_view_y_minimum = -1.0
        self._geophone_view_y_maximum = 1.0
        self._mpu_view_y_minimum = -1.0
        self._mpu_view_y_maximum = 1.0
        self._cursor_time = -1.0
        self._geophone_cursor_text = "Mueve el cursor sobre una señal para inspeccionar muestras."
        self._mpu_cursor_text = "Mueve el cursor sobre una señal para inspeccionar muestras."
        self._geophone_stalta_cursor_text = self._geophone_cursor_text
        self._mpu_stalta_cursor_text = self._mpu_cursor_text
        self._metrics = {"geophone": None, "mpu": None}
        self._geophone_stalta = self._empty_stalta()
        self._mpu_stalta = self._empty_stalta()
        self._geophone_spectrum = self._empty_spectrum()
        self._mpu_spectrum = self._empty_spectrum()
        self._spectrum_cursor_freq = -1.0
        self._geophone_spectrum_cursor_text = (
            "Mueve el cursor sobre un espectro para inspeccionar bins.")
        self._mpu_spectrum_cursor_text = self._geophone_spectrum_cursor_text
        self._geophone_spectrogram = self._empty_spectrogram()
        self._mpu_spectrogram = self._empty_spectrogram()
        self._spectrogram_cursor_time = -1.0
        self._spectrogram_cursor_freq = -1.0
        self._geophone_spectrogram_cursor_text = (
            "Mueve el cursor sobre un espectrograma para inspeccionar celdas.")
        self._mpu_spectrogram_cursor_text = (
            self._geophone_spectrogram_cursor_text)
        self._stalta_candidate_model.set_rows([])
        self._emit_cursor_changed()
        self._emit_viewport_changed()

    @staticmethod
    def _padded_y_range(values):
        finite = [float(value) for value in values if math.isfinite(float(value))]
        if not finite:
            return -1.0, 1.0
        low = min(0.0, min(finite))
        high = max(0.0, max(finite))
        span = high - low
        if span <= 0:
            span = max(abs(high), 1.0)
        padding = span * 0.08
        return low - padding, high + padding

    @staticmethod
    def _bounded_range(minimum, maximum, full_minimum, full_maximum):
        full_span = max(full_maximum - full_minimum, 1e-9)
        span = min(maximum - minimum, full_span)
        if span >= full_span:
            return full_minimum, full_maximum
        minimum = min(max(minimum, full_minimum), full_maximum - span)
        return minimum, minimum + span

    def zoom_time(self, factor, anchor_ratio):
        """Zoom the common time axis around the pointer's horizontal position."""
        if not math.isfinite(factor) or factor <= 0:
            return
        full_span = self._plot_x_maximum - self._plot_x_minimum
        current_span = self._view_x_maximum - self._view_x_minimum
        if full_span <= 0 or current_span <= 0:
            return
        ratio = min(max(float(anchor_ratio), 0.0), 1.0)
        minimum_span = min(full_span, max(0.01, full_span / 10000.0))
        new_span = min(max(current_span * float(factor), minimum_span), full_span)
        anchor = self._view_x_minimum + ratio * current_span
        new_minimum = anchor - ratio * new_span
        new_maximum = new_minimum + new_span
        self._view_x_minimum, self._view_x_maximum = self._bounded_range(
            new_minimum, new_maximum, self._plot_x_minimum, self._plot_x_maximum)
        self._emit_viewport_changed()

    def pan_viewport(self, sensor, horizontal_fraction, vertical_fraction):
        """Pan common time and the dragged sensor's independent amplitude axis."""
        if sensor not in ("geophone", "mpu"):
            return
        changed = False
        x_span = self._view_x_maximum - self._view_x_minimum
        if x_span > 0 and math.isfinite(horizontal_fraction):
            new_minimum = self._view_x_minimum - float(horizontal_fraction) * x_span
            new_maximum = new_minimum + x_span
            bounded = self._bounded_range(
                new_minimum, new_maximum,
                self._plot_x_minimum, self._plot_x_maximum)
            if bounded != (self._view_x_minimum, self._view_x_maximum):
                self._view_x_minimum, self._view_x_maximum = bounded
                changed = True

        y_min_attr = "_%s_view_y_minimum" % sensor
        y_max_attr = "_%s_view_y_maximum" % sensor
        y_minimum = getattr(self, y_min_attr)
        y_maximum = getattr(self, y_max_attr)
        y_span = y_maximum - y_minimum
        if y_span > 0 and math.isfinite(vertical_fraction):
            shift = float(vertical_fraction) * y_span
            # Amplitude panning must still respond from the initial auto-fit
            # view; unlike time, the signal can intentionally move partly
            # outside the visible Y range until the user resets the view.
            bounded = (y_minimum + shift, y_maximum + shift)
            if bounded != (y_minimum, y_maximum):
                setattr(self, y_min_attr, bounded[0])
                setattr(self, y_max_attr, bounded[1])
                changed = True
        if changed:
            self._emit_viewport_changed()

    def reset_viewport(self):
        self._view_x_minimum = self._plot_x_minimum
        self._view_x_maximum = self._plot_x_maximum
        self._geophone_view_y_minimum = self._geophone_full_y_minimum
        self._geophone_view_y_maximum = self._geophone_full_y_maximum
        self._mpu_view_y_minimum = self._mpu_full_y_minimum
        self._mpu_view_y_maximum = self._mpu_full_y_maximum
        self._emit_viewport_changed()

    def _data_changed(self):
        data_state = self._data.state
        if data_state == self._data.LOADING:
            self._file_model.set_rows([])
            self._set_empty_context(self.LOADING)
            return
        if data_state == self._data.EMPTY:
            self._file_model.set_rows([])
            self._set_empty_context(self.EMPTY)
            return
        if data_state in (self._data.UNAVAILABLE, self._data.ERROR):
            self._file_model.set_rows([])
            self._set_empty_context(self.UNAVAILABLE, self._data.errorText)
            return
        if data_state != self._data.READY:
            return

        sources = [AnalysisFile(path, name)
                   for path, name in self._data.analysis_sources()]
        self._file_model.set_rows(sources)
        if not sources:
            self._set_empty_context(self.UNAVAILABLE)
            return

        paths = {source.path for source in sources}
        if self._selected_path not in paths:
            preferred = self._data.selectedFilePath
            self._selected_path = preferred if preferred in paths else sources[0].path
            self._file_result = None
            self._events = []
            self._selected_index = -1
            self._origin_us = None
        if not self._activated:
            self._state = self.EMPTY
            self._error = ""
            self._emit_changed()
            return
        if self._loading_path == self._selected_path:
            return
        if (self._state == self.READY and self._file_result is not None
                and self._file_result.archivo == os.path.abspath(self._selected_path)):
            self._emit_changed()
            return
        self._load_selected_file()

    def _load_selected_file(self):
        if not self._selected_path:
            self._set_empty_context(self.UNAVAILABLE)
            return
        self._request_id += 1
        request_id = self._request_id
        self._loading_path = self._selected_path
        self._state = self.LOADING
        self._error = ""
        self._events = []
        self._selected_index = -1
        self._origin_us = None
        self._emit_changed()

        # Load file in background thread
        thread = threading.Thread(
            target=self._load_file_worker,
            args=(request_id, self._selected_path),
            daemon=True
        )
        self._tasks[request_id] = thread
        thread.start()

    def _load_file_worker(self, request_id, path):
        """Worker thread for loading BIN files."""
        try:
            result = parse_file(path)
            error = ""
        except Exception as exc:
            result = None
            error = "No se pudo cargar el archivo para Análisis: %s" % exc

        # Schedule callback on main thread via lock
        with self._lock:
            if request_id != self._request_id or path != self._selected_path:
                return
            self._tasks.pop(request_id, None)
            self._loading_path = ""
            if error:
                self._set_empty_context(self.ERROR, error)
                return
            self._load_finished(request_id, path, result, error)

    def _load_finished(self, request_id, path, result, error):
        self._tasks.pop(request_id, None)
        if request_id != self._request_id or path != self._selected_path:
            return
        self._loading_path = ""
        if error:
            self._set_empty_context(self.ERROR, error)
            return

        all_events = result.events if result is not None else []
        valid_events = [(index + 1, event) for index, event in enumerate(all_events)
                        if event.valido]
        if not valid_events:
            self._file_result = result
            self._events = []
            self._selected_index = -1
            self._origin_us = None
            self._clear_signal_data()
            self._state = self.UNAVAILABLE
            self._error = "El archivo no contiene eventos validados disponibles."
            self._emit_changed()
            return

        self._file_result = result
        self._load_stalta_defaults(result.metadata)
        self._events = []
        origin = min((event.inicio_us for _, event in valid_events), default=None)
        self._origin_us = origin
        for original_number, source_event in valid_events:
            analysis = analyze_event(source_event)
            geo_stats = analysis.sensors.get(L.SENSOR_GEOFONO)
            mpu_stats = analysis.sensors.get(L.SENSOR_MPU)
            geo_count = sum(1 for record in source_event.records
                            if record.tipo_sensor == L.SENSOR_GEOFONO)
            mpu_count = sum(1 for record in source_event.records
                            if record.tipo_sensor == L.SENSOR_MPU)
            context = _SelectedEvent(
                original_number=original_number,
                total_events=len(all_events),
                sequence=source_event.secuencia,
                start_us=source_event.inicio_us,
                end_us=source_event.fin_us,
                sample_count=len(source_event.records),
                geophone_samples=geo_count,
                mpu_samples=mpu_count,
                geophone_hz=(geo_stats.stats.observed_hz if geo_stats else 0.0),
                mpu_hz=(mpu_stats.stats.observed_hz if mpu_stats else 0.0),
            )
            self._events.append((source_event, context))
        self._selected_index = 0
        self._state = self.READY
        self._error = ""
        self._refresh_selected_signal_data()
        self._emit_changed()

    def _refresh_selected_signal_data(self):
        selected = self._selected_event()
        if selected is None:
            self._clear_signal_data()
            return
        source_event, context = self._events[self._selected_index]
        event_analysis = analyze_event(source_event)
        series_by_channel = event_series(source_event, event_analysis)
        geo_series = series_by_channel[CHANNEL_VELOCITY]
        mpu_series = series_by_channel[CHANNEL_MAGNITUDE]
        geo_findings = list(geo_series.findings)
        mpu_findings = list(mpu_series.findings)
        mpu_findings.extend(check_magnitude(source_event))

        def plot_data(series):
            ordered = sorted(series.samples,
                             key=lambda sample: (sample.timestamp_us,
                                                 sample.source_index))
            times = [(sample.timestamp_us - self._origin_us) / 1_000_000.0
                     for sample in ordered]
            values = [sample.value for sample in ordered]
            sequences = [sample.secuencia for sample in ordered]
            breaks = []
            for index in range(1, len(ordered)):
                previous, current = ordered[index - 1], ordered[index]
                sequence_gap = (current.secuencia != 0
                                and previous.secuencia != 0
                                and current.secuencia != previous.secuencia + 1)
                if (sequence_gap
                        or current.source_index < previous.source_index):
                    breaks.append(index)
            return times, values, breaks, sequences

        (self._geophone_times, self._geophone_values, self._geophone_breaks,
         self._geophone_sequences) = \
            plot_data(geo_series)
        (self._mpu_times, self._mpu_values, self._mpu_breaks,
         self._mpu_sequences) = \
            plot_data(mpu_series)
        self._plot_x_minimum = (context.start_us - self._origin_us) / 1_000_000.0
        self._plot_x_maximum = (context.end_us - self._origin_us) / 1_000_000.0
        if self._plot_x_maximum <= self._plot_x_minimum:
            greatest = max(self._geophone_times + self._mpu_times,
                           default=self._plot_x_minimum + 1.0)
            self._plot_x_maximum = max(greatest, self._plot_x_minimum + 1.0)
        self._view_x_minimum = self._plot_x_minimum
        self._view_x_maximum = self._plot_x_maximum
        (self._geophone_full_y_minimum,
         self._geophone_full_y_maximum) = self._padded_y_range(self._geophone_values)
        (self._mpu_full_y_minimum,
         self._mpu_full_y_maximum) = self._padded_y_range(self._mpu_values)
        self._geophone_view_y_minimum = self._geophone_full_y_minimum
        self._geophone_view_y_maximum = self._geophone_full_y_maximum
        self._mpu_view_y_minimum = self._mpu_full_y_minimum
        self._mpu_view_y_maximum = self._mpu_full_y_maximum

        metadata = self._file_result.metadata if self._file_result else None
        pre_event_seconds = (metadata.pre_evento_segundos
                             if metadata is not None else 0)
        self._metrics = {
            "geophone": calculate_signal_metrics(
                geo_series, pre_event_seconds, geo_findings),
            "mpu": calculate_signal_metrics(
                mpu_series, pre_event_seconds, mpu_findings),
        }
        self._calculate_stalta_for_selected_event()
        self._calculate_spectrum_for_selected_event()
        self._calculate_spectrogram_for_selected_event()
        self._cursor_time = -1.0
        self._spectrum_cursor_freq = -1.0
        self._spectrogram_cursor_time = -1.0
        self._spectrogram_cursor_freq = -1.0
        self._update_cursor_texts()
        self._update_spectrum_cursor_texts()
        self._update_spectrogram_cursor_texts()
        self._emit_cursor_changed()
        self._emit_viewport_changed()

    def _calculate_stalta_for_selected_event(self):
        selected = self._selected_event()
        if selected is None:
            self._geophone_stalta = self._empty_stalta()
            self._mpu_stalta = self._empty_stalta()
            return
        _, context = self._events[self._selected_index]
        arguments = (
            self._sta_window_seconds,
            self._lta_window_seconds,
            self._stalta_activation_threshold,
            self._stalta_deactivation_threshold,
            self._stalta_method,
        )
        self._geophone_stalta = calculate_stalta(
            self._geophone_times,
            self._geophone_values,
            self._geophone_sequences,
            self._geophone_breaks,
            context.geophone_hz,
            *arguments,
        )
        self._mpu_stalta = calculate_stalta(
            self._mpu_times,
            self._mpu_values,
            self._mpu_sequences,
            self._mpu_breaks,
            context.mpu_hz,
            *arguments,
        )
        rows = []
        for sensor_name, result in (("Geófono", self._geophone_stalta),
                                    ("MPU", self._mpu_stalta)):
            rows.extend(StaltaCandidateRow(
                sensor=sensor_name,
                start_text="%.3f s" % candidate.start_seconds,
                end_text="%.3f s" % candidate.end_seconds,
                duration_text="%.3f s" % candidate.duration_seconds,
                peak_ratio_text="%.2f" % candidate.peak_ratio,
            ) for candidate in result.candidates)
        rows.sort(key=lambda row: float(row.start_text[:-2]))
        self._stalta_candidate_model.set_rows(rows)

    def _calculate_spectrum_for_selected_event(self):
        # Single-segment rFFT over the longest continuous run. For the
        # analyzed event sizes (hundreds of samples) numpy completes in
        # microseconds, so no worker round-trip is needed here.
        selected = self._selected_event()
        if selected is None:
            self._geophone_spectrum = self._empty_spectrum()
            self._mpu_spectrum = self._empty_spectrum()
            return
        _, context = self._events[self._selected_index]
        self._geophone_spectrum = calculate_spectrum(
            self._geophone_times,
            self._geophone_values,
            self._geophone_sequences,
            self._geophone_breaks,
            context.geophone_hz,
            self._spectrum_window,
            self._spectrum_range_hz,
        )
        self._mpu_spectrum = calculate_spectrum(
            self._mpu_times,
            self._mpu_values,
            self._mpu_sequences,
            self._mpu_breaks,
            context.mpu_hz,
            self._spectrum_window,
            self._spectrum_range_hz,
        )

    def _update_spectrum_cursor_text(self, result, unit):
        if self._spectrum_cursor_freq < 0 or not result.freqs:
            return "Mueve el cursor sobre un espectro para inspeccionar bins."
        index = bisect.bisect_left(result.freqs, self._spectrum_cursor_freq)
        candidates = [candidate for candidate in (index - 1, index)
                      if 0 <= candidate < len(result.freqs)]
        if not candidates:
            return "Bin no disponible"
        nearest = min(candidates, key=lambda candidate:
                      abs(result.freqs[candidate] - self._spectrum_cursor_freq))
        return "f = %.2f Hz   Amplitud = %.4g %s" % (
            result.freqs[nearest], result.amps[nearest], unit)

    def _update_spectrum_cursor_texts(self):
        self._geophone_spectrum_cursor_text = self._update_spectrum_cursor_text(
            self._geophone_spectrum, "mm/s")
        self._mpu_spectrum_cursor_text = self._update_spectrum_cursor_text(
            self._mpu_spectrum, "m/s²")

    def set_spectrum_cursor(self, frequency_hz):
        value = float(frequency_hz)
        if not math.isfinite(value) or value < 0:
            return
        if abs(self._spectrum_cursor_freq - value) < 1e-9:
            return
        self._spectrum_cursor_freq = value
        self._update_spectrum_cursor_texts()
        self._emit_cursor_changed()

    def clear_spectrum_cursor(self):
        if self._spectrum_cursor_freq < 0:
            return
        self._spectrum_cursor_freq = -1.0
        self._update_spectrum_cursor_texts()
        self._emit_cursor_changed()

    def _update_cursor_text(self, times, values, unit):
        if (self._cursor_time < 0 or not times or len(times) != len(values)):
            return "Mueve el cursor sobre una señal para inspeccionar muestras."
        # Event-relative time: when an event is selected, compute time
        # proper to the event (cursor time minus event start).
        event_start_rel = None
        if self._selected_index >= 0 and self._selected_index < len(self._events):
            _, context = self._events[self._selected_index]
            event_start_rel = (context.start_us - self._origin_us) / 1_000_000.0
        index = bisect.bisect_left(times, self._cursor_time)
        candidates = [candidate for candidate in (index - 1, index)
                      if 0 <= candidate < len(times)]
        if not candidates:
            return "Muestra no disponible"
        nearest = min(candidates, key=lambda candidate:
                      abs(times[candidate] - self._cursor_time))
        value = values[nearest]
        total_s = times[nearest]
        rel_s = total_s - event_start_rel if event_start_rel is not None else None
        if not math.isfinite(value):
            if rel_s is not None:
                return ("t = %.3f s (archivo) / %.3f s (evento) · muestra no finita"
                        % (total_s, rel_s))
            return "t = %.3f s · muestra no finita" % total_s
        base = "t = %.3f s" % total_s
        if rel_s is not None:
            base += " · %.3f s (evento)" % rel_s
        base += "   Amplitud = %.5g %s" % (value, unit)
        return base

    def _update_cursor_texts(self):
        self._geophone_cursor_text = self._update_cursor_text(
            self._geophone_times, self._geophone_values, "mm/s")
        self._mpu_cursor_text = self._update_cursor_text(
            self._mpu_times, self._mpu_values, "m/s²")
        self._geophone_stalta_cursor_text = self._update_stalta_cursor_text(
            self._geophone_times, self._geophone_values,
            self._geophone_stalta, "mm/s")
        self._mpu_stalta_cursor_text = self._update_stalta_cursor_text(
            self._mpu_times, self._mpu_values, self._mpu_stalta, "m/s²")

    def _update_stalta_cursor_text(self, times, values, result, unit):
        if (self._cursor_time < 0 or not times
                or len(times) != len(values)):
            return "Mueve el cursor para inspeccionar señal, STA, LTA y Ratio."
        # Event-relative time when an event is selected.
        event_start_rel = None
        if self._selected_index >= 0 and self._selected_index < len(self._events):
            _, context = self._events[self._selected_index]
            event_start_rel = (context.start_us - self._origin_us) / 1_000_000.0
        index = bisect.bisect_left(times, self._cursor_time)
        candidates = [candidate for candidate in (index - 1, index)
                      if 0 <= candidate < len(times)]
        if not candidates:
            return "Muestra no disponible"
        nearest = min(candidates, key=lambda candidate:
                      abs(times[candidate] - self._cursor_time))
        value = values[nearest]
        total_s = times[nearest]
        rel_s = total_s - event_start_rel if event_start_rel is not None else None
        sta = result.sta[nearest] if nearest < len(result.sta) else math.nan
        lta = result.lta[nearest] if nearest < len(result.lta) else math.nan
        ratio = result.ratio[nearest] if nearest < len(result.ratio) else math.nan
        fields = []
        if rel_s is not None:
            fields.append("t=%.3f s (archivo) / %.3f s (evento)" % (total_s, rel_s))
        else:
            fields.append("t=%.3f s" % total_s)
        fields.append("Señal=%.4g %s" % (value, unit))
        if math.isfinite(sta) and math.isfinite(lta) and math.isfinite(ratio):
            fields.extend(("STA=%.4g %s" % (sta, unit),
                           "LTA=%.4g %s" % (lta, unit),
                           "Ratio=%.4g" % ratio))
        else:
            fields.append("STA/LTA/Ratio no disponibles (ventana incompleta)")
        return "   ".join(fields)

    def set_cursor_time(self, time_seconds):
        value = float(time_seconds)
        if not self._plot_x_minimum <= value <= self._plot_x_maximum:
            return
        if abs(self._cursor_time - value) < 1e-6:
            return
        self._cursor_time = value
        self._update_cursor_texts()
        self._emit_cursor_changed()

    def clear_cursor(self):
        if self._cursor_time < 0:
            return
        self._cursor_time = -1.0
        self._update_cursor_texts()
        self._emit_cursor_changed()

    def set_metric_sensor(self, sensor):
        if sensor not in ("geophone", "mpu") or sensor == self._metric_sensor:
            return
        self._metric_sensor = sensor
        self._emit_changed()

    def _load_stalta_defaults(self, metadata):
        sta = (metadata.ventana_sta_ms / 1000.0
               if metadata is not None and metadata.ventana_sta_ms > 0 else 0.5)
        lta = (metadata.ventana_lta_ms / 1000.0
               if metadata is not None and metadata.ventana_lta_ms > 0 else 5.0)
        threshold = (metadata.umbral_ratio_milli / 1000.0
                     if metadata is not None and metadata.umbral_ratio_milli > 0
                     else 3.0)
        if lta <= sta or sta <= 0 or lta > 50.0:
            sta, lta = 0.5, 5.0
        self._sta_window_seconds = sta
        self._lta_window_seconds = lta
        self._stalta_activation_threshold = threshold
        self._stalta_deactivation_threshold = threshold * 0.5

    def set_stalta_parameter(self, name, value):
        value = float(value)
        if not math.isfinite(value):
            return
        sta = self._sta_window_seconds
        lta = self._lta_window_seconds
        activation = self._stalta_activation_threshold
        deactivation = self._stalta_deactivation_threshold

        if name == "sta":
            sta = min(max(value, 0.001), lta - 0.001)
        elif name == "lta":
            lta = min(max(value, sta + 0.001), 50.0)
        elif name == "activation":
            activation = min(max(value, 0.001), 1000.0)
            if deactivation >= activation:
                deactivation = activation * 0.5
        elif name == "deactivation":
            deactivation = min(max(value, 0.0), max(0.0, activation - 0.001))
        else:
            return

        if (sta, lta, activation, deactivation) == (
                self._sta_window_seconds, self._lta_window_seconds,
                self._stalta_activation_threshold,
                self._stalta_deactivation_threshold):
            return
        current_event = self._selected_event()
        geo_hz = (self._events[self._selected_index][1].geophone_hz
                  if current_event is not None else 0.0)
        mpu_hz = (self._events[self._selected_index][1].mpu_hz
                  if current_event is not None else 0.0)
        if max(math.ceil(sta * geo_hz), math.ceil(sta * mpu_hz)) > 5000:
            return
        if max(math.ceil(lta * geo_hz), math.ceil(lta * mpu_hz)) > 5000:
            return
        selected = self._selected_event()
        if selected is not None:
            _, context = self._events[self._selected_index]
            for frequency in (context.geophone_hz, context.mpu_hz):
                if (frequency > 0
                        and math.ceil(sta * frequency) >= math.ceil(lta * frequency)):
                    return
        self._sta_window_seconds = sta
        self._lta_window_seconds = lta
        self._stalta_activation_threshold = activation
        self._stalta_deactivation_threshold = deactivation
        self._calculate_stalta_for_selected_event()
        self._emit_changed()

    def set_stalta_method(self, method):
        if method not in ("absolute", "rms") or method == self._stalta_method:
            return
        self._stalta_method = method
        self._calculate_stalta_for_selected_event()
        self._emit_changed()

    def select_submenu(self, submenu):
        if submenu not in ("senales", "espectrograma", "frecuencia", "sta_lta"):
            return
        if submenu == self._active_submenu:
            return
        self._active_submenu = submenu
        self._emit_changed()

    def select_file_at(self, index):
        path = self._file_model.path_at(int(index))
        if path:
            self.select_file(path)

    def select_file(self, path):
        if not path:
            return
        # Populate file model without side effects on _selected_path
        if self._file_model.index_of_path(path) < 0:
            sources = [AnalysisFile(p, n) for p, n in self._data.analysis_sources()]
            self._file_model.set_rows(sources)
        # Load the file if it's different from current or not yet loaded
        if path != self._selected_path or self._state != self.READY:
            self._selected_path = path
            self._load_selected_file()

    def previous_event(self):
        if self._selected_index > 0:
            self._selected_index -= 1
            self._refresh_selected_signal_data()
            self._emit_changed()

    def next_event(self):
        if self._selected_index < len(self._events) - 1:
            self._selected_index += 1
            self._refresh_selected_signal_data()
            self._emit_changed()

    def prepare_for_navigation(self, path):
        """Prefer the valid file selected in Data before opening Analysis."""
        self._activated = True
        if path and self._file_model.index_of_path(path) >= 0:
            self.select_file(path)
        elif self._selected_path and self._state != self.READY:
            self._load_selected_file()

    def activate(self):
        """Load the preferred valid event only when Analysis is opened."""
        if self._activated:
            return
        self._activated = True
        self._data_changed()

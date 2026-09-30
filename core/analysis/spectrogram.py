"""Short-time Fourier spectrograms for the Analysis event view.

Reuses the agreed Frecuencia decisions (see ``analysis/spectrum.py``):

* each sensor (geophone corrected velocity in mm/s, MPU magnitude in m/s²)
  is analyzed over its longest continuous run (``analysis/segments.py``);
* no resampling: samples are treated on a uniform grid at the observed
  rate (exact for the regular geophone stream, approximate for the
  clumped MPU delivery);
* each frame removes its own mean (DC) before transforming;
* the selected window (Hann by default, periodic FFT-bins form shared
  with ``spectrum._window_function``) tapers the frame;
* per-frame amplitudes use ``2·|X[k]| / (N·CG)`` with coherent-gain
  ``CG = mean(w)``, so a stationary sinusoidal peak reads the same
  physical amplitude as in the Frecuencia spectrum; DC and Nyquist bins
  are not doubled.

STFT-specific definitions (see ``analysis/ESPECTROGRAMA.md``):

* ``window_seconds`` (0.5 / 1.0 / 2.0 s, default 1.0 s) sets
  ``N = round(window_seconds * observed_hz)`` (minimum 8 samples). When
  the longest run is shorter, the window adapts down to the run length
  so every event still yields a single frame; samples are never
  invented.
* ``overlap`` (0 / 50 / 75 %, default 50 %) sets
  ``hop = max(1, round(N * (1 - overlap)))``.
* ``range_max_hz`` reuses the Frecuencia ranges (20 / 40 / Nyquist).
* Intensity scale is linear amplitude in physical units, normalized to
  the sensor's own event maximum for the 0–100 legend
  (``intensity = 100 * amp / max_amp``). No log/dB compression is
  applied in this increment.
* Quick-read derivations: the highest-energy frame (sum of ``amp²``
  over shown bins) gives the peak-energy interval; the time-averaged
  spectrum peak ``fp`` gives the dominant band ``[fp − 5, fp + 5] Hz``
  clamped to the shown range; spectral change is
  ``max_frame_energy / median_frame_energy`` (≥3 Alto, ≥1.5 Moderado,
  else Estable; unavailable with a single frame).
"""

import math
from dataclasses import dataclass, field
from typing import List, Optional, Sequence

import numpy as np

from .segments import analyze_runs, longest_run_indices
from .spectrum import WINDOWS, _window_function

#: Window durations offered by the spectrogram view, in seconds.
WINDOW_SECONDS = (0.5, 1.0, 2.0)

#: Overlap fractions offered by the spectrogram view.
OVERLAPS = (0.0, 0.5, 0.75)

#: Frequency ranges offered by the spectrogram view, in Hz.
#: ``None`` renders each sensor up to its own Nyquist limit.
RANGES_HZ = (20.0, 40.0, None)

#: Minimum frame length that still yields a usable spectrum slice.
MIN_SAMPLES = 8

#: Half-width of the reported dominant band, in Hz.
BAND_HALF_WIDTH_HZ = 5.0


@dataclass(frozen=True)
class SpectrogramResult:
    times: List[float] = field(default_factory=list)
    frame_starts: List[float] = field(default_factory=list)
    frame_ends: List[float] = field(default_factory=list)
    freqs: List[float] = field(default_factory=list)
    amps: List[float] = field(default_factory=list)
    sample_rate_hz: float = 0.0
    window_id: str = "hann"
    window_seconds: float = 0.0
    window_samples: int = 0
    hop_samples: int = 0
    overlap: float = 0.5
    freq_resolution_hz: float = 0.0
    time_step_s: float = 0.0
    range_max_hz: Optional[float] = 40.0
    frame_count: int = 0
    bin_count: int = 0
    peak_time: Optional[float] = None
    peak_freq: Optional[float] = None
    peak_amp: Optional[float] = None
    peak_energy_start: Optional[float] = None
    peak_energy_end: Optional[float] = None
    dominant_band_lo: Optional[float] = None
    dominant_band_hi: Optional[float] = None
    change_label: Optional[str] = None


def _empty(sample_rate_hz=0.0, window_id="hann", window_seconds=0.0,
           overlap=0.5, range_max_hz=40.0):
    return SpectrogramResult(
        [], [], [], [], [], sample_rate_hz, window_id, window_seconds,
        0, 0, overlap, 0.0, 0.0, range_max_hz, 0, 0,
        None, None, None, None, None, None, None, None)


def calculate_spectrogram(times_seconds: Sequence[float],
                          values: Sequence[float],
                          sequences: Sequence[int],
                          break_before: Sequence[int],
                          observed_hz: float,
                          window="hann", window_seconds=1.0,
                          overlap=0.5,
                          range_max_hz=40.0) -> SpectrogramResult:
    """Calculate the agreed STFT magnitude spectrogram."""
    if (not math.isfinite(observed_hz) or observed_hz <= 0
            or window not in WINDOWS
            or not math.isfinite(window_seconds) or window_seconds <= 0
            or not math.isfinite(overlap) or overlap < 0
            or overlap >= 1
            or (range_max_hz is not None
                and (not math.isfinite(range_max_hz)
                     or range_max_hz <= 0))):
        return _empty(window_id=window if window in WINDOWS else "hann",
                      window_seconds=window_seconds
                      if math.isfinite(window_seconds) else 0.0,
                      overlap=overlap if math.isfinite(overlap) else 0.5,
                      range_max_hz=range_max_hz)

    runs = analyze_runs(times_seconds, values, sequences, break_before,
                        observed_hz)
    count = min(len(times_seconds), len(values), len(sequences))
    usable = [math.isfinite(float(times_seconds[i]))
              and math.isfinite(float(values[i])) for i in range(count)]
    order = longest_run_indices(runs.boundary, usable)
    run_length = len(order)
    if run_length < MIN_SAMPLES:
        return _empty(sample_rate_hz=observed_hz, window_id=window,
                      window_seconds=window_seconds, overlap=overlap,
                      range_max_hz=range_max_hz)

    window_samples = max(MIN_SAMPLES,
                         int(round(window_seconds * observed_hz)))
    if window_samples > run_length:
        window_samples = run_length
    hop = max(1, int(round(window_samples * (1.0 - overlap))))

    weights = _window_function(window, window_samples)
    coherent_gain = float(np.mean(weights))
    if not math.isfinite(coherent_gain) or coherent_gain <= 0:
        return _empty(sample_rate_hz=observed_hz, window_id=window,
                      window_seconds=window_seconds, overlap=overlap,
                      range_max_hz=range_max_hz)

    full_freqs = np.fft.rfftfreq(window_samples, d=1.0 / observed_hz)
    if range_max_hz is None:
        shown = np.ones(len(full_freqs), dtype=bool)
    else:
        shown = full_freqs <= range_max_hz + 1e-12
    shown_idx = np.flatnonzero(shown)
    if len(shown_idx) == 0:
        return _empty(sample_rate_hz=observed_hz, window_id=window,
                      window_seconds=window_seconds, overlap=overlap,
                      range_max_hz=range_max_hz)
    freqs = [float(full_freqs[i]) for i in shown_idx]

    times: List[float] = []
    starts: List[float] = []
    ends: List[float] = []
    flat: List[float] = []
    frame = 0
    start = 0
    while start + window_samples <= run_length:
        idx = order[start:start + window_samples]
        raw = np.array([float(values[i]) for i in idx], dtype=np.float64)
        block = raw - raw.mean()
        spectrum = np.fft.rfft(block * weights)
        amps = np.abs(spectrum) / (window_samples * coherent_gain)
        if len(amps) > 2:
            amps[1:-1] *= 2.0
        elif len(amps) == 2:
            amps[1] *= 2.0
        center = order[start + window_samples // 2]
        times.append(float(times_seconds[center]))
        starts.append(float(times_seconds[order[start]]))
        ends.append(float(times_seconds[order[start + window_samples - 1]]))
        flat.extend(float(amps[i]) for i in shown_idx)
        frame += 1
        start += hop
    if frame == 0:
        return _empty(sample_rate_hz=observed_hz, window_id=window,
                      window_seconds=window_seconds, overlap=overlap,
                      range_max_hz=range_max_hz)

    bins = len(freqs)
    grid = np.array(flat, dtype=np.float64).reshape(frame, bins)
    best = int(np.argmax(grid))
    best_frame, best_bin = divmod(best, bins)
    peak_amp = float(grid[best_frame, best_bin])
    peak = (float(times[best_frame]), float(freqs[best_bin]),
            peak_amp if peak_amp > 0 else None)

    energies = np.sum(grid ** 2, axis=1)
    loud = int(np.argmax(energies))
    median_energy = float(np.median(energies))
    max_energy = float(energies[loud])
    change = None
    if frame > 1 and median_energy > 0 and math.isfinite(median_energy):
        ratio = max_energy / median_energy
        if ratio >= 3.0:
            change = "Alto durante el evento"
        elif ratio >= 1.5:
            change = "Moderado durante el evento"
        else:
            change = "Estable durante el evento"

    mean_spectrum = np.mean(grid, axis=0)
    mean_peak = int(np.argmax(mean_spectrum))
    top = float(freqs[mean_peak])
    fmax = float(freqs[-1])
    band = (max(0.0, top - BAND_HALF_WIDTH_HZ),
            min(fmax, top + BAND_HALF_WIDTH_HZ))

    return SpectrogramResult(
        times=times,
        frame_starts=starts,
        frame_ends=ends,
        freqs=freqs,
        amps=[float(a) for a in flat],
        sample_rate_hz=observed_hz,
        window_id=window,
        window_seconds=window_seconds,
        window_samples=window_samples,
        hop_samples=hop,
        overlap=overlap,
        freq_resolution_hz=float(observed_hz / window_samples),
        time_step_s=float(hop / observed_hz),
        range_max_hz=range_max_hz,
        frame_count=frame,
        bin_count=bins,
        peak_time=peak[0],
        peak_freq=peak[1],
        peak_amp=peak[2],
        peak_energy_start=float(starts[loud]),
        peak_energy_end=float(ends[loud]),
        dominant_band_lo=band[0],
        dominant_band_hi=band[1],
        change_label=change,
    )

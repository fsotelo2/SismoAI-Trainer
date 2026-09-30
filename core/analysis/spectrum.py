"""Single-sided amplitude spectra for the displayed Analysis traces.

For the selected event, each sensor (geophone corrected velocity in mm/s,
MPU magnitude in m/s²) is analyzed over its longest continuous run with a
single real FFT:

* the run mean (DC) is removed before transforming;
* the selected window (Hann by default) tapers the run;
* amplitudes use ``2·|X[k]| / (N·CG)`` with coherent-gain ``CG = mean(w)``,
  so a sinusoidal peak reads its physical amplitude; DC and Nyquist bins
  are not doubled;
* no resampling is performed: samples are treated on a uniform grid at
  the observed rate (exact for the regular geophone stream, approximate
  for the clumped MPU delivery — see analysis/FRECUENCIA.md).

Metrics (dominant/secondary peaks, centroid, −3 dB bandwidth, in-range
energy, resolution) are computed over the displayed frequency range.
"""

import math
from dataclasses import dataclass, field
from typing import List, Optional, Sequence

import numpy as np

from .segments import analyze_runs, longest_run_indices

WINDOWS = ("hann", "hamming", "rectangular")

#: Minimum run length that still yields a usable spectrum.
MIN_SAMPLES = 8


@dataclass(frozen=True)
class SpectrumResult:
    freqs: List[float]
    amps: List[float]
    sample_rate_hz: float
    window_id: str
    window_samples: int
    freq_resolution_hz: float
    range_max_hz: Optional[float]
    dominant_freq_hz: Optional[float]
    dominant_amp: Optional[float]
    secondary_freq_hz: Optional[float]
    secondary_amp: Optional[float]
    centroid_freq_hz: Optional[float]
    bandwidth_3db_hz: Optional[float]
    energy_in_range: Optional[float]


def _empty(sample_rate_hz=0.0, window_id="hann", range_max_hz=None):
    return SpectrumResult([], [], sample_rate_hz, window_id, 0, 0.0,
                          range_max_hz, None, None, None, None, None,
                          None, None)


def _window_function(window_id, length):
    # Periodic (FFT-bins) form: the window spans exactly the analyzed
    # block, so a bin-centered tone stays confined to three bins.
    # Periodic (FFT-bins) form: the window spans exactly the analyzed
    # block, so a bin-centered tone stays confined to three bins.
    index = np.arange(length)
    if window_id == "hann":
        return 0.5 - 0.5 * np.cos(2.0 * np.pi * index / length)
    if window_id == "hamming":
        return 0.54 - 0.46 * np.cos(2.0 * np.pi * index / length)
    if window_id == "rectangular":
        return np.ones(length)
    return None


def calculate_spectrum(times_seconds: Sequence[float],
                       values: Sequence[float], sequences: Sequence[int],
                       break_before: Sequence[int], observed_hz: float,
                       window="hann", range_max_hz=40.0) -> SpectrumResult:
    """Calculate the agreed single-sided amplitude spectrum."""
    if (not math.isfinite(observed_hz) or observed_hz <= 0
            or window not in WINDOWS
            or (range_max_hz is not None
                and (not math.isfinite(range_max_hz) or range_max_hz <= 0))):
        return _empty(window_id=window if window in WINDOWS else "hann",
                      range_max_hz=range_max_hz)

    runs = analyze_runs(times_seconds, values, sequences, break_before,
                        observed_hz)
    count = min(len(times_seconds), len(values), len(sequences))
    usable = [math.isfinite(float(times_seconds[i]))
              and math.isfinite(float(values[i])) for i in range(count)]
    order = longest_run_indices(runs.boundary, usable)
    if len(order) < MIN_SAMPLES:
        return _empty(sample_rate_hz=observed_hz, window_id=window,
                      range_max_hz=range_max_hz)

    raw = np.array([float(values[i]) for i in order], dtype=np.float64)
    run = raw - raw.mean()
    weights = _window_function(window, len(run))
    coherent_gain = float(weights.mean())
    spectrum = np.fft.rfft(run * weights)
    freqs = np.fft.rfftfreq(len(run), d=1.0 / observed_hz)
    amps = np.abs(spectrum) / (len(run) * coherent_gain)
    if len(amps) > 2:
        amps[1:-1] *= 2.0
    elif len(amps) == 2:
        amps[1] *= 2.0

    if range_max_hz is None:
        shown = np.ones(len(freqs), dtype=bool)
    else:
        shown = freqs <= range_max_hz + 1e-12
    if not shown.any():
        return _empty(sample_rate_hz=observed_hz, window_id=window,
                      range_max_hz=range_max_hz)

    shown_idx = np.flatnonzero(shown)
    search = shown_idx[shown_idx > 0]  # DC never wins a peak search
    if len(search) == 0:
        return SpectrumResult(
            [float(f) for f in freqs[shown]], [float(a) for a in amps[shown]],
            observed_hz, window, len(run), observed_hz / len(run),
            range_max_hz, None, None, None, None, None, None,
            float(np.sum(amps[shown] ** 2)))

    # Significance floor: in-range peaks below 1% of the event's global
    # spectral peak are numerical dust or out-of-range leakage, not content.
    # The paired amplitude always tells the same story.
    global_peak = float(np.max(amps)) if len(amps) else 0.0
    dom_pos = int(search[int(np.argmax(amps[search]))])
    dominant_freq = dominant_amp = None
    if global_peak > 0 and float(amps[dom_pos]) >= 0.01 * global_peak:
        dominant_freq = float(freqs[dom_pos])
        dominant_amp = float(amps[dom_pos])
    resolution = float(observed_hz / len(run))

    peak_positions = []
    if dominant_freq is not None:
        peak_positions = [
            int(i) for i in search
            if 0 < i < len(amps) - 1
            and amps[i] > amps[i - 1] and amps[i] >= amps[i + 1]
            and abs(float(freqs[i]) - dominant_freq) > 2.0 * resolution
            and float(amps[i]) >= 0.01 * global_peak
        ]
    secondary_freq = secondary_amp = None
    if peak_positions:
        second = max(peak_positions, key=lambda i: float(amps[i]))
        secondary_freq = float(freqs[second])
        secondary_amp = float(amps[second])

    weights_sum = float(np.sum(amps[shown]))
    centroid = (float(np.sum(freqs[shown] * amps[shown]) / weights_sum)
                if weights_sum > 0 else None)

    bandwidth = None
    if dominant_amp is not None and dominant_amp > 0:
        shown_set = set(int(i) for i in shown_idx)
        level = dominant_amp / math.sqrt(2.0)
        left = dom_pos
        while left - 1 in shown_set and amps[left - 1] >= level:
            left -= 1
        right = dom_pos
        while right + 1 in shown_set and amps[right + 1] >= level:
            right += 1
        if left > int(shown_idx[0]) and right < int(shown_idx[-1]):
            # Linear interpolation between bins locates each −3 dB
            # crossing; a pure tone then measures ~1.44 bins wide
            # instead of a degenerate 0.
            low_lo = left - 1
            span_lo = amps[left] - amps[low_lo]
            cross_lo = (float(freqs[low_lo]) + (level - amps[low_lo])
                        / span_lo * resolution) if span_lo > 0 else float(freqs[left])
            high_hi = right + 1
            span_hi = amps[right] - amps[high_hi]
            cross_hi = (float(freqs[right]) + (amps[right] - level)
                        / span_hi * resolution) if span_hi > 0 else float(freqs[right])
            bandwidth = max(0.0, cross_hi - cross_lo)

    return SpectrumResult(
        freqs=[float(f) for f in freqs[shown]],
        amps=[float(a) for a in amps[shown]],
        sample_rate_hz=observed_hz,
        window_id=window,
        window_samples=len(run),
        freq_resolution_hz=resolution,
        range_max_hz=range_max_hz,
        dominant_freq_hz=dominant_freq,
        dominant_amp=dominant_amp,
        secondary_freq_hz=secondary_freq,
        secondary_amp=secondary_amp,
        centroid_freq_hz=centroid,
        bandwidth_3db_hz=bandwidth,
        energy_in_range=float(np.sum(amps[shown] ** 2)),
    )

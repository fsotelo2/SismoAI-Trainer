"""STA/LTA calculation on the physical traces displayed by Analysis.

The detector uses trailing moving means of absolute sample amplitude. Window
durations are converted to sample counts with ceil(duration * observed_hz),
matching C06_STALTA's window conversion. Dataset traces are used directly:
geophone corrected velocity and the stored MPU magnitude. No hidden axis
reconstruction, interpolation, or source-file modification is performed.
"""

import math
import statistics
from collections import deque
from dataclasses import dataclass
from typing import List, Optional, Sequence

from .segments import analyze_runs


@dataclass(frozen=True)
class Candidate:
    start_seconds: float
    end_seconds: float
    peak_ratio: float
    peak_seconds: float

    @property
    def duration_seconds(self):
        return max(0.0, self.end_seconds - self.start_seconds)


@dataclass(frozen=True)
class StaltaResult:
    sta: List[float]
    lta: List[float]
    ratio: List[float]
    candidates: List[Candidate]
    peak_ratio: Optional[float]
    peak_seconds: Optional[float]
    mean_lta: Optional[float]
    sample_window_sta: int
    sample_window_lta: int
    windows_adapted: bool = False


def calculate_stalta(times_seconds: Sequence[float], values: Sequence[float],
                     sequences: Sequence[int], break_before: Sequence[int],
                     observed_hz: float, sta_seconds: float,
                     lta_seconds: float, activation_threshold: float,
                     deactivation_threshold: float,
                     method: str = "absolute") -> StaltaResult:
    """Calculate rolling STA/LTA with hysteretic candidates.

    NaN marks warm-up or samples discarded at a segment boundary. A boundary
    closes any active candidate and resets both windows. A time gap breaks a
    segment only when anomalous by both standards: three times the median
    positive interval, and four nominal periods from the observed rate (the
    C06 tolerance, which keeps bursty but valid delivery such as clumped
    MPU batches inside one segment). No samples are synthesized.

    When the longest continuous run holds fewer samples than a configured
    window, that window is adapted down to the run (per sensor) so the
    curves are still drawn; the effective sample windows are reported in
    the result instead of inventing data. Runs shorter than two samples
    cannot form a ratio and stay unavailable.
    """
    count = min(len(times_seconds), len(values), len(sequences))
    sta_out = [math.nan] * count
    lta_out = [math.nan] * count
    ratio_out = [math.nan] * count
    candidates: List[Candidate] = []

    if (count == 0 or not math.isfinite(observed_hz) or observed_hz <= 0
            or not math.isfinite(sta_seconds) or sta_seconds <= 0
            or not math.isfinite(lta_seconds) or lta_seconds <= sta_seconds
            or not math.isfinite(activation_threshold)
            or not math.isfinite(deactivation_threshold)
            or deactivation_threshold < 0
            or deactivation_threshold >= activation_threshold
            or method not in ("absolute", "rms")):
        return StaltaResult(sta_out, lta_out, ratio_out, candidates,
                            None, None, None, 0, 0)

    sta_count = int(math.ceil(sta_seconds * observed_hz))
    lta_count = int(math.ceil(lta_seconds * observed_hz))
    if (sta_count < 1 or lta_count <= sta_count
            or lta_count > 5000):
        return StaltaResult(sta_out, lta_out, ratio_out, candidates,
                            None, None, None, sta_count, lta_count)
    adapted = False

    runs = analyze_runs(times_seconds, values, sequences, break_before,
                        observed_hz)
    boundary = runs.boundary
    longest_run = runs.longest
    t_vals = [float(times_seconds[index]) for index in range(count)]
    v_vals = [float(values[index]) for index in range(count)]
    seq_vals = [int(sequences[index]) for index in range(count)]
    if lta_count > longest_run:
        lta_count = longest_run
        adapted = True
    if sta_count > lta_count - 1:
        sta_count = max(1, lta_count - 1)
        adapted = True
    if lta_count < 2 or sta_count < 1:
        return StaltaResult(sta_out, lta_out, ratio_out, candidates,
                            None, None, None, sta_count, lta_count,
                            adapted)

    sta_window = deque()
    lta_window = deque()
    sta_sum = 0.0
    lta_sum = 0.0
    candidate_start = None
    candidate_peak = 0.0
    candidate_peak_time = 0.0
    valid_lta_values = []
    peak_ratio = None
    peak_seconds = None
    previous_valid_index = None

    def close_candidate(end_time):
        nonlocal candidate_start, candidate_peak, candidate_peak_time
        if candidate_start is not None:
            candidates.append(Candidate(
                start_seconds=candidate_start,
                end_seconds=max(candidate_start, end_time),
                peak_ratio=candidate_peak,
                peak_seconds=candidate_peak_time,
            ))
        candidate_start = None
        candidate_peak = 0.0
        candidate_peak_time = 0.0

    def reset_windows():
        nonlocal sta_sum, lta_sum
        sta_window.clear()
        lta_window.clear()
        sta_sum = 0.0
        lta_sum = 0.0

    for index in range(count):
        time_value = t_vals[index]
        sample_value = v_vals[index]
        sequence = seq_vals[index]
        discontinuity = boundary[index]

        if discontinuity:
            end_time = (t_vals[previous_valid_index]
                        if previous_valid_index is not None else time_value)
            close_candidate(end_time)
            reset_windows()
            previous_valid_index = None
            continue

        measure = (sample_value * sample_value if method == "rms"
                   else abs(sample_value))
        sta_window.append(measure)
        lta_window.append(measure)
        sta_sum += measure
        lta_sum += measure
        if len(sta_window) > sta_count:
            sta_sum -= sta_window.popleft()
        if len(lta_window) > lta_count:
            lta_sum -= lta_window.popleft()

        if len(sta_window) == sta_count:
            mean_sta = sta_sum / sta_count
            sta_out[index] = math.sqrt(max(0.0, mean_sta)) \
                if method == "rms" else mean_sta
        if len(lta_window) == lta_count:
            mean_lta = lta_sum / lta_count
            lta_value = (math.sqrt(max(0.0, mean_lta))
                         if method == "rms" else mean_lta)
            lta_out[index] = lta_value
            valid_lta_values.append(lta_value)
            ratio_value = sta_out[index] / lta_value if lta_value > 0 else 0.0
            ratio_out[index] = ratio_value

            if peak_ratio is None or ratio_value > peak_ratio:
                peak_ratio = ratio_value
                peak_seconds = time_value
            if candidate_start is None and ratio_value >= activation_threshold:
                candidate_start = time_value
                candidate_peak = ratio_value
                candidate_peak_time = time_value
            elif candidate_start is not None:
                if ratio_value > candidate_peak:
                    candidate_peak = ratio_value
                    candidate_peak_time = time_value
                if ratio_value <= deactivation_threshold:
                    close_candidate(time_value)

        previous_valid_index = index

    if previous_valid_index is not None:
        close_candidate(t_vals[previous_valid_index])

    mean_lta = (statistics.fmean(valid_lta_values)
                if valid_lta_values else None)
    return StaltaResult(
        sta=sta_out,
        lta=lta_out,
        ratio=ratio_out,
        candidates=candidates,
        peak_ratio=peak_ratio,
        peak_seconds=peak_seconds,
        mean_lta=mean_lta,
        sample_window_sta=sta_count,
        sample_window_lta=lta_count,
        windows_adapted=adapted,
    )

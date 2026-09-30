"""Continuous-run segmentation shared by the Analysis detectors.

A run breaks before a sample that is unusable (non-finite time or value),
explicitly marked (sequence/source-order break from the drawing layer), out
of order in time, separated by an anomalous gap, or discontinuous in
per-sensor sequence numbers. A gap is anomalous only when it exceeds BOTH
three times the median positive interval AND four nominal periods from the
observed rate (the C06 tolerance, which keeps bursty but valid delivery
such as clumped MPU batches inside one run). Nothing is interpolated or
repaired; boundary samples start a new run.
"""

import math
import statistics
from dataclasses import dataclass, field
from typing import List, Sequence, Set


@dataclass(frozen=True)
class Runs:
    boundary: List[bool]
    longest: int


def analyze_runs(times_seconds: Sequence[float], values: Sequence[float],
                 sequences: Sequence[int], break_before: Sequence[int],
                 observed_hz: float) -> Runs:
    """Classify run boundaries and measure the longest usable run."""
    count = min(len(times_seconds), len(values), len(sequences))
    t_vals = [float(times_seconds[index]) for index in range(count)]
    v_vals = [float(values[index]) for index in range(count)]
    seq_vals = [int(sequences[index]) for index in range(count)]
    usable = [math.isfinite(t_vals[index]) and math.isfinite(v_vals[index])
              for index in range(count)]
    explicit: Set[int] = {int(index) for index in break_before}
    intervals = []
    for index in range(1, count):
        if index in explicit:
            continue
        delta = t_vals[index] - t_vals[index - 1]
        if math.isfinite(delta) and delta > 0:
            intervals.append(delta)
    median_interval = statistics.median(intervals) if intervals else 0.0
    gap_limit = max(
        3.0 * median_interval if median_interval > 0 else math.inf,
        4.0 / observed_hz if observed_hz > 0 else math.inf,
    )

    boundary = [False] * count
    for index in range(1, count):
        if index in explicit:
            boundary[index] = True
            continue
        if not usable[index]:
            boundary[index] = True
            continue
        if not math.isfinite(t_vals[index - 1]):
            continue
        delta = t_vals[index] - t_vals[index - 1]
        if delta <= 0 or delta > gap_limit:
            boundary[index] = True
            continue
        if (seq_vals[index] != 0 and seq_vals[index - 1] != 0
                and seq_vals[index] != seq_vals[index - 1] + 1):
            boundary[index] = True

    longest = 0
    run = 0
    for index in range(count):
        if usable[index] and (index == 0 or not boundary[index]):
            run += 1
            longest = max(longest, run)
        else:
            run = 0
    return Runs(boundary=boundary, longest=longest)


def longest_run_indices(boundary: List[bool], usable: List[bool]) -> List[int]:
    """Indices of the longest usable run (empty when none exists)."""
    best: List[int] = []
    current: List[int] = []
    for index, ok in enumerate(usable):
        if ok and (index == 0 or not boundary[index]):
            current.append(index)
        else:
            if len(current) > len(best):
                best = current
            current = []
    if len(current) > len(best):
        best = current
    return best

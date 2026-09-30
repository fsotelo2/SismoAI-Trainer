"""Per-event signal analysis (spec sections 11-12).

Separates samples by tipoSensor, keeps source order, reports (never
repairs): sequence gaps, timestamp reversals, interval statistics,
observed frequency per sensor, and MPU magnitude consistency. Findings
reference (file, event offset, secuencia, sensor) for traceability.
"""

import math
import statistics
from dataclasses import dataclass, field
from typing import Dict, List

from . import layout as L
from .records import EventResult


@dataclass(frozen=True)
class Finding:
    kind: str  # sequence_gap | timestamp_reversal | magnitude_mismatch
    source_file: str
    event_offset: int
    event_secuencia: int
    sensor: int
    prev_secuencia: int = 0
    cur_secuencia: int = 0
    prev_timestamp_us: int = 0
    cur_timestamp_us: int = 0
    detail: str = ""


@dataclass(frozen=True)
class IntervalStats:
    sample_count: int
    first_us: int
    last_us: int
    median_interval_us: float
    mean_interval_us: float
    min_interval_us: float
    max_interval_us: float
    stdev_interval_us: float
    observed_hz: float


@dataclass(frozen=True)
class SensorAnalysis:
    sensor: int
    stats: IntervalStats
    findings: List[Finding]


@dataclass(frozen=True)
class EventAnalysis:
    event_offset: int
    event_secuencia: int
    sensors: Dict[int, SensorAnalysis]


def _intervals(timestamps: List[int]) -> List[int]:
    return [b - a for a, b in zip(timestamps, timestamps[1:])]


def _stats(timestamps: List[int]) -> IntervalStats:
    n = len(timestamps)
    if n == 0:
        return IntervalStats(0, 0, 0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    if n == 1:
        return IntervalStats(1, timestamps[0], timestamps[0],
                             0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    diffs = _intervals(timestamps)
    med = float(statistics.median(diffs))
    span = timestamps[-1] - timestamps[0]
    return IntervalStats(
        sample_count=n,
        first_us=timestamps[0],
        last_us=timestamps[-1],
        median_interval_us=med,
        mean_interval_us=float(statistics.fmean(diffs)),
        min_interval_us=float(min(diffs)),
        max_interval_us=float(max(diffs)),
        stdev_interval_us=float(statistics.pstdev(diffs)),
        observed_hz=((n - 1) * 1_000_000.0 / span) if span > 0 else 0.0,
    )


def analyze_event(event: EventResult) -> EventAnalysis:
    by_sensor: Dict[int, list] = {}
    for idx, rec in enumerate(event.records):
        by_sensor.setdefault(rec.tipo_sensor, []).append((idx, rec))
    sensors: Dict[int, SensorAnalysis] = {}
    for sensor, items in by_sensor.items():
        findings: List[Finding] = []
        prev_seq = prev_ts = None
        for idx, rec in items:
            if prev_seq is not None and rec.secuencia != prev_seq + 1:
                findings.append(Finding(
                    kind="sequence_gap",
                    source_file=event.archivo,
                    event_offset=event.offset,
                    event_secuencia=event.secuencia,
                    sensor=sensor,
                    prev_secuencia=prev_seq,
                    cur_secuencia=rec.secuencia,
                    prev_timestamp_us=prev_ts,
                    cur_timestamp_us=rec.timestamp_us,
                    detail="discontinuidad de secuencia: no corregida",
                ))
            if prev_ts is not None and rec.timestamp_us < prev_ts:
                findings.append(Finding(
                    kind="timestamp_reversal",
                    source_file=event.archivo,
                    event_offset=event.offset,
                    event_secuencia=event.secuencia,
                    sensor=sensor,
                    prev_secuencia=prev_seq,
                    cur_secuencia=rec.secuencia,
                    prev_timestamp_us=prev_ts,
                    cur_timestamp_us=rec.timestamp_us,
                    detail="timestamp anterior al previo: orden conservado",
                ))
            prev_seq, prev_ts = rec.secuencia, rec.timestamp_us
        ordered = sorted(r.timestamp_us for _, r in items)
        sensors[sensor] = SensorAnalysis(
            sensor=sensor,
            stats=_stats(ordered),
            findings=findings,
        )
    return EventAnalysis(
        event_offset=event.offset,
        event_secuencia=event.secuencia,
        sensors=sensors,
    )


def analyze_file(result) -> List[EventAnalysis]:
    """Analyze every event of a FileResult (or a plain event list)."""
    from .records import FileResult
    events = result.events if isinstance(result, FileResult) else result
    return [analyze_event(e) for e in events]


def check_magnitude(event: EventResult):
    """MPU stored_magnitude vs sqrt(x^2+y^2+z^2); mismatches reported."""
    out = []
    for idx, rec in enumerate(event.records):
        if rec.tipo_sensor != L.SENSOR_MPU or len(rec.datos) < 4:
            continue
        x, y, z, stored = rec.datos[0], rec.datos[1], rec.datos[2], rec.datos[3]
        computed = math.sqrt(x * x + y * y + z * z)
        tol = max(1e-3, abs(computed) * 1e-4)
        if abs(stored - computed) > tol:
            out.append(Finding(
                kind="magnitude_mismatch",
                source_file=event.archivo,
                event_offset=event.offset,
                event_secuencia=event.secuencia,
                sensor=L.SENSOR_MPU,
                cur_secuencia=rec.secuencia,
                cur_timestamp_us=rec.timestamp_us,
                detail="magnitud almacenada %.6f vs calculada %.6f"
                       % (stored, computed),
            ))
    return out


def sensor_summary(analyses: List[EventAnalysis], sensor: int) -> IntervalStats:
    stamps = []
    for a in analyses:
        if sensor in a.sensors:
            s = a.sensors[sensor].stats
            if s.sample_count:
                stamps.append((s.first_us, s.last_us))
    flat = [t for pair in stamps for t in pair]
    return _stats(sorted(flat))


def aggregate_observed_frequency(interval_stats: List[IntervalStats]) -> float:
    """Combine per-event observed rates without counting gaps between events.

    Each event contributes only its own sample intervals and timestamp span;
    pauses between events are not treated as sensor intervals.
    """
    usable = [stats for stats in interval_stats
              if stats.sample_count > 1 and stats.last_us > stats.first_us]
    total_intervals = sum(stats.sample_count - 1 for stats in usable)
    total_span_us = sum(stats.last_us - stats.first_us for stats in usable)
    if total_intervals <= 0 or total_span_us <= 0:
        return 0.0
    return total_intervals * 1_000_000.0 / total_span_us

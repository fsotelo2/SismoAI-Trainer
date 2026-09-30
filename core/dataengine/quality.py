"""Quality summaries over parsed content (no resampling, no repair).

Counts valid/invalid/truncated events, CRC/commit failures, and records
per sensor; carries analysis findings through for UI reporting.
"""

from dataclasses import dataclass, field
from typing import Dict, List

from .analysis import Finding, IntervalStats, analyze_event, check_magnitude
from .records import EventResult, FileResult


@dataclass(frozen=True)
class EventQuality:
    secuencia: int
    offset: int
    valido: bool
    crc_valido: bool
    commit_valido: bool
    truncado: bool
    total_records: int
    records_by_sensor: Dict[int, int]
    frequency: Dict[int, IntervalStats]
    findings: List[Finding]


@dataclass(frozen=True)
class FileQuality:
    archivo: str
    event_count: int
    valid_count: int
    invalid_count: int
    truncated_count: int
    total_records: int
    records_by_sensor: Dict[int, int]
    crc_failures: int
    commit_failures: int
    valido: bool
    truncado: bool
    events: List[EventQuality]
    findings: List[Finding]
    razones: List[str]


def summarize_event(event: EventResult) -> EventQuality:
    by_sensor: Dict[int, int] = {}
    for r in event.records:
        by_sensor[r.tipo_sensor] = by_sensor.get(r.tipo_sensor, 0) + 1
    analysis = analyze_event(event)
    flat = [f for s in analysis.sensors.values() for f in s.findings]
    flat.extend(check_magnitude(event))
    return EventQuality(
        secuencia=event.secuencia,
        offset=event.offset,
        valido=event.valido,
        crc_valido=event.crc_valido,
        commit_valido=event.commit_valido,
        truncado=event.truncado,
        total_records=len(event.records),
        records_by_sensor=by_sensor,
        frequency={s: sa.stats for s, sa in analysis.sensors.items()},
        findings=flat,
    )


def summarize_file(result: FileResult) -> FileQuality:
    events = [summarize_event(e) for e in result.events]
    by_sensor: Dict[int, int] = {}
    for eq in events:
        for sensor, n in eq.records_by_sensor.items():
            by_sensor[sensor] = by_sensor.get(sensor, 0) + n
    findings = [f for eq in events for f in eq.findings]
    return FileQuality(
        archivo=result.archivo,
        event_count=len(events),
        valid_count=sum(1 for e in events if e.valido),
        invalid_count=sum(1 for e in events
                          if not e.valido and not e.truncado),
        truncated_count=sum(1 for e in events if e.truncado),
        total_records=sum(e.total_records for e in events),
        records_by_sensor=by_sensor,
        crc_failures=sum(1 for e in result.events if not e.crc_valido),
        commit_failures=sum(1 for e in result.events if not e.commit_valido),
        valido=result.valido,
        truncado=result.truncado,
        events=events,
        findings=findings,
        razones=list(result.razones),
    )
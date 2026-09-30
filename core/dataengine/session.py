"""Multi-file session loading and aggregation.

Discovers DAT_XXXXXX.BIN files in a directory (deterministic numeric
order), parses each independently, and aggregates quality results.
Samples and events are never merged across files. Source files are
only read.
"""

import os
import re
from dataclasses import dataclass, field
from typing import Dict, List

from .analysis import Finding
from .quality import FileQuality, summarize_file
from .records import FileResult
from .parser import parse_file

DAT_PATTERN = re.compile(r"^DAT_(\d{6})\.BIN$")


@dataclass(frozen=True)
class FrequencyPoint:
    source_file: str
    event_secuencia: int
    sensor: int
    observed_hz: float
    sample_count: int


@dataclass(frozen=True)
class FileEntry:
    path: str
    sequence: int
    status: str  # "ok" | "error"
    error: str
    quality: FileQuality


@dataclass(frozen=True)
class SessionSummary:
    directory: str
    files: List[FileEntry]
    ignored: List[str]
    file_count: int
    event_count: int
    valid_events: int
    invalid_events: int
    truncated_events: int
    total_records: int
    records_by_sensor: Dict[int, int]
    crc_failures: int
    commit_failures: int
    frequencies: List[FrequencyPoint]
    findings: List[Finding]
    valido: bool


def discover(directory: str) -> List[str]:
    found = []
    with os.scandir(directory) as it:
        for entry in it:
            if not entry.is_file():
                continue
            m = DAT_PATTERN.match(entry.name)
            if m:
                found.append((int(m.group(1)), entry.path))
    found.sort(key=lambda t: t[0])
    return [path for _, path in found]


def _file_sequence(path: str) -> int:
    m = DAT_PATTERN.match(os.path.basename(path))
    return int(m.group(1)) if m else 0


def _parse_one(path: str, sequence: int) -> FileEntry:
    try:
        result: FileResult = parse_file(path)
    except OSError as exc:
        return FileEntry(path, sequence, "error", "no se pudo leer: %s" % exc,
                         None)
    return FileEntry(path, sequence, "ok", "", summarize_file(result))


def aggregate_entries(directory: str, entries: List[FileEntry],
                      ignored=None) -> SessionSummary:
    ok = [e for e in entries if e.status == "ok" and e.quality is not None]
    records_by_sensor: Dict[int, int] = {}
    for e in ok:
        for sensor, n in e.quality.records_by_sensor.items():
            records_by_sensor[sensor] = records_by_sensor.get(sensor, 0) + n
    # Per-event observed frequencies with traceability. Qualities carry
    # findings but not full analyses, so each file is parsed once more
    # here (read-only); Phase 4+ can thread analyses through instead.
    from .analysis import analyze_event
    frequencies: List[FrequencyPoint] = []
    for e in ok:
        try:
            result = parse_file(e.path)
        except OSError:
            continue
        for ev in result.events:
            analysis = analyze_event(ev)
            for sensor, sa in analysis.sensors.items():
                frequencies.append(FrequencyPoint(
                    source_file=e.path,
                    event_secuencia=ev.secuencia,
                    sensor=sensor,
                    observed_hz=sa.stats.observed_hz,
                    sample_count=sa.stats.sample_count,
                ))
    findings: List[Finding] = []
    for e in ok:
        findings.extend(e.quality.findings)
    valido = (all(e.status == "ok" for e in entries)
              and all(e.quality.valido for e in ok))
    return SessionSummary(
        directory=directory,
        files=list(entries),
        ignored=sorted(ignored) if ignored else [],
        file_count=len(entries),
        event_count=sum(e.quality.event_count for e in ok),
        valid_events=sum(e.quality.valid_count for e in ok),
        invalid_events=sum(e.quality.invalid_count for e in ok),
        truncated_events=sum(e.quality.truncated_count for e in ok),
        total_records=sum(e.quality.total_records for e in ok),
        records_by_sensor=records_by_sensor,
        crc_failures=sum(e.quality.crc_failures for e in ok),
        commit_failures=sum(e.quality.commit_failures for e in ok),
        frequencies=frequencies,
        findings=findings,
        valido=valido,
    )


def load_session(directory: str) -> SessionSummary:
    paths = discover(directory)
    names = {os.path.basename(p) for p in paths}
    ignored = sorted(
        e.name for e in os.scandir(directory)
        if e.is_file() and e.name not in names)
    entries = [_parse_one(p, _file_sequence(p)) for p in paths]
    return aggregate_entries(directory, entries, ignored)

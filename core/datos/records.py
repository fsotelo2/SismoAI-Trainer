"""Presentation-neutral records assembled from dataengine outputs."""

from dataclasses import dataclass, field
from typing import List


SHA256_PENDING = "Calculando…"


@dataclass(frozen=True)
class EventRow:
    number: int
    sequence: int
    start_text: str
    duration_text: str
    geophone_hz_text: str
    mpu_hz_text: str
    status_code: str
    status_text: str


@dataclass(frozen=True)
class BinFileRow:
    path: str
    name: str
    sequence: int
    capture_date_text: str
    event_count_text: str
    duration_text: str
    size_text: str
    size_detail_text: str
    status_code: str
    status_text: str
    format_version_text: str
    capture_detail_text: str
    geophone_frequency_text: str
    mpu_frequency_text: str
    sha256_text: str
    modified_text: str
    errors: List[str] = field(default_factory=list)
    events: List[EventRow] = field(default_factory=list)
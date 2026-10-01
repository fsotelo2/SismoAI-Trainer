"""Domain models for traceable signal windows (Phase 6).

The model stores temporal bounds and provenance, not copies of source BIN data.
Times are integer microseconds in the source event's relative time base.
"""
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Mapping, Optional, Tuple


QUALITY_ACCEPTED = "accepted"
QUALITY_REVIEW = "review"
QUALITY_BLOCKED = "blocked"

SELECTION_INCLUDE = "include"
SELECTION_REVIEW = "review"
SELECTION_EXCLUDE = "exclude"

ORIGIN_FIXED = "fixed"
ORIGIN_SLIDING = "sliding"
ORIGIN_MANUAL = "manual"


@dataclass(frozen=True)
class SensorSamplingInfo:
    """Observed sampling metadata for one sensor."""
    sample_count: int
    observed_hz: Optional[float] = None
    start_us: Optional[int] = None
    end_us: Optional[int] = None


@dataclass(frozen=True)
class WindowQuality:
    """Technical quality state; deliberately separate from semantic labels."""
    status: str = QUALITY_ACCEPTED
    findings: Tuple[str, ...] = ()


@dataclass
class WindowRecord:
    """One derived interval with stable identity and complete provenance."""
    window_id: str
    source_file: str
    source_event_id: Optional[str]
    origin_mode: str
    start_us: int
    end_us: int
    sensors: Tuple[str, ...]
    samples: Dict[str, int] = field(default_factory=dict)
    sample_ranges: Dict[str, Tuple[int, int]] = field(default_factory=dict)
    sampling_info: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    quality: WindowQuality = field(default_factory=WindowQuality)
    window_config: Dict[str, Any] = field(default_factory=dict)
    selection_status: str = SELECTION_INCLUDE
    extractor_version: str = "0.2.0"
    source_hash: Optional[str] = None
    event_interval: Optional[Dict[str, int]] = None
    notes: str = ""

    @property
    def duration_ms(self) -> float:
        return (self.end_us - self.start_us) / 1000.0

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-compatible representation."""
        result = asdict(self)
        result["duration_ms"] = self.duration_ms
        result["sensors"] = list(self.sensors)
        result["quality"]["findings"] = list(self.quality.findings)
        return result

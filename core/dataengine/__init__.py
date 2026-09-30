"""DATASET BIN v2 data engine (Phase 3).

Public entry points: parse_file, analyze_event/analyze_file,
summarize_event/summarize_file, event_series and friends, discover,
load_session. Reads only; never modifies source files.
"""

from .analysis import (
    EventAnalysis,
    Finding,
    IntervalStats,
    SensorAnalysis,
    aggregate_observed_frequency,
    analyze_event,
    analyze_file,
    check_magnitude,
    sensor_summary,
)
from .parser import parse_file
from .quality import EventQuality, FileQuality, summarize_event, summarize_file
from .session import (
    FileEntry,
    FrequencyPoint,
    SessionSummary,
    aggregate_entries,
    discover,
    load_session,
)
from .records import (
    ContainerHeader,
    EventHeader,
    EventResult,
    FileResult,
    FrequencyCheck,
    Metadata,
    SensorRecord,
)
from .series import (
    CHANNEL_ADC,
    CHANNEL_MAGNITUDE,
    CHANNEL_VELOCITY,
    CHANNEL_VOLTAGE,
    Sample,
    Series,
    event_series,
    geophone_adc,
    geophone_velocity,
    geophone_voltage,
    mpu_magnitude_series,
)

__all__ = [
    "parse_file",
    "analyze_event",
    "analyze_file",
    "check_magnitude",
    "sensor_summary",
    "aggregate_observed_frequency",
    "EventAnalysis",
    "Finding",
    "IntervalStats",
    "SensorAnalysis",
    "ContainerHeader",
    "EventHeader",
    "EventResult",
    "FileResult",
    "FrequencyCheck",
    "Metadata",
    "SensorRecord",
    "event_series",
    "geophone_velocity",
    "geophone_voltage",
    "geophone_adc",
    "mpu_magnitude_series",
    "Series",
    "Sample",
    "CHANNEL_VELOCITY",
    "CHANNEL_VOLTAGE",
    "CHANNEL_ADC",
    "CHANNEL_MAGNITUDE",
    "EventQuality",
    "FileQuality",
    "summarize_event",
    "summarize_file",
    "FileEntry",
    "FrequencyPoint",
    "SessionSummary",
    "aggregate_entries",
    "discover",
    "load_session",
]
"""Phase 6: traceable windowing domain and interval engine."""
from .engine import (
    WindowSpec, WindowingError, build_window, evaluate_structure,
    generate_intervals, seconds_to_us, validate_interval, validate_sensors,
)
from .models import WindowRecord, WindowQuality

__all__ = [
    "WindowSpec", "WindowingError", "WindowRecord", "WindowQuality",
    "build_window", "evaluate_structure", "generate_intervals",
    "seconds_to_us", "validate_interval", "validate_sensors",
]

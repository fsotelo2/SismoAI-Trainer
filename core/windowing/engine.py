"""Deterministic interval generation and validation for Phase 6.

This layer handles temporal geometry only. It does not classify seismicity,
modify signal values, resample, interpolate, or define scientific thresholds.
"""
from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence, Tuple

from .models import (
    ORIGIN_FIXED, ORIGIN_MANUAL, ORIGIN_SLIDING,
    QUALITY_ACCEPTED, QUALITY_BLOCKED, QUALITY_REVIEW,
    SELECTION_INCLUDE, WindowQuality, WindowRecord,
)

MICROSECONDS_PER_SECOND = 1_000_000


class WindowingError(ValueError):
    """Invalid window configuration or requested interval."""


@dataclass(frozen=True)
class WindowSpec:
    duration_us: int
    step_us: Optional[int] = None
    mode: str = ORIGIN_FIXED
    discard_partial: bool = True

    def validate(self) -> None:
        if self.mode not in (ORIGIN_FIXED, ORIGIN_SLIDING):
            raise WindowingError("El modo debe ser fixed o sliding.")
        if not isinstance(self.duration_us, int) or self.duration_us <= 0:
            raise WindowingError("La duración debe ser un entero positivo en microsegundos.")
        step = self.step_us if self.step_us is not None else self.duration_us
        if not isinstance(step, int) or step <= 0:
            raise WindowingError("El paso debe ser un entero positivo en microsegundos.")
        if self.mode == ORIGIN_FIXED and step != self.duration_us:
            raise WindowingError("En modo fijo, el paso debe ser igual a la duración.")
        if self.mode == ORIGIN_SLIDING and step > self.duration_us:
            raise WindowingError("En modo deslizante, el paso no puede superar la duración.")


def seconds_to_us(seconds: float) -> int:
    """Convert finite seconds to nearest integer microsecond."""
    import math
    value = float(seconds)
    if not math.isfinite(value):
        raise WindowingError("El tiempo debe ser finito.")
    return int(round(value * MICROSECONDS_PER_SECOND))


def validate_interval(start_us: int, end_us: int,
                      bounds: Tuple[int, int]) -> None:
    """Require a non-empty interval fully contained in source bounds."""
    lower, upper = bounds
    if end_us <= start_us:
        raise WindowingError("El intervalo debe tener duración positiva.")
    if upper <= lower:
        raise WindowingError("El intervalo de origen no es válido.")
    if start_us < lower or end_us > upper:
        raise WindowingError("El intervalo está fuera de los límites del registro.")


def generate_intervals(start_us: int, end_us: int,
                       spec: WindowSpec) -> List[Tuple[int, int]]:
    """Generate consecutive fixed/sliding intervals; final partial is discarded."""
    spec.validate()
    validate_interval(start_us, end_us, (start_us, end_us))
    step = spec.step_us if spec.step_us is not None else spec.duration_us
    intervals = []
    cursor = start_us
    while cursor + spec.duration_us <= end_us:
        intervals.append((cursor, cursor + spec.duration_us))
        cursor += step
    # Phase 6 approved default: do not keep an incomplete tail window.
    return intervals


def validate_sensors(requested: Iterable[str],
                     available: Iterable[str]) -> Tuple[str, ...]:
    """Validate sensor selection against known available sensors."""
    allowed = {"GEO", "MPU"}
    available_set = set(available)
    chosen = tuple(dict.fromkeys(str(item).upper() for item in requested))
    if not chosen:
        raise WindowingError("Seleccione al menos un sensor.")
    if any(item not in allowed for item in chosen):
        raise WindowingError("Sensor no reconocido; use GEO o MPU.")
    missing = [item for item in chosen if item not in available_set]
    if missing:
        raise WindowingError("Sensor no disponible: " + ", ".join(missing))
    return chosen


def evaluate_structure(start_us: int, end_us: int,
                       bounds: Tuple[int, int],
                       sensors: Sequence[str],
                       sample_counts: Optional[dict] = None) -> WindowQuality:
    """Evaluate only structural validity; no unvalidated scientific thresholds."""
    try:
        validate_interval(start_us, end_us, bounds)
    except WindowingError as exc:
        return WindowQuality(QUALITY_BLOCKED, (str(exc),))
    if not sensors:
        return WindowQuality(QUALITY_BLOCKED, ("No hay sensores incluidos.",))
    counts = sample_counts or {}
    if any(counts.get(sensor, 0) <= 0 for sensor in sensors):
        return WindowQuality(QUALITY_BLOCKED,
                             ("Hay sensores incluidos sin muestras en el intervalo.",))
    return WindowQuality(QUALITY_ACCEPTED, ())


def build_window(window_id: str, source_file: str,
                 source_event_id: Optional[str], origin_mode: str,
                 start_us: int, end_us: int, sensors: Sequence[str],
                 config: Optional[dict] = None,
                 sample_counts: Optional[dict] = None,
                 quality: Optional[WindowQuality] = None) -> WindowRecord:
    """Create common output shape for automatic and manual intervals."""
    if origin_mode not in (ORIGIN_FIXED, ORIGIN_SLIDING, ORIGIN_MANUAL):
        raise WindowingError("Origen de ventana no reconocido.")
    if not window_id or not source_file:
        raise WindowingError("La ventana requiere ID y archivo de origen.")
    if end_us <= start_us:
        raise WindowingError("El intervalo debe tener duración positiva.")
    counts = dict(sample_counts or {})
    state = quality or WindowQuality(QUALITY_ACCEPTED, ())
    return WindowRecord(
        window_id=window_id,
        source_file=source_file,
        source_event_id=source_event_id,
        origin_mode=origin_mode,
        start_us=start_us,
        end_us=end_us,
        sensors=tuple(sensors),
        samples=counts,
        window_config=dict(config or {}),
        quality=state,
    )

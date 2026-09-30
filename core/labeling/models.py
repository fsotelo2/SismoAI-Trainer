"""Domain models for human-reviewed window labeling (Phase 7)."""
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional

# The primary label is strictly binary. "INDETERMINADO" is a secondary
# category for NO_SISMICO, never a primary class.
CLASS_TREMOR = 0
CLASS_NON_SEISMIC = 1
OFFICIAL_CLASSES = {
    CLASS_TREMOR: "TEMBLOR",
    CLASS_NON_SEISMIC: "NO_SISMICO",
}
SECONDARY_UNDETERMINED = "INDETERMINADO"
SOURCE_HUMAN = "human"
SOURCE_AUTOMATIC = "automatic"
REVIEW_PENDING = "pending"
REVIEW_CONFIRMED = "confirmed"
REVIEW_REJECTED = "rejected"


class LabelingError(ValueError):
    """Raised when an annotation violates the Phase 7 contract."""


def utc_now():
    return datetime.now(timezone.utc).isoformat()


@dataclass
class WindowLabel:
    """One binary semantic annotation per window; null class means pending."""
    window_id: str
    class_code: Optional[int] = None
    label_source: str = SOURCE_HUMAN
    confidence: Optional[float] = None
    disturbance: Optional[str] = None
    quality_review: str = REVIEW_PENDING
    reviewer: Optional[str] = None
    observations: str = ""
    sensor_attributes: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)
    schema_version: int = 1

    def validate(self):
        if not isinstance(self.window_id, str) or not self.window_id.strip():
            raise LabelingError("window_id es obligatorio.")
        if isinstance(self.schema_version, bool) or self.schema_version != 1:
            raise LabelingError("schema_version no compatible; se requiere versión 1.")
        if self.class_code is not None and (
            isinstance(self.class_code, bool)
            or not isinstance(self.class_code, int)
            or self.class_code not in OFFICIAL_CLASSES
        ):
            raise LabelingError("La clase principal debe ser 0 (TEMBLOR) o 1 (NO_SISMICO).")
        if self.label_source not in (SOURCE_HUMAN, SOURCE_AUTOMATIC):
            raise LabelingError("label_source debe ser human o automatic.")
        if self.confidence is not None:
            if (
                isinstance(self.confidence, bool)
                or not isinstance(self.confidence, (int, float))
                or not 0 <= self.confidence <= 1
            ):
                raise LabelingError("confidence debe estar entre 0 y 1.")
        if self.quality_review not in (REVIEW_PENDING, REVIEW_CONFIRMED, REVIEW_REJECTED):
            raise LabelingError("Estado de revisión no válido.")
        if self.disturbance is not None:
            if self.disturbance != SECONDARY_UNDETERMINED:
                raise LabelingError("Categoría secundaria no reconocida; use INDETERMINADO.")
            if self.class_code != CLASS_NON_SEISMIC:
                raise LabelingError("La categoría secundaria solo aplica a NO_SISMICO.")
        if not isinstance(self.observations, str) or len(self.observations) > 200:
            raise LabelingError("Las observaciones deben tener como máximo 200 caracteres.")
        if not isinstance(self.sensor_attributes, dict):
            raise LabelingError("sensor_attributes debe ser un objeto.")
        return self

    def to_dict(self):
        self.validate()
        return asdict(self)

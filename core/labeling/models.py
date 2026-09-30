"""Domain models for human-reviewed window labeling (Phase 7)."""
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional

CLASS_TREMOR = 0
CLASS_NON_SEISMIC = 1
CLASS_UNDETERMINED = 2
OFFICIAL_CLASSES = {
    CLASS_TREMOR: "TEMBLOR",
    CLASS_NON_SEISMIC: "NO_SISMICO",
    CLASS_UNDETERMINED: "INDETERMINADO",
}
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
    """One primary semantic annotation per window; null class means unlabeled."""
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
        if self.class_code is not None and self.class_code not in OFFICIAL_CLASSES:
            raise LabelingError("Código de clase no oficial.")
        if self.label_source not in (SOURCE_HUMAN, SOURCE_AUTOMATIC):
            raise LabelingError("label_source debe ser human o automatic.")
        if self.confidence is not None:
            if isinstance(self.confidence, bool) or not isinstance(self.confidence, (int, float)) or not 0 <= self.confidence <= 1:
                raise LabelingError("confidence debe estar entre 0 y 1.")
        if self.quality_review not in (REVIEW_PENDING, REVIEW_CONFIRMED, REVIEW_REJECTED):
            raise LabelingError("Estado de revisión no válido.")
        if not isinstance(self.sensor_attributes, dict):
            raise LabelingError("sensor_attributes debe ser un objeto.")
        return self

    def to_dict(self):
        self.validate()
        return asdict(self)

"""Application service for Phase 7 window labeling."""
from copy import deepcopy
from core.labeling.models import (
    WindowLabel, LabelingError, CLASS_NON_SEISMIC, REVIEW_PENDING, utc_now,
)
from core.labeling import persistence


class LabelingService:
    """Owns annotation state and persists it independently from source BIN files."""

    def __init__(self, path=None):
        self.path = path or persistence.default_path()
        restored = persistence.load(self.path) or {}
        self.workspace = restored.get("workspace", {})
        self.labels = {}
        for window_id, raw in (restored.get("labels") or {}).items():
            try:
                label = WindowLabel(**raw)
                if label.window_id == window_id:
                    label.validate()
                    self.labels[window_id] = label.to_dict()
            except (TypeError, ValueError):
                continue

    def list_labels(self, windows):
        result = []
        for window in windows:
            wid = window.get("window_id")
            if not wid:
                continue
            label = self.labels.get(wid)
            result.append({"window": deepcopy(window), "label": deepcopy(label)})
        return result

    def remove_labels(self, window_ids):
        """Remove persisted annotations for a set of window IDs."""
        ids = set(window_ids or ())
        if not ids:
            return
        candidate = {key: value for key, value in self.labels.items() if key not in ids}
        workspace = {"schema_version": 1, "updated_at": utc_now()}
        persistence.save(self.path, workspace, candidate)
        self.labels = candidate
        self.workspace = workspace

    def get_label(self, window_id):
        return deepcopy(self.labels.get(window_id))

    def save_label(self, window, payload):
        if not isinstance(window, dict) or not window.get("window_id"):
            raise LabelingError("Ventana no válida.")
        if not isinstance(payload, dict):
            raise LabelingError("La etiqueta debe ser un objeto.")
        wid = window["window_id"]
        previous = self.labels.get(wid) or {}
        category = payload.get("disturbance")
        if payload.get("class_code") != CLASS_NON_SEISMIC:
            category = None
        label = WindowLabel(
            window_id=wid,
            class_code=payload.get("class_code"),
            label_source="human",
            confidence=None,
            disturbance=category,
            quality_review=payload.get("quality_review", REVIEW_PENDING),
            reviewer=payload.get("reviewer"),
            observations=payload.get("observations", ""),
            sensor_attributes=previous.get("sensor_attributes", {}),
            created_at=previous.get("created_at", utc_now()),
            updated_at=utc_now(),
        ).validate()
        candidate = dict(self.labels)
        candidate[wid] = label.to_dict()
        workspace = {"schema_version": 1, "updated_at": utc_now()}
        persistence.save(self.path, workspace, candidate)
        self.labels = candidate
        self.workspace = workspace
        return deepcopy(candidate[wid])


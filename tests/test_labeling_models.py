import json

import pytest

from core.labeling.models import (
    OFFICIAL_CLASSES, LabelingError, WindowLabel,
    SOURCE_AUTOMATIC, REVIEW_CONFIRMED,
)
from core.labeling import persistence


def test_official_classes_are_stable():
    assert OFFICIAL_CLASSES == {0: "TEMBLOR", 1: "NO_SISMICO", 2: "INDETERMINADO"}


def test_unlabeled_window_is_valid():
    label = WindowLabel(window_id="W-001").validate()
    assert label.class_code is None
    assert label.label_source == "human"


@pytest.mark.parametrize("code", [-1, 3, "0", True])
def test_rejects_non_official_class_code(code):
    with pytest.raises(LabelingError):
        WindowLabel(window_id="W-001", class_code=code).validate()


def test_valid_automatic_suggestion_can_be_marked_confirmed():
    label = WindowLabel(
        window_id="W-002", class_code=0,
        label_source=SOURCE_AUTOMATIC, confidence=0.82,
        quality_review=REVIEW_CONFIRMED,
    ).validate()
    assert label.to_dict()["label_source"] == "automatic"


@pytest.mark.parametrize("confidence", [-0.1, 1.1, "high", True])
def test_rejects_invalid_confidence(confidence):
    with pytest.raises(LabelingError):
        WindowLabel(window_id="W-001", confidence=confidence).validate()


def test_labeling_persistence_roundtrip_and_schema(tmp_path):
    path = tmp_path / "labeling.json"
    workspace = {"workspace_id": "ws-1", "window_ids": ["W-001"]}
    labels = {"W-001": WindowLabel(window_id="W-001", class_code=2).to_dict()}
    persistence.save(str(path), workspace, labels)
    restored = persistence.load(str(path))
    assert restored["workspace"] == workspace
    assert restored["labels"] == labels
    assert restored["schema"] == "sismoai-labeling"


def test_invalid_schema_returns_none(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text(json.dumps({"schema": "wrong"}), encoding="utf-8")
    assert persistence.load(str(path)) is None

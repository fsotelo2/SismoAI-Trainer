"""Contract tests for Phase 7 labeling domain and persistence (unittest)."""
import json
import tempfile
import unittest
from pathlib import Path

from core.labeling.models import (
    OFFICIAL_CLASSES, LabelingError, WindowLabel,
    SOURCE_AUTOMATIC, REVIEW_CONFIRMED,
)
from core.labeling import persistence


class LabelingModelContractTests(unittest.TestCase):
    def test_official_classes_are_binary_and_stable(self):
        self.assertEqual(OFFICIAL_CLASSES, {0: "TEMBLOR", 1: "NO_SISMICO"})

    def test_unlabeled_window_is_valid(self):
        label = WindowLabel(window_id="W-001").validate()
        self.assertIsNone(label.class_code)
        self.assertEqual(label.label_source, "human")

    def test_rejects_non_official_class_code(self):
        for code in (-1, 2, 3, "0", True):
            with self.subTest(code=code), self.assertRaises(LabelingError):
                WindowLabel(window_id="W-001", class_code=code).validate()

    def test_valid_automatic_suggestion_can_be_marked_confirmed(self):
        label = WindowLabel(
            window_id="W-002", class_code=0,
            label_source=SOURCE_AUTOMATIC, confidence=0.82,
            quality_review=REVIEW_CONFIRMED,
        ).validate()
        self.assertEqual(label.to_dict()["label_source"], "automatic")

    def test_rejects_invalid_confidence(self):
        for confidence in (-0.1, 1.1, "high", True):
            with self.subTest(confidence=confidence), self.assertRaises(LabelingError):
                WindowLabel(window_id="W-001", confidence=confidence).validate()

    def test_labeling_persistence_roundtrip_and_schema(self):
        with tempfile.TemporaryDirectory() as folder:
            path = str(Path(folder) / "labeling.json")
            workspace = {"workspace_id": "ws-1", "window_ids": ["W-001"]}
            labels = {"W-001": WindowLabel(window_id="W-001", class_code=1).to_dict()}
            persistence.save(path, workspace, labels)
            restored = persistence.load(path)
            self.assertEqual(restored["workspace"], workspace)
            self.assertEqual(restored["labels"], labels)
            self.assertEqual(restored["schema"], "sismoai-labeling")

    def test_invalid_schema_returns_none(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "bad.json"
            path.write_text(json.dumps({"schema": "wrong"}), encoding="utf-8")
            self.assertIsNone(persistence.load(str(path)))


if __name__ == "__main__":
    unittest.main()

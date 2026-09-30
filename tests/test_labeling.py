"""Unit tests for Phase 7 label model and persistence."""
import os
import tempfile
import unittest

from core.labeling.models import (
    WindowLabel, LabelingError, CLASS_TREMOR, CLASS_NON_SEISMIC,
    SECONDARY_UNDETERMINED,
)
from core.labeling.service import LabelingService


class WindowLabelTests(unittest.TestCase):
    def test_binary_primary_classes_are_valid(self):
        self.assertEqual(WindowLabel("W-001", class_code=CLASS_TREMOR).validate().class_code, 0)
        self.assertEqual(WindowLabel("W-002", class_code=CLASS_NON_SEISMIC).validate().class_code, 1)

    def test_third_primary_class_is_rejected(self):
        with self.assertRaises(LabelingError):
            WindowLabel("W-001", class_code=2).validate()

    def test_undetermined_is_secondary_only_for_non_seismic(self):
        with self.assertRaises(LabelingError):
            WindowLabel("W-001", class_code=CLASS_TREMOR,
                        disturbance=SECONDARY_UNDETERMINED).validate()
        self.assertEqual(
            WindowLabel("W-002", class_code=CLASS_NON_SEISMIC,
                        disturbance=SECONDARY_UNDETERMINED).validate().disturbance,
            SECONDARY_UNDETERMINED,
        )

    def test_observations_are_limited_to_200_characters(self):
        with self.assertRaises(LabelingError):
            WindowLabel("W-001", observations="x" * 201).validate()

    def test_null_class_is_a_valid_pending_annotation(self):
        self.assertIsNone(WindowLabel("W-001").validate().class_code)

    def test_boolean_is_not_accepted_as_integer_class(self):
        with self.assertRaises(LabelingError):
            WindowLabel("W-001", class_code=True).validate()

    def test_unknown_secondary_category_is_rejected(self):
        with self.assertRaises(LabelingError):
            WindowLabel("W-001", class_code=CLASS_NON_SEISMIC,
                        disturbance="RUIDO").validate()

    def test_category_is_rejected_for_pending_window(self):
        with self.assertRaises(LabelingError):
            WindowLabel("W-001", class_code=None,
                        disturbance=SECONDARY_UNDETERMINED).validate()


class LabelingPersistenceTests(unittest.TestCase):
    def test_save_and_restore_label(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "labels.json")
            service = LabelingService(path)
            window = {"window_id": "W-001"}
            saved = service.save_label(window, {
                "class_code": CLASS_NON_SEISMIC,
                "disturbance": SECONDARY_UNDETERMINED,
                "quality_review": "confirmed",
                "observations": "Revisado",
            })
            restored = LabelingService(path).get_label("W-001")
            self.assertEqual(saved["class_code"], 1)
            self.assertEqual(restored["disturbance"], SECONDARY_UNDETERMINED)
            self.assertEqual(restored["observations"], "Revisado")


if __name__ == "__main__":
    unittest.main()

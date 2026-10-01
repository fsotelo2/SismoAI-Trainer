"""Tests for Phase 9 model training utilities."""
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from core.models.trainer import _metrics, build_network, train_experiment


class ModelMetricsTests(unittest.TestCase):
    def test_confusion_and_macro_metrics(self):
        result = _metrics([0, 0, 1, 1], [0, 1, 1, 1])
        self.assertEqual(result["confusion_matrix"], [[1, 1], [0, 2]])
        self.assertEqual(result["accuracy"], 0.75)
        self.assertAlmostEqual(result["per_class"][0]["recall"], 0.5)
        self.assertEqual(result["samples"], 4)

    def test_metric_empty_input_is_defined(self):
        result = _metrics([], [])
        self.assertEqual(result["accuracy"], 0.0)
        self.assertEqual(result["confusion_matrix"], [[0, 0], [0, 0]])


class ModelTrainingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            import torch  # noqa: F401
        except ImportError:
            raise unittest.SkipTest("PyTorch no instalado; prueba de entrenamiento omitida.")

    def test_network_shapes_for_catalog(self):
        import torch
        for architecture in ("1d_cnn", "feature_classifier", "baseline"):
            model = build_network(architecture, channels=2, points=32)
            output = model(torch.zeros((3, 2, 32)))
            self.assertEqual(tuple(output.shape), (3, 2))

    def test_train_writes_checkpoint_history_and_metrics(self):
        rng = np.random.default_rng(7)
        x = rng.normal(size=(8, 2, 32)).astype(np.float32)
        y = np.asarray([0, 1] * 4, dtype=np.int64)
        config = {
            "architecture": "1d_cnn",
            "training": {"seed": 3, "epochs": 2, "batch_size": 4,
                         "learning_rate": 0.001, "optimizer": "adam",
                         "early_stopping": False, "save_best": True,
                         "class_weighting": False},
        }
        with tempfile.TemporaryDirectory() as tmp:
            result = train_experiment(config, {
                "train": (x, y), "validation": (x[:4], y[:4]),
                "test": (x[4:], y[4:]),
            }, tmp)
            self.assertEqual(result["status"], "trained")
            self.assertEqual(result["epochs_completed"], 2)
            self.assertTrue(Path(result["weights_path"]).is_file())
            self.assertTrue((Path(tmp) / "training_result.json").is_file())
            saved = json.loads((Path(tmp) / "training_result.json").read_text())
            self.assertIn("confusion_matrix", saved["metrics"]["test"])
            self.assertIn("loss", saved["metrics"]["validation"])


if __name__ == "__main__":
    unittest.main()

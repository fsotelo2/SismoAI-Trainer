"""Tests for Phase 9 model training utilities."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))
if str(_project_root / "core") not in sys.path:
    sys.path.insert(0, str(_project_root / "core"))

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


class ModelDatasetCatalogTests(unittest.TestCase):
    def test_modelos_js_has_valid_syntax(self):
        js_path = Path(__file__).resolve().parent.parent / "ui" / "js" / "modelos.js"
        self.assertTrue(js_path.is_file(), "ui/js/modelos.js must exist")
        content = js_path.read_text(encoding="utf-8")
        self.assertNotIn("1d_cnn:", content, "1d_cnn must be quoted in object literals to avoid SyntaxError")
        try:
            import subprocess
            res = subprocess.run(["node", "-c", str(js_path)], capture_output=True, text=True)
            self.assertEqual(res.returncode, 0, f"Syntax error in modelos.js: {res.stderr}")
        except FileNotFoundError:
            pass

    def test_catalog_detection_and_selection_in_dataset_folder(self):
        from bridge.api_bridge import ApiBridge
        with tempfile.TemporaryDirectory() as tmp_dir:
            dataset_dir = Path(tmp_dir) / "Dataset"
            dataset_dir.mkdir(parents=True, exist_ok=True)
            manifest_payload = {
                "schema": "sismoai-dataset",
                "schema_version": 1,
                "dataset_id": "test-dataset-uuid-1234",
                "name": "Dataset_Prueba_01",
                "created_at": "2026-09-30T21:00:00Z",
                "splits": {
                    "train": [{"window_id": "W-001", "class_code": 0}],
                    "validation": [{"window_id": "W-002", "class_code": 1}],
                    "test": [{"window_id": "W-003", "class_code": 0}],
                },
                "summary": {
                    "all": {"windows": 3, "classes": {"0": 2, "1": 1}},
                    "train": {"windows": 1},
                    "validation": {"windows": 1},
                    "test": {"windows": 1},
                },
            }
            manifest_file = dataset_dir / "Dataset_Prueba_01.json"
            manifest_file.write_text(json.dumps(manifest_payload), encoding="utf-8")

            bridge = ApiBridge()
            bridge._dataset_dir = str(dataset_dir)
            bridge._dataset_path = str(manifest_file)
            bridge._restore_dataset()

            catalog = bridge.get_dataset_catalog()
            self.assertTrue(catalog["success"])
            self.assertEqual(len(catalog["datasets"]), 1)
            self.assertEqual(catalog["datasets"][0]["filename"], "Dataset_Prueba_01.json")
            self.assertEqual(catalog["datasets"][0]["dataset_id"], "test-dataset-uuid-1234")
            self.assertEqual(catalog["active_dataset"]["name"], "Dataset_Prueba_01")

            selected = bridge.select_dataset("Dataset_Prueba_01.json")
            self.assertTrue(selected["success"])
            self.assertEqual(selected["active_dataset"]["dataset_id"], "test-dataset-uuid-1234")

    def test_reject_invalid_manifest(self):
        from bridge.api_bridge import ApiBridge
        with tempfile.TemporaryDirectory() as tmp_dir:
            dataset_dir = Path(tmp_dir) / "Dataset"
            dataset_dir.mkdir(parents=True, exist_ok=True)
            bad_file = dataset_dir / "corrupt.json"
            bad_file.write_text(json.dumps({"schema": "unknown"}), encoding="utf-8")

            bridge = ApiBridge()
            bridge._dataset_dir = str(dataset_dir)
            res = bridge.select_dataset("corrupt.json")
            self.assertFalse(res["success"])
            self.assertIn("no contiene un manifiesto", res["error"])


if __name__ == "__main__":
    unittest.main()


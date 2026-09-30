"""Tests for durable window metadata storage."""
import json
import os
import tempfile
import unittest

from core.windowing import persistence


class WindowPersistenceTests(unittest.TestCase):
    def test_round_trip_and_schema(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "windows.json")
            records = [{"window_id": "W-001", "start_us": 0}]
            persistence.save(path, records, 1)
            loaded, sequence = persistence.load(path)
            self.assertEqual(loaded, records)
            self.assertEqual(sequence, 1)
            with open(path, encoding="utf-8") as stream:
                self.assertEqual(json.load(stream)["schema"], persistence.SCHEMA)

    def test_missing_or_invalid_file_is_empty(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "missing.json")
            self.assertEqual(persistence.load(path), ([], 0))
            with open(path, "w", encoding="utf-8") as stream:
                stream.write("{}")
            self.assertEqual(persistence.load(path), ([], 0))


if __name__ == "__main__":
    unittest.main()

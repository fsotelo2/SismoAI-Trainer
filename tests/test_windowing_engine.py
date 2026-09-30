"""Unit tests for Phase 6 temporal geometry."""
import unittest

from core.windowing import (
    WindowSpec, WindowingError, generate_intervals, seconds_to_us,
    validate_interval, validate_sensors, build_window,
)
from core.windowing.models import ORIGIN_FIXED, ORIGIN_SLIDING, ORIGIN_MANUAL


class WindowingEngineTests(unittest.TestCase):
    def test_fixed_consecutive_and_partial_discard(self):
        spec = WindowSpec(5_000_000, mode=ORIGIN_FIXED)
        self.assertEqual(generate_intervals(0, 12_000_000, spec),
                         [(0, 5_000_000), (5_000_000, 10_000_000)])

    def test_sliding_overlap(self):
        spec = WindowSpec(5_000_000, 2_500_000, ORIGIN_SLIDING)
        self.assertEqual(generate_intervals(0, 10_000_000, spec),
                         [(0, 5_000_000), (2_500_000, 7_500_000),
                          (5_000_000, 10_000_000)])

    def test_rejects_invalid_step(self):
        with self.assertRaises(WindowingError):
            WindowSpec(5_000_000, 6_000_000, ORIGIN_SLIDING).validate()

    def test_manual_interval_bounds(self):
        validate_interval(72_000_000, 77_000_000, (0, 180_000_000))
        with self.assertRaises(WindowingError):
            validate_interval(77_000_000, 72_000_000, (0, 180_000_000))
        with self.assertRaises(WindowingError):
            validate_interval(-1, 1, (0, 180_000_000))

    def test_sensor_validation(self):
        self.assertEqual(validate_sensors(["geo", "mpu"], ["GEO", "MPU"]),
                         ("GEO", "MPU"))
        with self.assertRaises(WindowingError):
            validate_sensors(["MPU"], ["GEO"])

    def test_common_record_shape_manual(self):
        window = build_window("W-001", "DAT_000001.BIN", "E-01",
                              ORIGIN_MANUAL, 1_000_000, 2_000_000,
                              ["GEO"], {"source": "manual"}, {"GEO": 88})
        payload = window.to_dict()
        self.assertEqual(payload["origin_mode"], "manual")
        self.assertEqual(payload["duration_ms"], 1000.0)
        self.assertEqual(payload["samples"]["GEO"], 88)

    def test_structural_quality_blocks_missing_sensor_samples(self):
        from core.windowing import evaluate_structure
        result = evaluate_structure(0, 1_000_000, (0, 2_000_000),
                                    ["GEO", "MPU"], {"GEO": 100, "MPU": 0})
        self.assertEqual(result.status, "blocked")

    def test_structural_quality_accepts_valid_interval(self):
        from core.windowing import evaluate_structure
        result = evaluate_structure(0, 1_000_000, (0, 2_000_000),
                                    ["GEO"], {"GEO": 100})
        self.assertEqual(result.status, "accepted")
        self.assertEqual(result.findings, ())

    def test_seconds_round_trip(self):
        self.assertEqual(seconds_to_us(1.234567), 1_234_567)

    def test_fixed_mode_requires_step_equal_duration(self):
        with self.assertRaises(WindowingError):
            WindowSpec(5_000_000, 2_000_000, ORIGIN_FIXED).validate()

    def test_zero_length_source_is_rejected(self):
        with self.assertRaises(WindowingError):
            generate_intervals(1_000_000, 1_000_000,
                               WindowSpec(500_000, mode=ORIGIN_FIXED))

    def test_non_finite_seconds_are_rejected(self):
        for value in (float("nan"), float("inf"), float("-inf")):
            with self.assertRaises(WindowingError):
                seconds_to_us(value)


if __name__ == "__main__":
    unittest.main()

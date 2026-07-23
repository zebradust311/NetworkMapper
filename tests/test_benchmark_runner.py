import json
import tempfile
import unittest
from pathlib import Path

from networkmapper.core.models import DeviceType
from networkmapper.developer.benchmark_runner import BenchmarkRunner


class BenchmarkRunnerTest(unittest.TestCase):
    def setUp(self):
        self.runner = BenchmarkRunner()

    def _write_json(self, path: Path, payload: dict) -> None:
        with path.open("w", encoding="utf-8") as file_handle:
            json.dump(payload, file_handle, indent=2)

    def test_dataset_loading_populates_device_fields(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            inventory_path = temp_path / "inventory.json"
            self._write_json(
                inventory_path,
                {
                    "devices": [
                        {
                            "ip_address": "192.168.50.10",
                            "hostname": "host-01",
                            "vendor": "Cisco",
                            "open_ports": [22, 161],
                            "detected_services": ["ssh", "snmp"],
                        }
                    ]
                },
            )

            devices = self.runner.load_inventory(inventory_path)

            self.assertEqual(len(devices), 1)
            self.assertEqual(devices[0].ip_address, "192.168.50.10")
            self.assertEqual(devices[0].hostname, "host-01")
            self.assertEqual(devices[0].vendor, "Cisco")
            self.assertEqual(devices[0].open_ports, [22, 161])
            self.assertEqual(devices[0].detected_services, ["ssh", "snmp"])
            self.assertEqual(devices[0].device_type, DeviceType.UNKNOWN)

    def test_accuracy_calculation_for_perfect_match_dataset(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            inventory_path = temp_path / "inventory.json"
            expected_path = temp_path / "expected_results.json"

            self._write_json(
                inventory_path,
                {
                    "devices": [
                        {
                            "ip_address": "192.168.60.10",
                            "hostname": "DC-01",
                            "vendor": "Cisco",
                        },
                        {
                            "ip_address": "192.168.60.20",
                            "hostname": "host-01",
                            "vendor": "Unknown",
                        },
                    ]
                },
            )

            self._write_json(
                expected_path,
                {
                    "expected_results": [
                        {"ip_address": "192.168.60.10", "device_type": "SERVER"},
                        {"ip_address": "192.168.60.20", "device_type": "UNKNOWN"},
                    ]
                },
            )

            report = self.runner.run_benchmark(inventory_path, expected_path)

            self.assertEqual(report.total_devices, 2)
            self.assertEqual(report.correct_classifications, 2)
            self.assertEqual(report.incorrect_classifications, 0)
            self.assertEqual(report.accuracy_percentage, 100.0)
            self.assertEqual(report.mismatches, ())

    def test_expected_vs_actual_comparison_captures_mismatches(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            inventory_path = temp_path / "inventory.json"
            expected_path = temp_path / "expected_results.json"

            self._write_json(
                inventory_path,
                {
                    "devices": [
                        {
                            "ip_address": "192.168.70.10",
                            "hostname": "switch-01",
                            "vendor": "Cisco",
                        },
                        {
                            "ip_address": "192.168.70.20",
                            "hostname": "unknown-01",
                            "vendor": "Unknown",
                        },
                    ]
                },
            )

            self._write_json(
                expected_path,
                {
                    "expected_results": [
                        {"ip_address": "192.168.70.10", "device_type": "SWITCH"},
                        {"ip_address": "192.168.70.20", "device_type": "FIREWALL"},
                    ]
                },
            )

            report = self.runner.run_benchmark(inventory_path, expected_path)

            self.assertEqual(report.total_devices, 2)
            self.assertEqual(report.correct_classifications, 1)
            self.assertEqual(report.incorrect_classifications, 1)
            self.assertEqual(report.accuracy_percentage, 50.0)
            self.assertEqual(len(report.mismatches), 1)
            self.assertEqual(report.mismatches[0].ip_address, "192.168.70.20")
            self.assertEqual(report.mismatches[0].expected_device_type, "FIREWALL")
            self.assertEqual(report.mismatches[0].predicted_device_type, "UNKNOWN")

    def test_mismatch_reporting_marks_missing_expected_results(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            inventory_path = temp_path / "inventory.json"
            expected_path = temp_path / "expected_results.json"

            self._write_json(
                inventory_path,
                {
                    "devices": [
                        {
                            "ip_address": "192.168.80.10",
                            "hostname": "host-01",
                            "vendor": "Unknown",
                        }
                    ]
                },
            )

            self._write_json(expected_path, {"expected_results": []})

            report = self.runner.run_benchmark(inventory_path, expected_path)

            self.assertEqual(report.total_devices, 1)
            self.assertEqual(report.correct_classifications, 0)
            self.assertEqual(report.incorrect_classifications, 1)
            self.assertEqual(len(report.mismatches), 1)
            self.assertEqual(report.mismatches[0].expected_device_type, "MISSING")
            self.assertEqual(report.mismatches[0].predicted_device_type, "UNKNOWN")


if __name__ == "__main__":
    unittest.main()
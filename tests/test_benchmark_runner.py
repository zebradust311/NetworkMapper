import json
import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from networkmapper.core.models import DeviceType
from networkmapper.developer.benchmark_runner import (
    BenchmarkRunner,
    parse_cli_args,
    main,
)


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
            self.assertEqual(report.dataset_name, "benchmark")
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
            self.assertEqual(report.mismatches[0].hostname, "unknown-01")
            self.assertEqual(report.mismatches[0].expected_device_type, "FIREWALL")
            self.assertEqual(report.mismatches[0].actual_device_type, "UNKNOWN")

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
            self.assertEqual(report.mismatches[0].hostname, "host-01")
            self.assertEqual(report.mismatches[0].expected_device_type, "MISSING")
            self.assertEqual(report.mismatches[0].actual_device_type, "UNKNOWN")

    def test_cli_argument_parsing(self):
        args = parse_cli_args(
            [
                "benchmarks/small_office",
                "--json",
                "--markdown",
                "--output",
                "custom-output",
                "--console",
            ]
        )

        self.assertEqual(args.benchmark_directory, "benchmarks/small_office")
        self.assertTrue(args.write_json)
        self.assertTrue(args.write_markdown)
        self.assertTrue(args.console)
        self.assertEqual(args.output, "custom-output")

    def test_cli_console_output_by_default(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            benchmark_dir = Path(temp_dir) / "dataset_console"
            benchmark_dir.mkdir(parents=True, exist_ok=True)

            self._write_json(
                benchmark_dir / "inventory.json",
                {
                    "devices": [
                        {
                            "ip_address": "10.10.0.10",
                            "hostname": "host-01",
                            "vendor": "Unknown",
                        }
                    ]
                },
            )
            self._write_json(
                benchmark_dir / "expected_results.json",
                {
                    "expected_results": [
                        {"ip_address": "10.10.0.10", "device_type": "UNKNOWN"}
                    ]
                },
            )

            stdout_capture = io.StringIO()
            stderr_capture = io.StringIO()
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                exit_code = main([str(benchmark_dir)])

            self.assertEqual(exit_code, 0)
            self.assertEqual(stderr_capture.getvalue(), "")

            console_output = stdout_capture.getvalue()
            self.assertIn("Dataset: dataset_console", console_output)
            self.assertIn("Total devices: 1", console_output)
            self.assertIn("Correct classifications: 1", console_output)
            self.assertIn("Incorrect classifications: 0", console_output)
            self.assertIn("Accuracy: 100.00%", console_output)
            self.assertIn("Mismatch list:", console_output)

    def test_cli_json_report_generation(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            benchmark_dir = temp_path / "dataset_json"
            output_dir = temp_path / "reports"
            benchmark_dir.mkdir(parents=True, exist_ok=True)

            self._write_json(
                benchmark_dir / "inventory.json",
                {
                    "devices": [
                        {
                            "ip_address": "10.20.0.10",
                            "hostname": "host-a",
                            "vendor": "Unknown",
                        }
                    ]
                },
            )
            self._write_json(
                benchmark_dir / "expected_results.json",
                {
                    "expected_results": [
                        {"ip_address": "10.20.0.10", "device_type": "SERVER"}
                    ]
                },
            )

            stdout_capture = io.StringIO()
            with redirect_stdout(stdout_capture):
                exit_code = main(
                    [str(benchmark_dir), "--json", "--output", str(output_dir)]
                )

            self.assertEqual(exit_code, 0)
            json_report_path = output_dir / "dataset_json.json"
            self.assertTrue(json_report_path.exists())

            with json_report_path.open("r", encoding="utf-8") as file_handle:
                report_payload = json.load(file_handle)

            self.assertEqual(report_payload["dataset_name"], "dataset_json")
            self.assertEqual(report_payload["total_devices"], 1)
            self.assertEqual(report_payload["correct_classifications"], 0)
            self.assertEqual(report_payload["incorrect_classifications"], 1)
            self.assertEqual(report_payload["accuracy_percentage"], 0.0)
            self.assertEqual(len(report_payload["mismatches"]), 1)
            self.assertEqual(report_payload["mismatches"][0]["ip_address"], "10.20.0.10")
            self.assertEqual(report_payload["mismatches"][0]["hostname"], "host-a")
            self.assertEqual(
                report_payload["mismatches"][0]["expected_device_type"], "SERVER"
            )
            self.assertEqual(
                report_payload["mismatches"][0]["actual_device_type"], "UNKNOWN"
            )
            self.assertIn("JSON report:", stdout_capture.getvalue())

    def test_cli_markdown_report_generation(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            benchmark_dir = temp_path / "dataset_markdown"
            output_dir = temp_path / "reports"
            benchmark_dir.mkdir(parents=True, exist_ok=True)

            self._write_json(
                benchmark_dir / "inventory.json",
                {
                    "devices": [
                        {
                            "ip_address": "10.30.0.10",
                            "hostname": "host-b",
                            "vendor": "Unknown",
                        }
                    ]
                },
            )
            self._write_json(
                benchmark_dir / "expected_results.json",
                {
                    "expected_results": [
                        {"ip_address": "10.30.0.10", "device_type": "SERVER"}
                    ]
                },
            )

            stdout_capture = io.StringIO()
            with redirect_stdout(stdout_capture):
                exit_code = main(
                    [str(benchmark_dir), "--markdown", "--output", str(output_dir)]
                )

            self.assertEqual(exit_code, 0)
            markdown_report_path = output_dir / "dataset_markdown.md"
            self.assertTrue(markdown_report_path.exists())

            markdown_content = markdown_report_path.read_text(encoding="utf-8")
            self.assertIn("# Benchmark Report: dataset_markdown", markdown_content)
            self.assertIn("- Total devices: 1", markdown_content)
            self.assertIn("- Correct classifications: 0", markdown_content)
            self.assertIn("- Incorrect classifications: 1", markdown_content)
            self.assertIn("- Accuracy: 0.00%", markdown_content)
            self.assertIn("| IP address | Hostname | Expected DeviceType | Actual DeviceType |", markdown_content)
            self.assertIn("| 10.30.0.10 | host-b | SERVER | UNKNOWN |", markdown_content)
            self.assertIn("Markdown report:", stdout_capture.getvalue())

    def test_invalid_dataset_path_returns_error(self):
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()
        with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
            exit_code = main(["benchmarks/does-not-exist"])

        self.assertEqual(exit_code, 1)
        self.assertEqual(stdout_capture.getvalue(), "")
        self.assertIn("Error: benchmark directory not found:", stderr_capture.getvalue())

    def test_output_directory_is_created_for_report_generation(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            benchmark_dir = temp_path / "dataset_output_dir"
            output_dir = temp_path / "nested" / "reports" / "benchmarks"
            benchmark_dir.mkdir(parents=True, exist_ok=True)

            self._write_json(
                benchmark_dir / "inventory.json",
                {
                    "devices": [
                        {
                            "ip_address": "10.40.0.10",
                            "hostname": "host-c",
                            "vendor": "Unknown",
                        }
                    ]
                },
            )
            self._write_json(
                benchmark_dir / "expected_results.json",
                {
                    "expected_results": [
                        {"ip_address": "10.40.0.10", "device_type": "UNKNOWN"}
                    ]
                },
            )

            self.assertFalse(output_dir.exists())
            exit_code = main([str(benchmark_dir), "--json", "--output", str(output_dir)])

            self.assertEqual(exit_code, 0)
            self.assertTrue(output_dir.exists())
            self.assertTrue((output_dir / "dataset_output_dir.json").exists())


if __name__ == "__main__":
    unittest.main()
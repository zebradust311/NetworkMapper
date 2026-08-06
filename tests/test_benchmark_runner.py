import json
import io
import re
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from networkmapper.core.models import DeviceType, ServiceEvidence
from networkmapper.developer.benchmark_runner import (
    BenchmarkMismatch,
    BenchmarkReport,
    BenchmarkRunner,
    parse_cli_args,
    main,
    render_console_report,
    write_json_report,
    write_markdown_report,
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
                            "mac_address": "AA:BB:CC:DD:EE:FF",
                            "vendor": "Cisco",
                            "services": [
                                {"port": 22, "protocol": "tcp", "service": "ssh"},
                                {"port": 161, "protocol": "udp", "service": "snmp"},
                            ],
                        }
                    ]
                },
            )

            devices = self.runner.load_inventory(inventory_path)

            self.assertEqual(len(devices), 1)
            self.assertEqual(devices[0].ip_address, "192.168.50.10")
            self.assertEqual(devices[0].hostname, "host-01")
            self.assertEqual(devices[0].mac_address, "AA:BB:CC:DD:EE:FF")
            self.assertEqual(devices[0].vendor, "Cisco")
            self.assertEqual(
                devices[0].services,
                [
                    ServiceEvidence(port=22, protocol="tcp", service="ssh"),
                    ServiceEvidence(port=161, protocol="udp", service="snmp"),
                ],
            )
            self.assertEqual(devices[0].device_type, DeviceType.UNKNOWN)

    def test_dataset_loading_populates_http_title_and_tls_fields(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            inventory_path = temp_path / "inventory.json"
            self._write_json(
                inventory_path,
                {
                    "devices": [
                        {
                            "ip_address": "192.168.50.20",
                            "hostname": "fw-01",
                            "vendor": "Unknown",
                            "services": [
                                {
                                    "port": 443,
                                    "protocol": "tcp",
                                    "service": "https",
                                    "http_title": "SonicWALL - Network Security Appliance",
                                    "tls_subject": "commonName=SonicWALL",
                                    "tls_issuer": "commonName=SonicWALL",
                                },
                            ],
                        }
                    ]
                },
            )

            devices = self.runner.load_inventory(inventory_path)

            self.assertEqual(
                devices[0].services,
                [
                    ServiceEvidence(
                        port=443,
                        protocol="tcp",
                        service="https",
                        http_title="SonicWALL - Network Security Appliance",
                        tls_subject="commonName=SonicWALL",
                        tls_issuer="commonName=SonicWALL",
                    ),
                ],
            )

    def test_dataset_loading_populates_http_auth_realm_field(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            inventory_path = temp_path / "inventory.json"
            self._write_json(
                inventory_path,
                {
                    "devices": [
                        {
                            "ip_address": "192.168.50.21",
                            "hostname": "printer-01",
                            "vendor": "Unknown",
                            "services": [
                                {
                                    "port": 80,
                                    "protocol": "tcp",
                                    "service": "http",
                                    "http_auth_realm": "HP LaserJet 4250",
                                },
                            ],
                        }
                    ]
                },
            )

            devices = self.runner.load_inventory(inventory_path)

            self.assertEqual(
                devices[0].services,
                [
                    ServiceEvidence(
                        port=80,
                        protocol="tcp",
                        service="http",
                        http_auth_realm="HP LaserJet 4250",
                    ),
                ],
            )

    def test_dataset_loading_populates_smb_identity_fields(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            inventory_path = temp_path / "inventory.json"
            self._write_json(
                inventory_path,
                {
                    "devices": [
                        {
                            "ip_address": "192.168.50.22",
                            "hostname": "dc-01",
                            "vendor": "Unknown",
                            "operating_system": "Windows Server 2019 Standard 17763",
                            "computer_name": "DC01",
                            "domain": "corp.local",
                            "smb_signing": "disabled (dangerous, but default)",
                        }
                    ]
                },
            )

            devices = self.runner.load_inventory(inventory_path)

            self.assertEqual(
                devices[0].operating_system, "Windows Server 2019 Standard 17763"
            )
            self.assertEqual(devices[0].computer_name, "DC01")
            self.assertEqual(devices[0].domain, "corp.local")
            self.assertEqual(devices[0].smb_signing, "disabled (dangerous, but default)")

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
            self.assertEqual(report.device_type_summary["SERVER"]["total"], 1)
            self.assertEqual(report.device_type_summary["SERVER"]["correct"], 1)
            self.assertEqual(report.device_type_summary["SERVER"]["incorrect"], 0)
            self.assertEqual(report.device_type_summary["SERVER"]["accuracy"], 100.0)
            self.assertEqual(report.device_type_summary["UNKNOWN"]["total"], 1)
            self.assertEqual(report.device_type_summary["UNKNOWN"]["correct"], 1)
            self.assertEqual(report.device_type_summary["UNKNOWN"]["incorrect"], 0)
            self.assertEqual(report.device_type_summary["UNKNOWN"]["accuracy"], 100.0)
            self.assertEqual(report.misclassification_summary, {})
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
            self.assertEqual(report.device_type_summary["SWITCH"]["accuracy"], 100.0)
            self.assertEqual(report.device_type_summary["FIREWALL"]["accuracy"], 0.0)
            self.assertEqual(report.misclassification_summary, {"FIREWALL": {"UNKNOWN": 1}})
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
            self.assertEqual(report.device_type_summary, {})
            self.assertEqual(report.misclassification_summary, {"MISSING": {"UNKNOWN": 1}})
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
            self.assertRegex(
                console_output,
                r"Generated at: \d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z",
            )
            self.assertIn("Total devices: 1", console_output)
            self.assertIn("Correct classifications: 1", console_output)
            self.assertIn("Incorrect classifications: 0", console_output)
            self.assertIn("Accuracy: 100.00%", console_output)
            self.assertIn("Device Type Summary", console_output)
            self.assertIn("UNKNOWN       100.0%", console_output)
            self.assertIn("Misclassification Summary", console_output)
            self.assertIn("- None", console_output)
            self.assertIn("Confusion Matrix", console_output)
            self.assertIn("Expected \\ Actual", console_output)
            self.assertIn("UNKNOWN", console_output)
            self.assertIn("Mismatch summary:", console_output)
            self.assertIn("Total mismatches: 0", console_output)
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
            self.assertRegex(
                report_payload["generated_at"],
                r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z",
            )
            self.assertEqual(report_payload["total_devices"], 1)
            self.assertEqual(report_payload["correct_classifications"], 0)
            self.assertEqual(report_payload["incorrect_classifications"], 1)
            self.assertEqual(report_payload["accuracy_percentage"], 0.0)
            self.assertEqual(report_payload["device_type_summary"]["SERVER"]["total"], 1)
            self.assertEqual(report_payload["device_type_summary"]["SERVER"]["correct"], 0)
            self.assertEqual(report_payload["device_type_summary"]["SERVER"]["incorrect"], 1)
            self.assertEqual(report_payload["device_type_summary"]["SERVER"]["accuracy"], 0.0)
            self.assertEqual(
                report_payload["confusion_matrix"],
                {"SERVER": {"SERVER": 0, "UNKNOWN": 1}},
            )
            self.assertEqual(report_payload["misclassification_summary"], {"SERVER": {"UNKNOWN": 1}})
            self.assertEqual(report_payload["mismatch_summary"]["total_mismatches"], 1)
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
            self.assertRegex(
                markdown_content,
                r"Generated at: \d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z",
            )
            self.assertIn("- Total devices: 1", markdown_content)
            self.assertIn("- Correct classifications: 0", markdown_content)
            self.assertIn("- Incorrect classifications: 1", markdown_content)
            self.assertIn("- Accuracy: 0.00%", markdown_content)
            self.assertIn("## Device Type Summary", markdown_content)
            self.assertIn("| Device Type | Total | Correct | Incorrect | Accuracy |", markdown_content)
            self.assertIn("| SERVER | 1 | 0 | 1 | 0.0% |", markdown_content)
            self.assertIn("## Misclassification Summary", markdown_content)
            self.assertIn("| Expected | Actual | Count |", markdown_content)
            self.assertIn("| SERVER | UNKNOWN | 1 |", markdown_content)
            self.assertIn("## Confusion Matrix", markdown_content)
            self.assertIn("| Expected \\ Actual | SERVER | UNKNOWN |", markdown_content)
            self.assertIn("| SERVER | 0 | 1 |", markdown_content)
            self.assertIn("## Mismatch summary", markdown_content)
            self.assertIn("- Total mismatches: 1", markdown_content)
            self.assertIn("| IP address | Hostname | Expected DeviceType | Actual DeviceType |", markdown_content)
            self.assertIn("| 10.30.0.10 | host-b | SERVER | UNKNOWN |", markdown_content)
            self.assertIn("Markdown report:", stdout_capture.getvalue())

    def test_markdown_report_generation_with_empty_mismatch_list(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "markdown_reports"
            report = BenchmarkReport(
                dataset_name="empty_mismatch_dataset",
                total_devices=2,
                correct_classifications=2,
                incorrect_classifications=0,
                accuracy_percentage=100.0,
                device_type_summary={"SERVER": {"total": 2, "correct": 2, "incorrect": 0, "accuracy": 100.0}},
                confusion_matrix={"SERVER": {"SERVER": 2}},
                misclassification_summary={},
                mismatches=(),
            )

            report_path = write_markdown_report(
                report=report,
                output_directory=output_dir,
                generated_at="2026-07-24T10:00:00Z",
            )

            markdown_content = report_path.read_text(encoding="utf-8")
            self.assertIn("# Benchmark Report: empty_mismatch_dataset", markdown_content)
            self.assertIn("Generated at: 2026-07-24T10:00:00Z", markdown_content)
            self.assertIn("## Device Type Summary", markdown_content)
            self.assertIn("| SERVER | 2 | 2 | 0 | 100.0% |", markdown_content)
            self.assertIn("## Misclassification Summary", markdown_content)
            self.assertIn("No misclassifications.", markdown_content)
            self.assertIn("## Confusion Matrix", markdown_content)
            self.assertIn("| Expected \\ Actual | SERVER |", markdown_content)
            self.assertIn("| SERVER | 2 |", markdown_content)
            self.assertIn("## Mismatch summary", markdown_content)
            self.assertIn("- Total mismatches: 0", markdown_content)
            self.assertIn("| None | N/A | N/A | N/A |", markdown_content)

    def test_json_report_generation_with_multiple_mismatches(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "json_reports"
            report = BenchmarkReport(
                dataset_name="multiple_mismatch_dataset",
                total_devices=3,
                correct_classifications=1,
                incorrect_classifications=2,
                accuracy_percentage=33.3333333333,
                device_type_summary={
                    "SERVER": {"total": 1, "correct": 0, "incorrect": 1, "accuracy": 0.0},
                    "SWITCH": {"total": 2, "correct": 1, "incorrect": 1, "accuracy": 50.0},
                },
                confusion_matrix={
                    "SERVER": {"SERVER": 0, "SWITCH": 0, "UNKNOWN": 1},
                    "SWITCH": {"SERVER": 0, "SWITCH": 1, "UNKNOWN": 1},
                },
                misclassification_summary={
                    "SERVER": {"UNKNOWN": 1},
                    "SWITCH": {"UNKNOWN": 1},
                },
                mismatches=(
                    BenchmarkMismatch(
                        ip_address="192.168.1.10",
                        hostname="host-10",
                        expected_device_type="SERVER",
                        actual_device_type="UNKNOWN",
                    ),
                    BenchmarkMismatch(
                        ip_address="192.168.1.11",
                        hostname=None,
                        expected_device_type="SWITCH",
                        actual_device_type="UNKNOWN",
                    ),
                ),
            )

            report_path = write_json_report(
                report=report,
                output_directory=output_dir,
                generated_at="2026-07-24T11:00:00Z",
            )

            with report_path.open("r", encoding="utf-8") as file_handle:
                report_payload = json.load(file_handle)

            self.assertEqual(report_payload["dataset_name"], "multiple_mismatch_dataset")
            self.assertEqual(report_payload["generated_at"], "2026-07-24T11:00:00Z")
            self.assertEqual(report_payload["device_type_summary"]["SERVER"]["accuracy"], 0.0)
            self.assertEqual(report_payload["device_type_summary"]["SWITCH"]["accuracy"], 50.0)
            self.assertEqual(
                report_payload["confusion_matrix"],
                {
                    "SERVER": {"SERVER": 0, "SWITCH": 0, "UNKNOWN": 1},
                    "SWITCH": {"SERVER": 0, "SWITCH": 1, "UNKNOWN": 1},
                },
            )
            self.assertEqual(report_payload["misclassification_summary"]["SERVER"]["UNKNOWN"], 1)
            self.assertEqual(report_payload["misclassification_summary"]["SWITCH"]["UNKNOWN"], 1)
            self.assertEqual(report_payload["mismatch_summary"]["total_mismatches"], 2)
            self.assertEqual(len(report_payload["mismatches"]), 2)
            self.assertEqual(report_payload["mismatches"][0]["ip_address"], "192.168.1.10")
            self.assertEqual(report_payload["mismatches"][0]["hostname"], "host-10")
            self.assertEqual(report_payload["mismatches"][0]["expected_device_type"], "SERVER")
            self.assertEqual(report_payload["mismatches"][0]["actual_device_type"], "UNKNOWN")
            self.assertEqual(report_payload["mismatches"][1]["ip_address"], "192.168.1.11")
            self.assertIsNone(report_payload["mismatches"][1]["hostname"])
            self.assertEqual(report_payload["mismatches"][1]["expected_device_type"], "SWITCH")
            self.assertEqual(report_payload["mismatches"][1]["actual_device_type"], "UNKNOWN")

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

    def test_device_type_summary_single_device_type(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            inventory_path = temp_path / "inventory.json"
            expected_path = temp_path / "expected_results.json"

            self._write_json(
                inventory_path,
                {
                    "devices": [
                        {"ip_address": "10.1.0.1", "hostname": "host-1", "vendor": "Unknown"},
                        {"ip_address": "10.1.0.2", "hostname": "host-2", "vendor": "Unknown"},
                    ]
                },
            )
            self._write_json(
                expected_path,
                {
                    "expected_results": [
                        {"ip_address": "10.1.0.1", "device_type": "UNKNOWN"},
                        {"ip_address": "10.1.0.2", "device_type": "UNKNOWN"},
                    ]
                },
            )

            report = self.runner.run_benchmark(inventory_path, expected_path)

            self.assertEqual(report.device_type_summary, {
                "UNKNOWN": {"total": 2, "correct": 2, "incorrect": 0, "accuracy": 100.0}
            })
            self.assertEqual(report.confusion_matrix, {"UNKNOWN": {"UNKNOWN": 2}})
            self.assertEqual(report.misclassification_summary, {})

    def test_device_type_summary_multiple_device_types(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            inventory_path = temp_path / "inventory.json"
            expected_path = temp_path / "expected_results.json"

            self._write_json(
                inventory_path,
                {
                    "devices": [
                        {"ip_address": "10.2.0.10", "hostname": "dc-01", "vendor": "Cisco"},
                        {"ip_address": "10.2.0.20", "hostname": "switch-01", "vendor": "Cisco"},
                        {"ip_address": "10.2.0.30", "hostname": "voice-01", "vendor": "Unknown"},
                    ]
                },
            )
            self._write_json(
                expected_path,
                {
                    "expected_results": [
                        {"ip_address": "10.2.0.10", "device_type": "SERVER"},
                        {"ip_address": "10.2.0.20", "device_type": "SWITCH"},
                        {"ip_address": "10.2.0.30", "device_type": "PHONE"},
                    ]
                },
            )

            report = self.runner.run_benchmark(inventory_path, expected_path)

            self.assertEqual(report.device_type_summary["SERVER"]["total"], 1)
            self.assertEqual(report.device_type_summary["SWITCH"]["total"], 1)
            self.assertEqual(report.device_type_summary["PHONE"]["total"], 1)
            self.assertEqual(
                report.confusion_matrix,
                {
                    "PHONE": {"PHONE": 0, "SERVER": 0, "SWITCH": 0, "UNKNOWN": 1},
                    "SERVER": {"PHONE": 0, "SERVER": 1, "SWITCH": 0, "UNKNOWN": 0},
                    "SWITCH": {"PHONE": 0, "SERVER": 0, "SWITCH": 1, "UNKNOWN": 0},
                },
            )

    def test_device_type_summary_empty_benchmark(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            inventory_path = temp_path / "inventory.json"
            expected_path = temp_path / "expected_results.json"

            self._write_json(inventory_path, {"devices": []})
            self._write_json(expected_path, {"expected_results": []})

            report = self.runner.run_benchmark(inventory_path, expected_path)

            self.assertEqual(report.total_devices, 0)
            self.assertEqual(report.accuracy_percentage, 0.0)
            self.assertEqual(report.device_type_summary, {})
            self.assertEqual(report.confusion_matrix, {})

    def test_device_type_summary_perfect_accuracy(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            inventory_path = temp_path / "inventory.json"
            expected_path = temp_path / "expected_results.json"

            self._write_json(
                inventory_path,
                {
                    "devices": [
                        {"ip_address": "10.3.0.10", "hostname": "dc-01", "vendor": "Cisco"},
                        {"ip_address": "10.3.0.20", "hostname": "host-01", "vendor": "Unknown"},
                    ]
                },
            )
            self._write_json(
                expected_path,
                {
                    "expected_results": [
                        {"ip_address": "10.3.0.10", "device_type": "SERVER"},
                        {"ip_address": "10.3.0.20", "device_type": "UNKNOWN"},
                    ]
                },
            )

            report = self.runner.run_benchmark(inventory_path, expected_path)

            self.assertEqual(report.device_type_summary["SERVER"]["accuracy"], 100.0)
            self.assertEqual(report.device_type_summary["UNKNOWN"]["accuracy"], 100.0)
            self.assertEqual(
                report.confusion_matrix,
                {
                    "SERVER": {"SERVER": 1, "UNKNOWN": 0},
                    "UNKNOWN": {"SERVER": 0, "UNKNOWN": 1},
                },
            )

    def test_device_type_summary_mixed_accuracy(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            inventory_path = temp_path / "inventory.json"
            expected_path = temp_path / "expected_results.json"

            self._write_json(
                inventory_path,
                {
                    "devices": [
                        {"ip_address": "10.4.0.10", "hostname": "switch-01", "vendor": "Cisco"},
                        {"ip_address": "10.4.0.20", "hostname": "switch-02", "vendor": "Unknown"},
                        {"ip_address": "10.4.0.30", "hostname": "voice-01", "vendor": "Unknown"},
                    ]
                },
            )
            self._write_json(
                expected_path,
                {
                    "expected_results": [
                        {"ip_address": "10.4.0.10", "device_type": "SWITCH"},
                        {"ip_address": "10.4.0.20", "device_type": "SWITCH"},
                        {"ip_address": "10.4.0.30", "device_type": "PHONE"},
                    ]
                },
            )

            report = self.runner.run_benchmark(inventory_path, expected_path)

            self.assertEqual(report.device_type_summary["SWITCH"]["total"], 2)
            self.assertEqual(report.device_type_summary["SWITCH"]["correct"], 1)
            self.assertEqual(report.device_type_summary["SWITCH"]["incorrect"], 1)
            self.assertEqual(report.device_type_summary["SWITCH"]["accuracy"], 50.0)
            self.assertEqual(report.device_type_summary["PHONE"]["accuracy"], 0.0)
            self.assertEqual(
                report.confusion_matrix,
                {
                    "PHONE": {"PHONE": 0, "SWITCH": 0, "UNKNOWN": 1},
                    "SWITCH": {"PHONE": 0, "SWITCH": 1, "UNKNOWN": 1},
                },
            )
            self.assertEqual(
                report.misclassification_summary,
                {
                    "PHONE": {"UNKNOWN": 1},
                    "SWITCH": {"UNKNOWN": 1},
                },
            )

    def test_misclassification_summary_no_mismatches(self):
        report = BenchmarkReport(
            dataset_name="no_mismatch",
            total_devices=1,
            correct_classifications=1,
            incorrect_classifications=0,
            accuracy_percentage=100.0,
            device_type_summary={"UNKNOWN": {"total": 1, "correct": 1, "incorrect": 0, "accuracy": 100.0}},
            confusion_matrix={"UNKNOWN": {"UNKNOWN": 1}},
            misclassification_summary={},
            mismatches=(),
        )

        markdown = write_markdown_report(
            report=report,
            output_directory=Path(tempfile.gettempdir()) / "nm_acc004",
            generated_at="2026-07-24T12:00:00Z",
        ).read_text(encoding="utf-8")
        self.assertIn("No misclassifications.", markdown)

    def test_misclassification_summary_one_mismatch(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            inventory_path = temp_path / "inventory.json"
            expected_path = temp_path / "expected_results.json"

            self._write_json(
                inventory_path,
                {"devices": [{"ip_address": "10.5.0.1", "hostname": "host-1", "vendor": "Unknown"}]},
            )
            self._write_json(
                expected_path,
                {"expected_results": [{"ip_address": "10.5.0.1", "device_type": "SERVER"}]},
            )

            report = self.runner.run_benchmark(inventory_path, expected_path)
            self.assertEqual(report.misclassification_summary, {"SERVER": {"UNKNOWN": 1}})

    def test_misclassification_summary_multiple_categories(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            inventory_path = temp_path / "inventory.json"
            expected_path = temp_path / "expected_results.json"

            self._write_json(
                inventory_path,
                {
                    "devices": [
                        {"ip_address": "10.6.0.1", "hostname": "host-1", "vendor": "Unknown"},
                        {"ip_address": "10.6.0.2", "hostname": "host-2", "vendor": "Unknown"},
                    ]
                },
            )
            self._write_json(
                expected_path,
                {
                    "expected_results": [
                        {"ip_address": "10.6.0.1", "device_type": "SERVER"},
                        {"ip_address": "10.6.0.2", "device_type": "PHONE"},
                    ]
                },
            )

            report = self.runner.run_benchmark(inventory_path, expected_path)
            self.assertEqual(
                report.misclassification_summary,
                {
                    "PHONE": {"UNKNOWN": 1},
                    "SERVER": {"UNKNOWN": 1},
                },
            )

    def test_misclassification_summary_repeated_aggregation(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            inventory_path = temp_path / "inventory.json"
            expected_path = temp_path / "expected_results.json"

            self._write_json(
                inventory_path,
                {
                    "devices": [
                        {"ip_address": "10.7.0.1", "hostname": "host-1", "vendor": "Unknown"},
                        {"ip_address": "10.7.0.2", "hostname": "host-2", "vendor": "Unknown"},
                    ]
                },
            )
            self._write_json(
                expected_path,
                {
                    "expected_results": [
                        {"ip_address": "10.7.0.1", "device_type": "PHONE"},
                        {"ip_address": "10.7.0.2", "device_type": "PHONE"},
                    ]
                },
            )

            report = self.runner.run_benchmark(inventory_path, expected_path)
            self.assertEqual(report.misclassification_summary, {"PHONE": {"UNKNOWN": 2}})

    def test_misclassification_summary_json_serialization(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            report = BenchmarkReport(
                dataset_name="json_misclass",
                total_devices=2,
                correct_classifications=0,
                incorrect_classifications=2,
                accuracy_percentage=0.0,
                device_type_summary={"PHONE": {"total": 2, "correct": 0, "incorrect": 2, "accuracy": 0.0}},
                confusion_matrix={"PHONE": {"PHONE": 0, "UNKNOWN": 2}},
                misclassification_summary={"PHONE": {"UNKNOWN": 2}},
                mismatches=(
                    BenchmarkMismatch("10.8.0.1", "host-a", "PHONE", "UNKNOWN"),
                    BenchmarkMismatch("10.8.0.2", "host-b", "PHONE", "UNKNOWN"),
                ),
            )
            report_path = write_json_report(report, output_dir, "2026-07-24T12:10:00Z")
            payload = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["confusion_matrix"], {"PHONE": {"PHONE": 0, "UNKNOWN": 2}})
            self.assertEqual(payload["misclassification_summary"], {"PHONE": {"UNKNOWN": 2}})

    def test_misclassification_summary_markdown_rendering(self):
        report = BenchmarkReport(
            dataset_name="md_misclass",
            total_devices=1,
            correct_classifications=0,
            incorrect_classifications=1,
            accuracy_percentage=0.0,
            device_type_summary={"SERVER": {"total": 1, "correct": 0, "incorrect": 1, "accuracy": 0.0}},
            confusion_matrix={"SERVER": {"SERVER": 0, "UNKNOWN": 1}},
            misclassification_summary={"SERVER": {"UNKNOWN": 1}},
            mismatches=(BenchmarkMismatch("10.9.0.1", None, "SERVER", "UNKNOWN"),),
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            path = write_markdown_report(report, output_dir, "2026-07-24T12:20:00Z")
            content = path.read_text(encoding="utf-8")
            self.assertIn("## Misclassification Summary", content)
            self.assertIn("| Expected | Actual | Count |", content)
            self.assertIn("| SERVER | UNKNOWN | 1 |", content)
            self.assertIn("## Confusion Matrix", content)
            self.assertIn("| Expected \\ Actual | SERVER | UNKNOWN |", content)
            self.assertIn("| SERVER | 0 | 1 |", content)

    def test_misclassification_summary_console_rendering(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            benchmark_dir = Path(temp_dir) / "dataset_console_misclass"
            benchmark_dir.mkdir(parents=True, exist_ok=True)

            self._write_json(
                benchmark_dir / "inventory.json",
                {
                    "devices": [
                        {"ip_address": "10.10.10.1", "hostname": "host-1", "vendor": "Unknown"},
                        {"ip_address": "10.10.10.2", "hostname": "host-2", "vendor": "Unknown"},
                    ]
                },
            )
            self._write_json(
                benchmark_dir / "expected_results.json",
                {
                    "expected_results": [
                        {"ip_address": "10.10.10.1", "device_type": "SERVER"},
                        {"ip_address": "10.10.10.2", "device_type": "PHONE"},
                    ]
                },
            )

            stdout_capture = io.StringIO()
            stderr_capture = io.StringIO()
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                exit_code = main([str(benchmark_dir), "--console"])

            self.assertEqual(exit_code, 0)
            self.assertEqual(stderr_capture.getvalue(), "")
            output = stdout_capture.getvalue()
            self.assertIn("Misclassification Summary", output)
            self.assertIn("PHONE -> UNKNOWN : 1", output)
            self.assertIn("SERVER -> UNKNOWN : 1", output)
            self.assertIn("Confusion Matrix", output)
            self.assertIn("Expected \\ Actual", output)
            self.assertIn("PHONE", output)
            self.assertIn("SERVER", output)
            self.assertIn("UNKNOWN", output)

    def test_confusion_matrix_json_serialization(self):
        report = BenchmarkReport(
            dataset_name="confusion_json",
            total_devices=2,
            correct_classifications=1,
            incorrect_classifications=1,
            accuracy_percentage=50.0,
            device_type_summary={
                "SERVER": {"total": 1, "correct": 0, "incorrect": 1, "accuracy": 0.0},
                "SWITCH": {"total": 1, "correct": 1, "incorrect": 0, "accuracy": 100.0},
            },
            confusion_matrix={
                "SERVER": {"SERVER": 0, "SWITCH": 0, "UNKNOWN": 1},
                "SWITCH": {"SERVER": 0, "SWITCH": 1, "UNKNOWN": 0},
            },
            misclassification_summary={"SERVER": {"UNKNOWN": 1}},
            mismatches=(BenchmarkMismatch("10.11.0.1", "host-1", "SERVER", "UNKNOWN"),),
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            report_path = write_json_report(report, output_dir, "2026-07-24T12:30:00Z")
            payload = json.loads(report_path.read_text(encoding="utf-8"))

        self.assertEqual(
            payload["confusion_matrix"],
            {
                "SERVER": {"SERVER": 0, "SWITCH": 0, "UNKNOWN": 1},
                "SWITCH": {"SERVER": 0, "SWITCH": 1, "UNKNOWN": 0},
            },
        )

    def test_confusion_matrix_markdown_rendering(self):
        report = BenchmarkReport(
            dataset_name="confusion_markdown",
            total_devices=3,
            correct_classifications=2,
            incorrect_classifications=1,
            accuracy_percentage=66.6666666667,
            device_type_summary={
                "SERVER": {"total": 1, "correct": 1, "incorrect": 0, "accuracy": 100.0},
                "SWITCH": {"total": 2, "correct": 1, "incorrect": 1, "accuracy": 50.0},
            },
            confusion_matrix={
                "SERVER": {"SERVER": 1, "SWITCH": 0, "UNKNOWN": 0},
                "SWITCH": {"SERVER": 0, "SWITCH": 1, "UNKNOWN": 1},
            },
            misclassification_summary={"SWITCH": {"UNKNOWN": 1}},
            mismatches=(BenchmarkMismatch("10.12.0.2", "host-2", "SWITCH", "UNKNOWN"),),
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            report_path = write_markdown_report(report, output_dir, "2026-07-24T12:35:00Z")
            content = report_path.read_text(encoding="utf-8")

        self.assertIn("## Confusion Matrix", content)
        self.assertIn("| Expected \\ Actual | SERVER | SWITCH | UNKNOWN |", content)
        self.assertIn("| SERVER | 1 | 0 | 0 |", content)
        self.assertIn("| SWITCH | 0 | 1 | 1 |", content)

    def test_confusion_matrix_console_rendering(self):
        report = BenchmarkReport(
            dataset_name="confusion_console",
            total_devices=2,
            correct_classifications=1,
            incorrect_classifications=1,
            accuracy_percentage=50.0,
            device_type_summary={"SERVER": {"total": 2, "correct": 1, "incorrect": 1, "accuracy": 50.0}},
            confusion_matrix={"SERVER": {"SERVER": 1, "UNKNOWN": 1}},
            misclassification_summary={"SERVER": {"UNKNOWN": 1}},
            mismatches=(BenchmarkMismatch("10.13.0.2", "host-2", "SERVER", "UNKNOWN"),),
        )

        output = render_console_report(report, "2026-07-24T12:40:00Z")

        self.assertIn("Confusion Matrix", output)
        self.assertIn("Expected \\ Actual", output)
        self.assertIn("SERVER", output)
        self.assertIn("UNKNOWN", output)


if __name__ == "__main__":
    unittest.main()
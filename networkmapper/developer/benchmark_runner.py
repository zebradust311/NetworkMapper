from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from networkmapper.classification.classifier import DeviceClassifier
from networkmapper.core.models import Device, DeviceType, ServiceEvidence


@dataclass(frozen=True)
class BenchmarkMismatch:
    """Represent one classification mismatch in a benchmark run."""

    ip_address: str
    hostname: str | None
    expected_device_type: str
    actual_device_type: str


@dataclass(frozen=True)
class BenchmarkReport:
    """Represent aggregate classification accuracy for one benchmark run."""

    dataset_name: str
    total_devices: int
    correct_classifications: int
    incorrect_classifications: int
    accuracy_percentage: float
    device_type_summary: dict[str, dict[str, float | int]]
    confusion_matrix: dict[str, dict[str, int]]
    misclassification_summary: dict[str, dict[str, int]]
    mismatches: tuple[BenchmarkMismatch, ...]


class BenchmarkRunner:
    """Run classification benchmarks against curated inventory datasets."""

    def __init__(self, classifier: DeviceClassifier | None = None) -> None:
        """Initialize a runner with an optional classifier instance."""
        self._classifier = classifier or DeviceClassifier()

    def load_inventory(self, inventory_path: str | Path) -> list[Device]:
        """Load benchmark inventory devices from a JSON file."""
        payload = self._load_json_file(inventory_path)
        device_payloads = payload.get("devices", [])

        devices: list[Device] = []
        for device_payload in device_payloads:
            devices.append(
                Device(
                    ip_address=device_payload["ip_address"],
                    hostname=device_payload.get("hostname"),
                    mac_address=device_payload.get("mac_address"),
                    vendor=device_payload.get("vendor"),
                    operating_system=device_payload.get("operating_system"),
                    computer_name=device_payload.get("computer_name"),
                    domain=device_payload.get("domain"),
                    smb_signing=device_payload.get("smb_signing"),
                    services=[
                        ServiceEvidence(
                            port=entry["port"],
                            protocol=entry.get("protocol", "tcp"),
                            service=entry.get("service"),
                            product=entry.get("product"),
                            version=entry.get("version"),
                            http_title=entry.get("http_title"),
                            tls_subject=entry.get("tls_subject"),
                            tls_issuer=entry.get("tls_issuer"),
                            http_auth_realm=entry.get("http_auth_realm"),
                        )
                        for entry in device_payload.get("services", [])
                    ],
                    device_type=DeviceType.UNKNOWN,
                    discovery_sources=device_payload.get("discovery_sources", []),
                )
            )

        return devices

    def load_expected_results(
        self,
        expected_results_path: str | Path,
    ) -> dict[str, DeviceType]:
        """Load expected device types keyed by IP address from JSON."""
        payload = self._load_json_file(expected_results_path)

        if "expected_results" in payload:
            expected_payloads = payload["expected_results"]
            expected_by_ip: dict[str, DeviceType] = {}
            for expected_payload in expected_payloads:
                ip_address = expected_payload["ip_address"]
                expected_type = self._parse_device_type(
                    expected_payload.get("device_type")
                    or expected_payload.get("expected_device_type")
                )
                expected_by_ip[ip_address] = expected_type
            return expected_by_ip

        expected_by_ip = {}
        for ip_address, device_type in payload.items():
            expected_by_ip[ip_address] = self._parse_device_type(device_type)

        return expected_by_ip

    def run_benchmark(
        self,
        inventory_path: str | Path,
        expected_results_path: str | Path,
        dataset_name: str = "benchmark",
    ) -> BenchmarkReport:
        """Run classification against one inventory and compute accuracy metrics."""
        devices = self.load_inventory(inventory_path)
        expected_by_ip = self.load_expected_results(expected_results_path)

        total_devices = len(devices)
        correct_classifications = 0
        device_type_summary_counts: dict[str, dict[str, int]] = {}
        confusion_matrix_counts: dict[str, dict[str, int]] = {}
        expected_device_types: set[str] = set()
        actual_device_types: set[str] = set()
        misclassification_summary: dict[str, dict[str, int]] = {}
        mismatches: list[BenchmarkMismatch] = []

        for device in devices:
            predicted_type = self._classifier.classify(device).device_type
            expected_type = expected_by_ip.get(device.ip_address)

            if expected_type is not None:
                type_name = expected_type.name
                summary_entry = device_type_summary_counts.setdefault(
                    type_name,
                    {"total": 0, "correct": 0, "incorrect": 0},
                )
                summary_entry["total"] += 1
                expected_device_types.add(type_name)
                actual_name = predicted_type.name
                actual_device_types.add(actual_name)
                matrix_row = confusion_matrix_counts.setdefault(type_name, {})
                matrix_row[actual_name] = matrix_row.get(actual_name, 0) + 1

            if expected_type is not None and predicted_type == expected_type:
                correct_classifications += 1
                device_type_summary_counts[expected_type.name]["correct"] += 1
                continue

            if expected_type is not None:
                device_type_summary_counts[expected_type.name]["incorrect"] += 1

            expected_name = expected_type.name if expected_type else "MISSING"
            actual_name = predicted_type.name
            expected_bucket = misclassification_summary.setdefault(expected_name, {})
            expected_bucket[actual_name] = expected_bucket.get(actual_name, 0) + 1

            mismatches.append(
                BenchmarkMismatch(
                    ip_address=device.ip_address,
                    hostname=device.hostname,
                    expected_device_type=expected_name,
                    actual_device_type=actual_name,
                )
            )

        incorrect_classifications = total_devices - correct_classifications
        accuracy_percentage = (
            (correct_classifications / total_devices) * 100 if total_devices else 0.0
        )
        device_type_summary: dict[str, dict[str, float | int]] = {}
        for device_type, counts in sorted(device_type_summary_counts.items()):
            total = counts["total"]
            correct = counts["correct"]
            incorrect = counts["incorrect"]
            device_type_summary[device_type] = {
                "total": total,
                "correct": correct,
                "incorrect": incorrect,
                "accuracy": (correct / total) * 100 if total else 0.0,
            }

        matrix_columns = sorted(expected_device_types | actual_device_types)
        confusion_matrix: dict[str, dict[str, int]] = {}
        for expected_type in sorted(expected_device_types):
            confusion_matrix[expected_type] = {
                actual_type: confusion_matrix_counts.get(expected_type, {}).get(
                    actual_type,
                    0,
                )
                for actual_type in matrix_columns
            }

        return BenchmarkReport(
            dataset_name=dataset_name,
            total_devices=total_devices,
            correct_classifications=correct_classifications,
            incorrect_classifications=incorrect_classifications,
            accuracy_percentage=accuracy_percentage,
            device_type_summary=device_type_summary,
            confusion_matrix=confusion_matrix,
            misclassification_summary={
                expected: dict(sorted(actual_counts.items()))
                for expected, actual_counts in sorted(misclassification_summary.items())
            },
            mismatches=tuple(mismatches),
        )

    def run_benchmark_directory(self, benchmark_dir: str | Path) -> BenchmarkReport:
        """Run a benchmark using the standard dataset file names in a directory."""
        benchmark_path = Path(benchmark_dir)
        return self.run_benchmark(
            inventory_path=benchmark_path / "inventory.json",
            expected_results_path=benchmark_path / "expected_results.json",
            dataset_name=benchmark_path.name,
        )

    def _load_json_file(self, path: str | Path) -> dict[str, Any]:
        with Path(path).open("r", encoding="utf-8") as file_handle:
            payload: dict[str, Any] = json.load(file_handle)
        return payload

    def _parse_device_type(self, raw_device_type: Any) -> DeviceType:
        if not isinstance(raw_device_type, str):
            raise ValueError(f"Unsupported device type value: {raw_device_type!r}")

        normalized = raw_device_type.strip()
        try:
            return DeviceType(normalized.lower())
        except ValueError:
            try:
                return DeviceType[normalized.upper()]
            except KeyError as error:
                raise ValueError(
                    f"Unsupported device type value: {raw_device_type!r}"
                ) from error


def build_argument_parser() -> argparse.ArgumentParser:
    """Build and return the benchmark CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="python -m networkmapper.developer.benchmark_runner",
        description="Run benchmark datasets and generate reports.",
    )
    parser.add_argument(
        "benchmark_directory",
        help="Path to a benchmark dataset directory containing inventory.json and expected_results.json.",
    )
    parser.add_argument(
        "--console",
        action="store_true",
        help="Print results to the terminal (default when no output flags are specified).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="write_json",
        help="Write a JSON report.",
    )
    parser.add_argument(
        "--markdown",
        action="store_true",
        dest="write_markdown",
        help="Write a Markdown report.",
    )
    parser.add_argument(
        "--output",
        default="output/benchmarks",
        help="Output directory for generated reports (default: output/benchmarks/).",
    )
    return parser


def parse_cli_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse benchmark CLI arguments."""
    return build_argument_parser().parse_args(argv)


def benchmark_report_to_dict(
    report: BenchmarkReport,
    generated_at: str,
) -> dict[str, Any]:
    """Convert a benchmark report into a serializable dictionary."""
    mismatch_rows = [
        {
            "ip_address": mismatch.ip_address,
            "hostname": mismatch.hostname,
            "expected_device_type": mismatch.expected_device_type,
            "actual_device_type": mismatch.actual_device_type,
        }
        for mismatch in report.mismatches
    ]

    return {
        "dataset_name": report.dataset_name,
        "generated_at": generated_at,
        "total_devices": report.total_devices,
        "correct_classifications": report.correct_classifications,
        "incorrect_classifications": report.incorrect_classifications,
        "accuracy_percentage": report.accuracy_percentage,
        "device_type_summary": report.device_type_summary,
        "confusion_matrix": report.confusion_matrix,
        "misclassification_summary": report.misclassification_summary,
        "mismatch_summary": {
            "total_mismatches": len(mismatch_rows),
        },
        "mismatches": mismatch_rows,
    }


def _ordered_confusion_matrix_columns(
    confusion_matrix: dict[str, dict[str, int]],
) -> list[str]:
    columns: set[str] = set()
    for actual_counts in confusion_matrix.values():
        columns.update(actual_counts.keys())
    return sorted(columns)


def render_console_report(report: BenchmarkReport, generated_at: str) -> str:
    """Render benchmark results as human-readable console text."""
    lines = [
        f"Dataset: {report.dataset_name}",
        f"Generated at: {generated_at}",
        f"Total devices: {report.total_devices}",
        f"Correct classifications: {report.correct_classifications}",
        f"Incorrect classifications: {report.incorrect_classifications}",
        f"Accuracy: {report.accuracy_percentage:.2f}%",
        "",
        "Device Type Summary",
    ]

    if not report.device_type_summary:
        lines.append("- None")
    else:
        for device_type, summary in sorted(report.device_type_summary.items()):
            lines.append(f"{device_type:<12} {summary['accuracy']:>6.1f}%")

    lines.extend(
        [
            "",
            "Misclassification Summary",
        ]
    )

    if not report.misclassification_summary:
        lines.append("- None")
    else:
        for expected_type, actual_counts in sorted(report.misclassification_summary.items()):
            for actual_type, count in sorted(actual_counts.items()):
                lines.append(f"{expected_type} -> {actual_type} : {count}")

    lines.extend(["", "Confusion Matrix"])

    if not report.confusion_matrix:
        lines.append("- None")
    else:
        expected_header = "Expected \\ Actual"
        expected_types = sorted(report.confusion_matrix.keys())
        actual_types = _ordered_confusion_matrix_columns(report.confusion_matrix)

        expected_width = max(
            len(expected_header),
            *(len(expected_type) for expected_type in expected_types),
        )
        actual_widths = {
            actual_type: max(
                len(actual_type),
                *(
                    len(str(report.confusion_matrix[expected_type].get(actual_type, 0)))
                    for expected_type in expected_types
                ),
            )
            for actual_type in actual_types
        }

        header = (
            f"{expected_header:<{expected_width}}"
            " | "
            + " | ".join(
                f"{actual_type:>{actual_widths[actual_type]}}"
                for actual_type in actual_types
            )
        )
        separator = "-" * len(header)
        lines.append(header)
        lines.append(separator)

        for expected_type in expected_types:
            row = (
                f"{expected_type:<{expected_width}}"
                " | "
                + " | ".join(
                    f"{report.confusion_matrix[expected_type].get(actual_type, 0):>{actual_widths[actual_type]}}"
                    for actual_type in actual_types
                )
            )
            lines.append(row)

    lines.extend(
        [
            "",
            "Mismatch summary:",
            f"Total mismatches: {len(report.mismatches)}",
            "Mismatch list:",
        ]
    )

    if not report.mismatches:
        lines.append("- None")
    else:
        for mismatch in report.mismatches:
            hostname = mismatch.hostname if mismatch.hostname else "N/A"
            lines.append(
                "- "
                f"IP: {mismatch.ip_address}, "
                f"Hostname: {hostname}, "
                f"Expected: {mismatch.expected_device_type}, "
                f"Actual: {mismatch.actual_device_type}"
            )

    return "\n".join(lines)


def render_markdown_report(report: BenchmarkReport, generated_at: str) -> str:
    """Render benchmark results in Markdown format."""
    lines = [
        f"# Benchmark Report: {report.dataset_name}",
        "",
        f"Generated at: {generated_at}",
        "",
        f"- Total devices: {report.total_devices}",
        f"- Correct classifications: {report.correct_classifications}",
        f"- Incorrect classifications: {report.incorrect_classifications}",
        f"- Accuracy: {report.accuracy_percentage:.2f}%",
        "",
        "## Device Type Summary",
        "",
        "| Device Type | Total | Correct | Incorrect | Accuracy |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]

    if not report.device_type_summary:
        lines.append("| None | 0 | 0 | 0 | 0.0% |")
    else:
        for device_type, summary in sorted(report.device_type_summary.items()):
            lines.append(
                f"| {device_type} | {summary['total']} | {summary['correct']} | "
                f"{summary['incorrect']} | {summary['accuracy']:.1f}% |"
            )

    lines.extend(
        [
            "",
            "## Misclassification Summary",
            "",
        ]
    )

    if not report.misclassification_summary:
        lines.append("No misclassifications.")
    else:
        lines.extend(
            [
                "| Expected | Actual | Count |",
                "| --- | --- | ---: |",
            ]
        )
        for expected_type, actual_counts in sorted(report.misclassification_summary.items()):
            for actual_type, count in sorted(actual_counts.items()):
                lines.append(f"| {expected_type} | {actual_type} | {count} |")

    lines.extend(["", "## Confusion Matrix", ""])

    if not report.confusion_matrix:
        lines.append("No benchmark data.")
    else:
        actual_types = _ordered_confusion_matrix_columns(report.confusion_matrix)
        lines.append(
            "| Expected \\ Actual | " + " | ".join(actual_types) + " |"
        )
        lines.append("| --- |" + "".join(" ---: |" for _ in actual_types))

        for expected_type in sorted(report.confusion_matrix.keys()):
            counts = report.confusion_matrix[expected_type]
            row_cells = [str(counts.get(actual_type, 0)) for actual_type in actual_types]
            lines.append("| " + expected_type + " | " + " | ".join(row_cells) + " |")

    lines.extend(
        [
            "",
            "## Mismatch summary",
            "",
            f"- Total mismatches: {len(report.mismatches)}",
            "",
            "## Mismatch list",
            "",
            "| IP address | Hostname | Expected DeviceType | Actual DeviceType |",
            "| --- | --- | --- | --- |",
        ]
    )

    if not report.mismatches:
        lines.append("| None | N/A | N/A | N/A |")
    else:
        for mismatch in report.mismatches:
            hostname = mismatch.hostname if mismatch.hostname else "N/A"
            lines.append(
                "| "
                f"{mismatch.ip_address} | "
                f"{hostname} | "
                f"{mismatch.expected_device_type} | "
                f"{mismatch.actual_device_type} "
                "|"
            )

    return "\n".join(lines) + "\n"


def report_timestamp() -> str:
    """Return a UTC timestamp string for report generation."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def write_json_report(
    report: BenchmarkReport,
    output_directory: str | Path,
    generated_at: str,
) -> Path:
    """Write benchmark report as JSON and return the report path."""
    output_path = Path(output_directory)
    output_path.mkdir(parents=True, exist_ok=True)
    report_path = output_path / f"{report.dataset_name}.json"
    with report_path.open("w", encoding="utf-8") as file_handle:
        json.dump(benchmark_report_to_dict(report, generated_at), file_handle, indent=2)
    return report_path


def write_markdown_report(
    report: BenchmarkReport,
    output_directory: str | Path,
    generated_at: str,
) -> Path:
    """Write benchmark report as Markdown and return the report path."""
    output_path = Path(output_directory)
    output_path.mkdir(parents=True, exist_ok=True)
    report_path = output_path / f"{report.dataset_name}.md"
    with report_path.open("w", encoding="utf-8") as file_handle:
        file_handle.write(render_markdown_report(report, generated_at))
    return report_path


def main(argv: list[str] | None = None) -> int:
    """Run the benchmark CLI command."""
    args = parse_cli_args(argv)

    benchmark_path = Path(args.benchmark_directory)
    if not benchmark_path.is_dir():
        print(
            f"Error: benchmark directory not found: {benchmark_path}",
            file=sys.stderr,
        )
        return 1

    runner = BenchmarkRunner()

    try:
        report = runner.run_benchmark_directory(benchmark_path)
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as error:
        print(f"Error: unable to run benchmark: {error}", file=sys.stderr)
        return 1

    generated_at = report_timestamp()

    emit_console = args.console or (not args.write_json and not args.write_markdown)
    if emit_console:
        print(render_console_report(report, generated_at))

    if args.write_json:
        json_report_path = write_json_report(report, args.output, generated_at)
        print(f"JSON report: {json_report_path}")

    if args.write_markdown:
        markdown_report_path = write_markdown_report(report, args.output, generated_at)
        print(f"Markdown report: {markdown_report_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

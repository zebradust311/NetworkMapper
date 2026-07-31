from __future__ import annotations

import io
import time
import unittest
from dataclasses import dataclass
from pathlib import Path

from devtools.benchmark import (
    BenchmarkCommandArgs,
    DEFAULT_BENCHMARK_OUTPUT,
    discover_benchmark_datasets,
    run_benchmark_command,
)


TESTS_DIRECTORY = Path("tests")


STANDARD_REGRESSION_TESTS: tuple[str, ...] = (
    "tests.test_classifier",
    "tests.test_rule_result_framework",
    "tests.test_device_classifier_evidence_api",
    "tests.test_cisco_switch_rule",
    "tests.test_dell_workstation_rule",
    "tests.test_hypervisor_hostname_rule",
    "tests.test_printer_vendor_rule",
    "tests.test_server_hostname_rule",
    "tests.test_sonicwall_firewall_rule",
    "tests.test_ubiquiti_access_point_rule",
    "tests.test_voice_vendor_rule",
)


@dataclass(frozen=True)
class ValidationResult:
    tests_run: int
    failures: int
    errors: int
    skipped: int
    exit_code: int
    passed: bool


class _QuietResult(unittest.TextTestResult):
    """Collect unittest results without emitting runner noise."""

    def __init__(self, stream, descriptions, verbosity):
        super().__init__(stream, descriptions, verbosity)


def _build_suite() -> unittest.TestSuite:
    loader = unittest.defaultTestLoader
    suite = unittest.TestSuite()
    for test_name in STANDARD_REGRESSION_TESTS:
        suite.addTests(loader.loadTestsFromName(test_name))
    return suite


def run_validation() -> ValidationResult:
    """Execute the canonical regression suite and summarize the results."""
    buffer = io.StringIO()
    runner = unittest.TextTestRunner(
        stream=buffer,
        verbosity=0,
        resultclass=_QuietResult,
    )
    result = runner.run(_build_suite())
    exit_code = 0 if result.wasSuccessful() else 1
    return ValidationResult(
        tests_run=result.testsRun,
        failures=len(result.failures),
        errors=len(result.errors),
        skipped=len(result.skipped),
        exit_code=exit_code,
        passed=result.wasSuccessful(),
    )


def format_validation_report(result: ValidationResult) -> str:
    """Format a concise, deterministic validation report."""
    status = "PASS" if result.passed else "FAIL"
    lines = [
        "========================================",
        "NetworkMapper Validation",
        "========================================",
        "",
        "Status",
        "",
        status,
        "",
        f"Tests Run: {result.tests_run}",
        f"Failures: {result.failures}",
        f"Errors: {result.errors}",
        f"Skipped: {result.skipped}",
        f"Exit Code: {result.exit_code}",
        "",
        "========================================",
    ]
    return "\n".join(lines)


def discover_test_modules(tests_directory: Path = TESTS_DIRECTORY) -> tuple[str, ...]:
    """Return every test module under tests_directory, as dotted module names.

    Comprehensive validation discovers modules dynamically rather than using a
    second hardcoded list, so it can never go stale the way
    STANDARD_REGRESSION_TESTS was found to (see
    docs/reports/TEST-001-Validation-Coverage-Assessment.md).
    """
    module_names = sorted(f"tests.{path.stem}" for path in tests_directory.glob("test_*.py"))
    return tuple(module_names)


def _build_full_test_suite() -> unittest.TestSuite:
    loader = unittest.defaultTestLoader
    suite = unittest.TestSuite()
    for test_name in discover_test_modules():
        suite.addTests(loader.loadTestsFromName(test_name))
    return suite


@dataclass(frozen=True)
class BenchmarkDatasetResult:
    """Represent one dataset's outcome within a full validation run."""

    dataset_name: str
    total_devices: int
    accuracy_percentage: float
    passed: bool


@dataclass(frozen=True)
class FullValidationResult:
    """Represent the combined outcome of every test module and every benchmark dataset."""

    tests_run: int
    failures: int
    errors: int
    skipped: int
    unit_tests_passed: bool
    benchmark_results: tuple[BenchmarkDatasetResult, ...]
    exit_code: int
    passed: bool
    runtime_seconds: float = 0.0
    first_failure_test_id: str | None = None
    first_failure_summary: str | None = None


def _first_failure_summary_line(traceback_text: str) -> str:
    """Return the final, most relevant line of a traceback for a concise summary."""
    lines = [line for line in traceback_text.strip().splitlines() if line.strip()]
    return lines[-1] if lines else traceback_text.strip()


def _first_failure(result: unittest.TestResult) -> tuple[str | None, str | None]:
    """Return the first failing test id and a concise exception summary, if any.

    Reporting only: reads detail already collected by the same test run rather
    than affecting what runs, how it runs, or the pass/fail determination.
    """
    problems = result.errors + result.failures
    if not problems:
        return None, None

    test_case, traceback_text = problems[0]
    return test_case.id(), _first_failure_summary_line(traceback_text)


def run_full_validation() -> FullValidationResult:
    """Execute every discovered test module and every discovered benchmark dataset."""
    start_time = time.monotonic()
    buffer = io.StringIO()
    runner = unittest.TextTestRunner(
        stream=buffer,
        verbosity=0,
        resultclass=_QuietResult,
    )
    result = runner.run(_build_full_test_suite())
    unit_tests_passed = result.wasSuccessful()
    first_failure_test_id, first_failure_summary = _first_failure(result)

    benchmark_results: list[BenchmarkDatasetResult] = []
    for dataset_directory in discover_benchmark_datasets():
        benchmark_result = run_benchmark_command(
            BenchmarkCommandArgs(
                benchmark_directory=dataset_directory,
                output_directory=DEFAULT_BENCHMARK_OUTPUT,
            )
        )
        benchmark_results.append(
            BenchmarkDatasetResult(
                dataset_name=benchmark_result.dataset_name,
                total_devices=benchmark_result.total_devices,
                accuracy_percentage=benchmark_result.accuracy_percentage,
                passed=benchmark_result.passed,
            )
        )

    all_benchmarks_passed = all(item.passed for item in benchmark_results)
    passed = unit_tests_passed and all_benchmarks_passed
    runtime_seconds = time.monotonic() - start_time

    return FullValidationResult(
        tests_run=result.testsRun,
        failures=len(result.failures),
        errors=len(result.errors),
        skipped=len(result.skipped),
        unit_tests_passed=unit_tests_passed,
        benchmark_results=tuple(benchmark_results),
        exit_code=0 if passed else 1,
        passed=passed,
        runtime_seconds=runtime_seconds,
        first_failure_test_id=first_failure_test_id,
        first_failure_summary=first_failure_summary,
    )


def format_full_validation_report(result: FullValidationResult) -> str:
    """Format a concise, deterministic comprehensive validation report."""
    lines = [
        "========================================",
        "NetworkMapper Full Validation",
        "========================================",
        "",
        "Unit Tests",
        "",
        "PASS" if result.unit_tests_passed else "FAIL",
        "",
        f"Tests Run: {result.tests_run}",
        f"Failures: {result.failures}",
        f"Errors: {result.errors}",
        f"Skipped: {result.skipped}",
        "",
        "Benchmarks",
    ]

    for benchmark_result in result.benchmark_results:
        lines.extend(
            [
                "",
                f"Dataset: {benchmark_result.dataset_name}",
                f"Devices: {benchmark_result.total_devices}",
                f"Accuracy: {benchmark_result.accuracy_percentage:.1f}%",
                "PASS" if benchmark_result.passed else "FAIL",
            ]
        )

    lines.extend(
        [
            "",
            "----------------------------------------",
            "",
            "Overall Status",
            "",
            "PASS" if result.passed else "FAIL",
            "",
            "========================================",
        ]
    )
    return "\n".join(lines)


def _dataset_display_name(dataset_name: str) -> str:
    """Format a dataset directory name for human-readable summary display."""
    return dataset_name.replace("_", " ").title()


def format_full_validation_summary(result: FullValidationResult) -> str:
    """Format the CI-style summary block appended after the full validation report.

    Reporting only: every value here is read from FullValidationResult, which
    format_full_validation_report() already renders in full detail above it.
    This adds a shorter, scannable summary; it changes no validation logic,
    discovery, or exit-code behavior.
    """
    passed_count = result.tests_run - result.failures - result.errors - result.skipped

    lines = [
        "=========================",
        "FULL VALIDATION SUMMARY",
        "=========================",
        "",
        "Tests",
        "",
        f"- Total executed: {result.tests_run}",
        f"- Passed: {passed_count}",
        f"- Failed: {result.failures}",
        f"- Errors: {result.errors}",
        f"- Runtime: {result.runtime_seconds:.2f}s",
        "",
        "Benchmarks",
        "",
    ]

    for benchmark_result in result.benchmark_results:
        status = "PASS" if benchmark_result.passed else "FAIL"
        lines.append(f"- {_dataset_display_name(benchmark_result.dataset_name)}: {status}")

    lines.extend(
        [
            "",
            "Overall Result",
            "",
            "PASS" if result.passed else "FAIL",
        ]
    )

    if not result.passed and result.first_failure_test_id is not None:
        lines.extend(
            [
                "",
                f"First failing test: {result.first_failure_test_id}",
                result.first_failure_summary or "",
            ]
        )

    return "\n".join(lines)

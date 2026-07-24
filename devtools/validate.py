from __future__ import annotations

import io
import unittest
from dataclasses import dataclass


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

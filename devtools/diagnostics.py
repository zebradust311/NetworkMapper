from __future__ import annotations

import platform
from dataclasses import dataclass
from pathlib import Path

from devtools.benchmark import (
    DEFAULT_BENCHMARK_DATASET,
    DEFAULT_BENCHMARK_OUTPUT,
    BenchmarkCommandArgs,
    run_benchmark_command,
)
from devtools.validate import run_validation


@dataclass(frozen=True)
class DiagnosticCheck:
    name: str
    passed: bool


@dataclass(frozen=True)
class DiagnosticsResult:
    checks: tuple[DiagnosticCheck, ...]
    exit_code: int


def _check_python_runtime() -> DiagnosticCheck:
    version = platform.python_version_tuple()
    passed = len(version) == 3 and all(part.isdigit() for part in version)
    return DiagnosticCheck(name="Python Runtime", passed=passed)


def _check_imports() -> DiagnosticCheck:
    try:
        from networkmapper.application import Application  # noqa: F401
        from networkmapper.classification.device_classifier import DeviceClassifier  # noqa: F401
        from networkmapper.developer.benchmark_runner import BenchmarkRunner  # noqa: F401
        from networkmapper.project.serializer import ProjectSerializer  # noqa: F401
    except Exception:
        return DiagnosticCheck(name="Imports", passed=False)

    return DiagnosticCheck(name="Imports", passed=True)


def _check_project_structure() -> DiagnosticCheck:
    required_paths = (
        Path("main.py"),
        Path("README.md"),
        Path("ENGINEERING.md"),
        Path("ROADMAP.md"),
        Path("networkmapper"),
        Path("tests"),
        Path("benchmarks"),
        Path("devtools"),
    )
    passed = all(path.exists() for path in required_paths)
    return DiagnosticCheck(name="Project Structure", passed=passed)


def _check_developer_platform() -> DiagnosticCheck:
    required_paths = (
        Path("devtools") / "__main__.py",
        Path("devtools") / "validate.py",
        Path("devtools") / "benchmark.py",
        Path("devtools") / "compare.py",
        Path("devtools") / "diagnostics.py",
        Path("devtools") / "README.md",
    )
    passed = all(path.exists() for path in required_paths)
    return DiagnosticCheck(name="Developer Platform", passed=passed)


def _check_classifier_validation() -> DiagnosticCheck:
    result = run_validation()
    return DiagnosticCheck(name="Validation", passed=result.passed)


def _check_benchmark_validation() -> DiagnosticCheck:
    result = run_benchmark_command(
        BenchmarkCommandArgs(
            benchmark_directory=Path("benchmarks") / DEFAULT_BENCHMARK_DATASET,
            output_directory=DEFAULT_BENCHMARK_OUTPUT,
        )
    )
    return DiagnosticCheck(name="Benchmark", passed=result.passed)


def run_diagnostics() -> DiagnosticsResult:
    """Run deterministic pre-flight checks for the developer environment."""
    checks = (
        _check_python_runtime(),
        _check_imports(),
        _check_project_structure(),
        _check_developer_platform(),
        _check_classifier_validation(),
        _check_benchmark_validation(),
    )
    passed = all(check.passed for check in checks)
    return DiagnosticsResult(checks=checks, exit_code=0 if passed else 1)


def format_diagnostics_report(result: DiagnosticsResult) -> str:
    """Format a concise deterministic diagnostics report."""
    lines = [
        "========================================",
        "NetworkMapper Diagnostics",
        "========================================",
        "",
    ]

    for check in result.checks:
        lines.append(check.name)
        lines.append("PASS" if check.passed else "FAIL")
        lines.append("")

    lines.extend(
        [
            "----------------------------------------",
            "",
            "Overall Status",
            "",
            "PASS" if result.exit_code == 0 else "FAIL",
            "",
            "========================================",
        ]
    )
    return "\n".join(lines)
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

from networkmapper.developer.benchmark_runner import (
    BenchmarkRunner,
    report_timestamp,
    write_json_report,
    write_markdown_report,
)


DEFAULT_BENCHMARK_DATASET = "homelab"
DEFAULT_BENCHMARK_ROOT = Path("benchmarks")
DEFAULT_BENCHMARK_OUTPUT = Path("output/benchmarks")


@dataclass(frozen=True)
class BenchmarkCommandArgs:
    benchmark_directory: Path
    output_directory: Path


@dataclass(frozen=True)
class BenchmarkCommandResult:
    dataset_name: str
    total_devices: int
    accuracy_percentage: float
    output_directory: Path
    exit_code: int
    passed: bool


def discover_benchmark_datasets(root: Path = DEFAULT_BENCHMARK_ROOT) -> tuple[Path, ...]:
    """Return every benchmark dataset directory with both required fixture files.

    Used by full validation so new datasets are picked up automatically,
    rather than requiring a second hardcoded list to stay in sync.
    """
    if not root.is_dir():
        return ()

    datasets = [
        entry
        for entry in sorted(root.iterdir())
        if entry.is_dir()
        and (entry / "inventory.json").is_file()
        and (entry / "expected_results.json").is_file()
    ]
    return tuple(datasets)


def build_argument_parser() -> argparse.ArgumentParser:
    """Build and return the benchmark command parser."""
    parser = argparse.ArgumentParser(
        prog="python -m devtools benchmark",
        description="Run NetworkMapper benchmark datasets with standardized output.",
    )
    parser.add_argument(
        "dataset",
        nargs="?",
        default=DEFAULT_BENCHMARK_DATASET,
        help=(
            "Benchmark dataset name under benchmarks/ or a dataset directory path "
            "(default: homelab)."
        ),
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_BENCHMARK_OUTPUT),
        help="Output directory for benchmark reports (default: output/benchmarks).",
    )
    return parser


def parse_args(argv: list[str] | None = None) -> BenchmarkCommandArgs:
    """Parse CLI arguments into canonical benchmark command arguments."""
    namespace = build_argument_parser().parse_args(argv)
    dataset_input = Path(namespace.dataset)
    if dataset_input.is_dir():
        benchmark_directory = dataset_input
    else:
        benchmark_directory = DEFAULT_BENCHMARK_ROOT / namespace.dataset

    return BenchmarkCommandArgs(
        benchmark_directory=benchmark_directory,
        output_directory=Path(namespace.output),
    )


def run_benchmark_command(args: BenchmarkCommandArgs) -> BenchmarkCommandResult:
    """Execute benchmark command using the existing benchmark framework."""
    benchmark_directory = args.benchmark_directory
    if not benchmark_directory.is_dir():
        return BenchmarkCommandResult(
            dataset_name=benchmark_directory.name,
            total_devices=0,
            accuracy_percentage=0.0,
            output_directory=args.output_directory,
            exit_code=1,
            passed=False,
        )

    runner = BenchmarkRunner()
    try:
        report = runner.run_benchmark_directory(benchmark_directory)
    except (FileNotFoundError, ValueError, json.JSONDecodeError):
        return BenchmarkCommandResult(
            dataset_name=benchmark_directory.name,
            total_devices=0,
            accuracy_percentage=0.0,
            output_directory=args.output_directory,
            exit_code=1,
            passed=False,
        )

    generated_at = report_timestamp()
    write_json_report(report, args.output_directory, generated_at)
    write_markdown_report(report, args.output_directory, generated_at)

    return BenchmarkCommandResult(
        dataset_name=report.dataset_name,
        total_devices=report.total_devices,
        accuracy_percentage=report.accuracy_percentage,
        output_directory=args.output_directory,
        exit_code=0,
        passed=True,
    )


def format_benchmark_report(result: BenchmarkCommandResult) -> str:
    """Format concise deterministic benchmark output."""
    status = "PASS" if result.passed else "FAIL"
    lines = [
        "========================================",
        "NetworkMapper Benchmark",
        "========================================",
        "",
        f"Dataset: {result.dataset_name}",
        "",
        f"Devices: {result.total_devices}",
        "",
        f"Accuracy: {result.accuracy_percentage:.1f}%",
        "",
        status,
    ]

    if result.passed:
        lines.extend(
            [
                "",
                "Reports written to:",
                "",
                f"{result.output_directory.as_posix()}/",
            ]
        )

    lines.extend(
        [
            "",
            "========================================",
        ]
    )
    return "\n".join(lines)

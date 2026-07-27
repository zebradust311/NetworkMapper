from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_REPORT_DIRECTORY = Path("output/benchmarks")


@dataclass(frozen=True)
class CompareArgs:
    baseline_report: Path
    candidate_report: Path


@dataclass(frozen=True)
class DeltaRow:
    key: str
    baseline: float
    candidate: float
    delta: float


@dataclass(frozen=True)
class CountDeltaRow:
    key: str
    baseline: int
    candidate: int
    delta: int


@dataclass(frozen=True)
class CompareResult:
    baseline_label: str
    candidate_label: str
    overall: DeltaRow
    per_device_type: tuple[DeltaRow, ...]
    misclassification: tuple[CountDeltaRow, ...]
    confusion_off_diagonal_baseline: int
    confusion_off_diagonal_candidate: int
    confusion_off_diagonal_delta: int
    confusion_changed_cells: int
    confusion_improved_cells: int
    confusion_regressed_cells: int
    confusion_unchanged_cells: int
    exit_code: int


def build_argument_parser() -> argparse.ArgumentParser:
    """Build and return the compare command parser."""
    parser = argparse.ArgumentParser(
        prog="python -m devtools compare",
        description="Compare two benchmark JSON reports.",
    )
    parser.add_argument(
        "baseline_report",
        nargs="?",
        help="Path to baseline benchmark JSON report.",
    )
    parser.add_argument(
        "candidate_report",
        nargs="?",
        help="Path to candidate benchmark JSON report.",
    )
    return parser


def _default_reports() -> tuple[Path, Path] | None:
    if not DEFAULT_REPORT_DIRECTORY.is_dir():
        return None

    reports = sorted(DEFAULT_REPORT_DIRECTORY.glob("*.json"))
    if len(reports) < 2:
        return None

    return reports[0], reports[1]


def parse_args(argv: list[str] | None = None) -> CompareArgs:
    """Parse compare command arguments with deterministic defaults."""
    namespace = build_argument_parser().parse_args(argv)

    if namespace.baseline_report and namespace.candidate_report:
        return CompareArgs(
            baseline_report=Path(namespace.baseline_report),
            candidate_report=Path(namespace.candidate_report),
        )

    if namespace.baseline_report or namespace.candidate_report:
        raise ValueError("Provide both baseline and candidate report paths.")

    defaults = _default_reports()
    if defaults is None:
        raise ValueError(
            "Unable to locate two benchmark reports. "
            "Run benchmark first or pass explicit report paths."
        )

    return CompareArgs(baseline_report=defaults[0], candidate_report=defaults[1])


def _load_report(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file_handle:
        payload = json.load(file_handle)
    if not isinstance(payload, dict):
        raise ValueError(f"Unsupported benchmark report format: {path}")
    return payload


def _status_for_delta(delta: float) -> str:
    if delta > 0:
        return "IMPROVED"
    if delta < 0:
        return "REGRESSED"
    return "UNCHANGED"


def _status_for_misclassification_delta(delta: int) -> str:
    if delta < 0:
        return "IMPROVED"
    if delta > 0:
        return "REGRESSED"
    return "UNCHANGED"


def _flatten_misclassifications(
    payload: dict[str, Any],
) -> dict[str, int]:
    summary = payload.get("misclassification_summary", {})
    flattened: dict[str, int] = {}
    if not isinstance(summary, dict):
        return flattened

    for expected_type, actual_counts in summary.items():
        if not isinstance(actual_counts, dict):
            continue
        for actual_type, count in actual_counts.items():
            key = f"{expected_type} -> {actual_type}"
            flattened[key] = int(count)
    return flattened


def _flatten_confusion_matrix(payload: dict[str, Any]) -> dict[str, int]:
    matrix = payload.get("confusion_matrix", {})
    flattened: dict[str, int] = {}
    if not isinstance(matrix, dict):
        return flattened

    for expected_type, actual_counts in matrix.items():
        if not isinstance(actual_counts, dict):
            continue
        for actual_type, count in actual_counts.items():
            key = f"{expected_type} -> {actual_type}"
            flattened[key] = int(count)
    return flattened


def _off_diagonal_total(matrix_payload: dict[str, Any]) -> int:
    matrix = matrix_payload.get("confusion_matrix", {})
    if not isinstance(matrix, dict):
        return 0

    total = 0
    for expected_type, actual_counts in matrix.items():
        if not isinstance(actual_counts, dict):
            continue
        for actual_type, count in actual_counts.items():
            if expected_type != actual_type:
                total += int(count)
    return total


def compare_reports(args: CompareArgs) -> CompareResult:
    """Compare two benchmark reports and return deterministic summary data."""
    baseline_payload = _load_report(args.baseline_report)
    candidate_payload = _load_report(args.candidate_report)

    baseline_name = str(baseline_payload.get("dataset_name", args.baseline_report.name))
    candidate_name = str(candidate_payload.get("dataset_name", args.candidate_report.name))

    baseline_accuracy = float(baseline_payload.get("accuracy_percentage", 0.0))
    candidate_accuracy = float(candidate_payload.get("accuracy_percentage", 0.0))
    overall = DeltaRow(
        key="Overall accuracy",
        baseline=baseline_accuracy,
        candidate=candidate_accuracy,
        delta=candidate_accuracy - baseline_accuracy,
    )

    baseline_types = baseline_payload.get("device_type_summary", {})
    candidate_types = candidate_payload.get("device_type_summary", {})
    all_device_types = sorted(
        set(baseline_types.keys()) | set(candidate_types.keys())
    )
    per_device_rows: list[DeltaRow] = []
    for device_type in all_device_types:
        baseline_type_accuracy = float(
            baseline_types.get(device_type, {}).get("accuracy", 0.0)
        )
        candidate_type_accuracy = float(
            candidate_types.get(device_type, {}).get("accuracy", 0.0)
        )
        per_device_rows.append(
            DeltaRow(
                key=device_type,
                baseline=baseline_type_accuracy,
                candidate=candidate_type_accuracy,
                delta=candidate_type_accuracy - baseline_type_accuracy,
            )
        )

    baseline_misclassification = _flatten_misclassifications(baseline_payload)
    candidate_misclassification = _flatten_misclassifications(candidate_payload)
    all_misclassification_keys = sorted(
        set(baseline_misclassification.keys()) | set(candidate_misclassification.keys())
    )
    misclassification_rows: list[CountDeltaRow] = []
    for key in all_misclassification_keys:
        baseline_count = baseline_misclassification.get(key, 0)
        candidate_count = candidate_misclassification.get(key, 0)
        misclassification_rows.append(
            CountDeltaRow(
                key=key,
                baseline=baseline_count,
                candidate=candidate_count,
                delta=candidate_count - baseline_count,
            )
        )

    baseline_confusion = _flatten_confusion_matrix(baseline_payload)
    candidate_confusion = _flatten_confusion_matrix(candidate_payload)
    all_confusion_keys = sorted(set(baseline_confusion.keys()) | set(candidate_confusion.keys()))

    confusion_improved = 0
    confusion_regressed = 0
    confusion_unchanged = 0
    confusion_changed = 0
    for key in all_confusion_keys:
        baseline_count = baseline_confusion.get(key, 0)
        candidate_count = candidate_confusion.get(key, 0)
        delta = candidate_count - baseline_count
        if delta == 0:
            confusion_unchanged += 1
            continue

        confusion_changed += 1
        expected_type, actual_type = key.split(" -> ", maxsplit=1)
        if expected_type == actual_type:
            if delta > 0:
                confusion_improved += 1
            else:
                confusion_regressed += 1
        else:
            if delta < 0:
                confusion_improved += 1
            else:
                confusion_regressed += 1

    baseline_off_diagonal = _off_diagonal_total(baseline_payload)
    candidate_off_diagonal = _off_diagonal_total(candidate_payload)

    return CompareResult(
        baseline_label=baseline_name,
        candidate_label=candidate_name,
        overall=overall,
        per_device_type=tuple(per_device_rows),
        misclassification=tuple(misclassification_rows),
        confusion_off_diagonal_baseline=baseline_off_diagonal,
        confusion_off_diagonal_candidate=candidate_off_diagonal,
        confusion_off_diagonal_delta=candidate_off_diagonal - baseline_off_diagonal,
        confusion_changed_cells=confusion_changed,
        confusion_improved_cells=confusion_improved,
        confusion_regressed_cells=confusion_regressed,
        confusion_unchanged_cells=confusion_unchanged,
        exit_code=0,
    )


def format_compare_report(result: CompareResult) -> str:
    """Format deterministic compare output."""
    def format_delta_value(delta: float) -> str:
        return f"({delta:+.1f}%)"

    def format_count_delta(delta: int) -> str:
        return f"({delta:+d})"

    def top_rows(rows: tuple[DeltaRow, ...]) -> tuple[DeltaRow, ...]:
        improvements = sorted(
            (row for row in rows if row.delta > 0),
            key=lambda row: (-row.delta, row.key),
        )
        regressions = sorted(
            (row for row in rows if row.delta < 0),
            key=lambda row: (row.delta, row.key),
        )
        return tuple(improvements[:3]), tuple(regressions[:3])

    def top_count_rows(rows: tuple[CountDeltaRow, ...]) -> tuple[CountDeltaRow, ...]:
        reduced = sorted(
            (row for row in rows if row.delta < 0),
            key=lambda row: (row.delta, row.key),
        )
        increased = sorted(
            (row for row in rows if row.delta > 0),
            key=lambda row: (-row.delta, row.key),
        )
        return tuple(reduced[:3]), tuple(increased[:3])

    improved_types, regressed_types = top_rows(result.per_device_type)
    reduced_misclassifications, increased_misclassifications = top_count_rows(
        result.misclassification
    )

    lines = [
        "========================================",
        "NetworkMapper Benchmark Comparison",
        "========================================",
        "",
        "Overall Accuracy",
        f"{result.overall.baseline:.1f}%",
        "↓",
        f"{result.overall.candidate:.1f}%",
        f"{format_delta_value(result.overall.delta)}",
        "",
        "Largest Improvements",
    ]

    if not improved_types:
        lines.append("- None")
    else:
        for row in improved_types:
            lines.append(f"{row.key}")
            lines.append(f"{format_delta_value(row.delta)}")

    lines.extend(["", "Largest Regressions"])
    if not regressed_types:
        lines.append("- None")
    else:
        for row in regressed_types:
            lines.append(f"{row.key}")
            lines.append(f"{format_delta_value(row.delta)}")

    lines.extend(["", "Misclassifications Reduced"])
    if not reduced_misclassifications:
        lines.append("- None")
    else:
        for row in reduced_misclassifications:
            lines.extend(
                [
                    row.key,
                    f"{row.baseline}",
                    "↓",
                    f"{row.candidate}",
                    f"{format_count_delta(row.delta)}",
                ]
            )

    if increased_misclassifications:
        lines.extend(["", "Misclassifications Increased"])
        for row in increased_misclassifications:
            lines.extend(
                [
                    row.key,
                    f"{row.baseline}",
                    "↓",
                    f"{row.candidate}",
                    f"{format_count_delta(row.delta)}",
                ]
            )

    confusion_status = _status_for_misclassification_delta(
        result.confusion_off_diagonal_delta
    )
    lines.extend(
        [
            "",
            "Confusion Matrix Summary",
            (
                f"- Off-diagonal total: {result.confusion_off_diagonal_baseline} "
                f"→ {result.confusion_off_diagonal_candidate} "
                f"({result.confusion_off_diagonal_delta:+d}) [{confusion_status}]"
            ),
            f"- Changed cells: {result.confusion_changed_cells}",
            f"- Improved cells: {result.confusion_improved_cells}",
            f"- Regressed cells: {result.confusion_regressed_cells}",
            f"- Unchanged cells: {result.confusion_unchanged_cells}",
            "",
            "Status",
            "",
            _status_for_delta(result.overall.delta),
            "",
            "========================================",
        ]
    )

    return "\n".join(lines)

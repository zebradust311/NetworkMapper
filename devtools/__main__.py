from __future__ import annotations

import sys

from devtools.benchmark import format_benchmark_report, parse_args, run_benchmark_command
from devtools.compare import compare_reports, format_compare_report, parse_args as parse_compare_args
from devtools.diagnostics import format_diagnostics_report, run_diagnostics
from devtools.validate import (
    format_full_validation_report,
    format_full_validation_summary,
    format_validation_report,
    run_full_validation,
    run_validation,
)


def _print_usage() -> int:
    print("Usage: python -m devtools <command>")
    print("Commands:")
    print("  validate        Run the fast classifier regression suite")
    print("  validate --all  Run every test module and every benchmark dataset")
    print("  benchmark  Run canonical benchmark workflow")
    print("  compare    Compare two benchmark JSON reports")
    print("  diagnostics  Run canonical developer environment diagnostics")
    return 1


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        return _print_usage()

    command = args[0]
    if command == "validate":
        remaining = args[1:]

        if not remaining:
            result = run_validation()
            print(format_validation_report(result))
            return result.exit_code

        if remaining == ["--all"]:
            full_result = run_full_validation()
            print(format_full_validation_report(full_result))
            print()
            print(format_full_validation_summary(full_result))
            return full_result.exit_code

        return _print_usage()

    if command == "benchmark":
        benchmark_args = parse_args(args[1:])
        result = run_benchmark_command(benchmark_args)
        print(format_benchmark_report(result))
        return result.exit_code

    if command == "compare":
        try:
            compare_args = parse_compare_args(args[1:])
        except ValueError as error:
            print(f"Error: {error}")
            print("Usage: python -m devtools compare [baseline_report.json candidate_report.json]")
            return 1

        result = compare_reports(compare_args)
        print(format_compare_report(result))
        return result.exit_code

    if command == "diagnostics" and len(args) == 1:
        result = run_diagnostics()
        print(format_diagnostics_report(result))
        return result.exit_code

    return _print_usage()


if __name__ == "__main__":
    raise SystemExit(main())

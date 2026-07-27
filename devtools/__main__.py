from __future__ import annotations

import sys

from devtools.benchmark import format_benchmark_report, parse_args, run_benchmark_command
from devtools.compare import compare_reports, format_compare_report, parse_args as parse_compare_args
from devtools.validate import format_validation_report, run_validation


def _print_usage() -> int:
    print("Usage: python -m devtools <command>")
    print("Commands:")
    print("  validate   Run canonical classifier regression validation")
    print("  benchmark  Run canonical benchmark workflow")
    print("  compare    Compare two benchmark JSON reports")
    return 1


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        return _print_usage()

    command = args[0]
    if command == "validate" and len(args) == 1:
        result = run_validation()
        print(format_validation_report(result))
        return result.exit_code

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

    return _print_usage()


if __name__ == "__main__":
    raise SystemExit(main())

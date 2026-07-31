import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devtools.validate import (
    STANDARD_REGRESSION_TESTS,
    BenchmarkDatasetResult,
    FullValidationResult,
    _first_failure,
    discover_test_modules,
    format_full_validation_report,
    format_full_validation_summary,
    run_full_validation,
    run_validation,
)
from devtools.benchmark import discover_benchmark_datasets


class FastValidationBackwardCompatibilityTest(unittest.TestCase):
    def test_run_validation_still_covers_exactly_the_standard_regression_tests(self):
        result = run_validation()

        self.assertEqual(result.tests_run, 75)
        self.assertTrue(result.passed)
        self.assertEqual(result.exit_code, 0)


class DiscoverTestModulesTest(unittest.TestCase):
    def test_discovery_is_a_superset_of_the_fast_regression_list(self):
        discovered = discover_test_modules()

        for module_name in STANDARD_REGRESSION_TESTS:
            self.assertIn(module_name, discovered)

    def test_discovery_includes_modules_previously_excluded_from_validate(self):
        discovered = discover_test_modules()

        self.assertIn("tests.test_nmap_provider_scan_profile", discovered)
        self.assertIn("tests.test_benchmark_runner", discovered)
        self.assertIn("tests.test_application_cli", discovered)
        self.assertIn("tests.test_csv_exporter", discovered)

    def test_discovery_finds_more_modules_than_the_fast_regression_list(self):
        discovered = discover_test_modules()

        self.assertGreater(len(discovered), len(STANDARD_REGRESSION_TESTS))


class DiscoverBenchmarkDatasetsTest(unittest.TestCase):
    def _write_json(self, path: Path, payload: dict) -> None:
        with path.open("w", encoding="utf-8") as file_handle:
            json.dump(payload, file_handle)

    def test_only_directories_with_both_fixture_files_are_returned(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)

            complete_dataset = root / "complete"
            complete_dataset.mkdir()
            self._write_json(complete_dataset / "inventory.json", {"devices": []})
            self._write_json(complete_dataset / "expected_results.json", {"expected_results": []})

            incomplete_dataset = root / "incomplete"
            incomplete_dataset.mkdir()
            self._write_json(incomplete_dataset / "inventory.json", {"devices": []})

            (root / "stray_file.txt").write_text("not a dataset", encoding="utf-8")

            discovered = discover_benchmark_datasets(root)

            self.assertEqual(discovered, (complete_dataset,))

    def test_missing_root_returns_empty_tuple(self):
        discovered = discover_benchmark_datasets(Path("this_directory_does_not_exist"))

        self.assertEqual(discovered, ())


class FormatFullValidationReportTest(unittest.TestCase):
    def test_report_includes_unit_test_and_benchmark_sections(self):
        result = FullValidationResult(
            tests_run=125,
            failures=0,
            errors=0,
            skipped=0,
            unit_tests_passed=True,
            benchmark_results=(
                BenchmarkDatasetResult(
                    dataset_name="homelab",
                    total_devices=5,
                    accuracy_percentage=100.0,
                    passed=True,
                ),
            ),
            exit_code=0,
            passed=True,
        )

        report = format_full_validation_report(result)

        self.assertIn("NetworkMapper Full Validation", report)
        self.assertIn("Tests Run: 125", report)
        self.assertIn("Dataset: homelab", report)
        self.assertIn("Accuracy: 100.0%", report)
        self.assertIn("Overall Status", report)
        self.assertIn("PASS", report)

    def test_report_reflects_failure_when_any_component_fails(self):
        result = FullValidationResult(
            tests_run=125,
            failures=0,
            errors=1,
            skipped=0,
            unit_tests_passed=False,
            benchmark_results=(),
            exit_code=1,
            passed=False,
        )

        report = format_full_validation_report(result)

        self.assertIn("FAIL", report)


class FirstFailureTest(unittest.TestCase):
    def _run_synthetic_suite(self, test_function) -> unittest.TestResult:
        suite = unittest.TestSuite()
        suite.addTest(unittest.FunctionTestCase(test_function))
        runner = unittest.TextTestRunner(stream=io.StringIO(), verbosity=0)
        return runner.run(suite)

    def test_returns_none_when_no_failures_or_errors(self):
        result = self._run_synthetic_suite(lambda: None)

        test_id, summary = _first_failure(result)

        self.assertIsNone(test_id)
        self.assertIsNone(summary)

    def test_returns_failing_test_id_and_exception_summary(self):
        def _boom():
            raise ValueError("synthetic failure for isolated testing")

        result = self._run_synthetic_suite(_boom)

        test_id, summary = _first_failure(result)

        self.assertIsNotNone(test_id)
        self.assertIn("ValueError", summary)
        self.assertIn("synthetic failure for isolated testing", summary)


class FormatFullValidationSummaryTest(unittest.TestCase):
    def test_passing_summary_includes_ci_style_sections(self):
        result = FullValidationResult(
            tests_run=134,
            failures=0,
            errors=0,
            skipped=0,
            unit_tests_passed=True,
            benchmark_results=(
                BenchmarkDatasetResult("enterprise", 7, 100.0, True),
                BenchmarkDatasetResult("homelab", 5, 100.0, True),
                BenchmarkDatasetResult("small_office", 5, 100.0, True),
            ),
            exit_code=0,
            passed=True,
            runtime_seconds=1.08,
        )

        summary = format_full_validation_summary(result)

        self.assertIn("FULL VALIDATION SUMMARY", summary)
        self.assertIn("- Total executed: 134", summary)
        self.assertIn("- Passed: 134", summary)
        self.assertIn("- Failed: 0", summary)
        self.assertIn("- Errors: 0", summary)
        self.assertIn("- Runtime: 1.08s", summary)
        self.assertIn("- Enterprise: PASS", summary)
        self.assertIn("- Homelab: PASS", summary)
        self.assertIn("- Small Office: PASS", summary)
        self.assertIn("Overall Result", summary)
        self.assertNotIn("First failing test", summary)

    def test_failing_summary_lists_first_failure_beneath_overall_result(self):
        result = FullValidationResult(
            tests_run=134,
            failures=0,
            errors=1,
            skipped=0,
            unit_tests_passed=False,
            benchmark_results=(BenchmarkDatasetResult("homelab", 5, 100.0, True),),
            exit_code=1,
            passed=False,
            runtime_seconds=1.1,
            first_failure_test_id="tests.test_csv_exporter.CsvExporterTest.test_export_writes_expected_csv_rows",
            first_failure_summary="AttributeError: 'str' object has no attribute 'name'",
        )

        summary = format_full_validation_summary(result)

        self.assertIn("- Passed: 133", summary)
        self.assertIn("- Errors: 1", summary)
        self.assertIn("Overall Result", summary)
        overall_index = summary.index("Overall Result")
        first_failure_index = summary.index("First failing test")
        self.assertGreater(first_failure_index, overall_index)
        self.assertIn(
            "First failing test: tests.test_csv_exporter.CsvExporterTest."
            "test_export_writes_expected_csv_rows",
            summary,
        )
        self.assertIn("AttributeError: 'str' object has no attribute 'name'", summary)

    def test_failing_summary_omits_first_failure_section_when_no_test_failed(self):
        result = FullValidationResult(
            tests_run=134,
            failures=0,
            errors=0,
            skipped=0,
            unit_tests_passed=True,
            benchmark_results=(BenchmarkDatasetResult("homelab", 5, 50.0, False),),
            exit_code=1,
            passed=False,
            runtime_seconds=1.1,
        )

        summary = format_full_validation_summary(result)

        self.assertIn("- Homelab: FAIL", summary)
        self.assertNotIn("First failing test", summary)


class RunFullValidationTest(unittest.TestCase):
    # discover_test_modules/discover_benchmark_datasets are patched here to a
    # small, fixed set. Without this, run_full_validation() would discover
    # and re-run this very test file (and this very test), causing unbounded
    # recursive self-inclusion rather than a single, isolated execution.
    @patch("devtools.validate.discover_benchmark_datasets")
    @patch("devtools.validate.discover_test_modules")
    def test_aggregates_unit_test_and_benchmark_results(
        self,
        discover_test_modules_mock,
        discover_benchmark_datasets_mock,
    ):
        discover_test_modules_mock.return_value = ("tests.test_hypervisor_hostname_rule",)
        discover_benchmark_datasets_mock.return_value = (Path("benchmarks/homelab"),)

        result = run_full_validation()

        self.assertGreater(result.tests_run, 0)
        self.assertEqual(len(result.benchmark_results), 1)
        self.assertEqual(result.benchmark_results[0].dataset_name, "homelab")
        self.assertTrue(result.benchmark_results[0].passed)
        self.assertGreaterEqual(result.runtime_seconds, 0)
        self.assertIsNone(result.first_failure_test_id)
        self.assertIsNone(result.first_failure_summary)


if __name__ == "__main__":
    unittest.main()

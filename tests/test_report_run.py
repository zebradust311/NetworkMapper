import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from networkmapper import __version__
from networkmapper.discovery.scan_profile import ScanProfile
from networkmapper.reporting.report_run import RunMetadata, build_report_run_paths


class RunMetadataTest(unittest.TestCase):
    def test_version_defaults_to_the_package_version(self):
        run_metadata = RunMetadata(
            generated_at=datetime(2026, 8, 10, 13, 57, 42),
            scan_profile=ScanProfile.STANDARD,
            customer_name="Acme",
            device_count=5,
        )

        self.assertEqual(run_metadata.version, __version__)

    def test_version_can_be_overridden(self):
        run_metadata = RunMetadata(
            generated_at=datetime(2026, 8, 10, 13, 57, 42),
            scan_profile=ScanProfile.STANDARD,
            customer_name="Acme",
            device_count=5,
            version="9.9.9",
        )

        self.assertEqual(run_metadata.version, "9.9.9")


class BuildReportRunPathsTest(unittest.TestCase):
    def test_run_directory_name_encodes_timestamp_and_scan_profile(self):
        run_metadata = RunMetadata(
            generated_at=datetime(2026, 8, 10, 13, 57, 42),
            scan_profile=ScanProfile.STANDARD,
            customer_name="Acme",
            device_count=5,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            paths = build_report_run_paths(temp_dir, run_metadata)

        self.assertEqual(paths.run_directory.name, "2026-08-10_135742_standard")

    def test_markdown_and_csv_paths_live_inside_the_run_directory(self):
        run_metadata = RunMetadata(
            generated_at=datetime(2026, 8, 10, 13, 57, 42),
            scan_profile=ScanProfile.DEEP,
            customer_name="Acme",
            device_count=5,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            paths = build_report_run_paths(temp_dir, run_metadata)

        self.assertEqual(paths.markdown_path, paths.run_directory / "report.md")
        self.assertEqual(paths.csv_path, paths.run_directory / "devices.csv")

    def test_run_directory_is_created_on_disk(self):
        run_metadata = RunMetadata(
            generated_at=datetime(2026, 8, 10, 13, 57, 42),
            scan_profile=ScanProfile.FAST,
            customer_name="Acme",
            device_count=0,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            paths = build_report_run_paths(temp_dir, run_metadata)

            self.assertTrue(paths.run_directory.is_dir())

    def test_consecutive_runs_with_different_timestamps_do_not_collide(self):
        first_run = RunMetadata(
            generated_at=datetime(2026, 8, 10, 13, 57, 42),
            scan_profile=ScanProfile.STANDARD,
            customer_name="Acme",
            device_count=5,
        )
        second_run = RunMetadata(
            generated_at=datetime(2026, 8, 10, 13, 58, 1),
            scan_profile=ScanProfile.STANDARD,
            customer_name="Acme",
            device_count=6,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            first_paths = build_report_run_paths(temp_dir, first_run)
            first_paths.markdown_path.write_text("first run report", encoding="utf-8")

            second_paths = build_report_run_paths(temp_dir, second_run)

            self.assertNotEqual(first_paths.run_directory, second_paths.run_directory)
            self.assertEqual(
                first_paths.markdown_path.read_text(encoding="utf-8"),
                "first run report",
            )

    def test_standard_and_deep_runs_at_the_same_timestamp_do_not_collide(self):
        generated_at = datetime(2026, 8, 10, 13, 57, 42)
        standard_run = RunMetadata(
            generated_at=generated_at,
            scan_profile=ScanProfile.STANDARD,
            customer_name="Acme",
            device_count=5,
        )
        deep_run = RunMetadata(
            generated_at=generated_at,
            scan_profile=ScanProfile.DEEP,
            customer_name="Acme",
            device_count=5,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            standard_paths = build_report_run_paths(temp_dir, standard_run)
            deep_paths = build_report_run_paths(temp_dir, deep_run)

        self.assertNotEqual(standard_paths.run_directory, deep_paths.run_directory)

    def test_output_root_accepts_a_path_object(self):
        run_metadata = RunMetadata(
            generated_at=datetime(2026, 8, 10, 13, 57, 42),
            scan_profile=ScanProfile.FAST,
            customer_name="Acme",
            device_count=0,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            paths = build_report_run_paths(Path(temp_dir), run_metadata)

            self.assertTrue(paths.run_directory.is_relative_to(Path(temp_dir)))


if __name__ == "__main__":
    unittest.main()

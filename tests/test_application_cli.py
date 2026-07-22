import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from networkmapper.application import Application
from networkmapper.discovery.scan_profile import ScanProfile


class ApplicationCliTest(unittest.TestCase):
    def _run_application(self, argv: list[str]):
        with patch("networkmapper.application.DiscoveryEngine") as discovery_engine_mock, patch(
            "networkmapper.application.NmapProvider"
        ) as provider_mock, patch("networkmapper.application.CsvExporter") as csv_exporter_mock, patch(
            "networkmapper.application.MarkdownExporter"
        ) as markdown_exporter_mock, patch(
            "networkmapper.application.ProjectSerializer"
        ) as serializer_mock, patch(
            "networkmapper.application.ClassificationWorkbench"
        ) as workbench_mock, patch("sys.argv", argv):
            graph = type("Graph", (), {"device_count": lambda self: 1, "all_devices": lambda self: []})()
            discovery_engine_mock.return_value.discover.return_value = graph
            serializer_mock.load.return_value.network_graph.device_count.return_value = 1

            stdout = io.StringIO()
            stderr = io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                Application().run()

        return {
            "provider_mock": provider_mock,
            "csv_exporter_mock": csv_exporter_mock,
            "markdown_exporter_mock": markdown_exporter_mock,
            "workbench_mock": workbench_mock,
            "stdout": stdout.getvalue(),
            "stderr": stderr.getvalue(),
        }

    def test_application_without_arguments_preserves_existing_behavior(self):
        result = self._run_application(["networkmapper"])

        self.assertIn("NetworkMapper is starting", result["stdout"])
        self.assertIn("✓ CSV exported", result["stdout"])
        self.assertIn("✓ Markdown exported", result["stdout"])
        result["workbench_mock"].assert_not_called()
        result["csv_exporter_mock"].assert_called_once()
        result["markdown_exporter_mock"].assert_called_once()
        result["provider_mock"].assert_called_once_with(
            "172.16.100.0/24",
            scan_profile=ScanProfile.FAST,
        )

    def test_scan_profile_fast_is_supported(self):
        result = self._run_application(["networkmapper", "--scan-profile", "fast"])

        result["provider_mock"].assert_called_once_with(
            "172.16.100.0/24",
            scan_profile=ScanProfile.FAST,
        )

    def test_scan_profile_standard_is_supported(self):
        result = self._run_application(["networkmapper", "--scan-profile", "standard"])

        result["provider_mock"].assert_called_once_with(
            "172.16.100.0/24",
            scan_profile=ScanProfile.STANDARD,
        )

    def test_scan_profile_deep_is_supported(self):
        result = self._run_application(["networkmapper", "--scan-profile", "deep"])

        result["provider_mock"].assert_called_once_with(
            "172.16.100.0/24",
            scan_profile=ScanProfile.DEEP,
        )

    def test_invalid_scan_profile_exits_with_non_zero_code(self):
        with patch("sys.argv", ["networkmapper", "--scan-profile", "invalid"]):
            stdout = io.StringIO()
            stderr = io.StringIO()

            with redirect_stdout(stdout), redirect_stderr(stderr):
                with self.assertRaises(SystemExit) as context:
                    Application().run()

        self.assertNotEqual(context.exception.code, 0)
        self.assertIn("invalid --scan-profile value", stderr.getvalue())

    def test_workbench_flag_creates_expected_output_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            current_dir = Path.cwd()
            try:
                Path(temp_dir).mkdir(parents=True, exist_ok=True)
                import os
                os.chdir(temp_dir)

                with patch("networkmapper.application.DiscoveryEngine") as discovery_engine_mock, patch(
                    "networkmapper.application.NmapProvider"
                ) as provider_mock, patch("networkmapper.application.CsvExporter") as csv_exporter_mock, patch(
                    "networkmapper.application.MarkdownExporter"
                ) as markdown_exporter_mock, patch(
                    "networkmapper.application.ProjectSerializer"
                ) as serializer_mock, patch(
                    "networkmapper.application.ClassificationWorkbench"
                ) as workbench_mock:
                    graph = type("Graph", (), {"device_count": lambda self: 1, "all_devices": lambda self: []})()
                    discovery_engine_mock.return_value.discover.return_value = graph
                    serializer_mock.load.return_value.network_graph.device_count.return_value = 1
                    workbench_mock.return_value.generate.return_value = "workbench output"

                    with patch("sys.argv", ["networkmapper", "--workbench"]):
                        with redirect_stdout(io.StringIO()) as stdout:
                            Application().run()

                    workbench_output = Path(temp_dir) / "output" / "Test Network.workbench.txt"
                    self.assertTrue(workbench_output.exists())
                    self.assertIn("✓ Classification Workbench exported", stdout.getvalue())
                    workbench_mock.assert_called_once()
                    csv_exporter_mock.assert_called_once()
                    markdown_exporter_mock.assert_called_once()
                    provider_mock.assert_called_once_with(
                        "172.16.100.0/24",
                        scan_profile=ScanProfile.FAST,
                    )
            finally:
                os.chdir(current_dir)


if __name__ == "__main__":
    unittest.main()

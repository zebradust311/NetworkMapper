import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from networkmapper.application import Application


class ApplicationCliTest(unittest.TestCase):
    def test_application_without_arguments_preserves_existing_behavior(self):
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

            with redirect_stdout(io.StringIO()) as stdout:
                Application().run()

            self.assertIn("NetworkMapper is starting", stdout.getvalue())
            self.assertIn("✓ CSV exported", stdout.getvalue())
            self.assertIn("✓ Markdown exported", stdout.getvalue())
            workbench_mock.assert_not_called()
            csv_exporter_mock.assert_called_once()
            markdown_exporter_mock.assert_called_once()

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
            finally:
                os.chdir(current_dir)


if __name__ == "__main__":
    unittest.main()

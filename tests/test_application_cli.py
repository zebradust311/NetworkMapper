import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from networkmapper.application import Application
from networkmapper.discovery.run_diagnostics import HostDiagnostics, RunDiagnostics, ScanPhase
from networkmapper.discovery.scan_profile import ScanProfile


def _default_run_diagnostics(scan_profile: ScanProfile) -> RunDiagnostics:
    """Build a minimal, well-formed RunDiagnostics for tests that don't
    care about diagnostics content, so discovery-diagnostics printing has
    real data to render instead of an unconfigured mock."""
    return RunDiagnostics(
        scan_profile=scan_profile,
        hosts_discovered=0,
        enrichment_enabled=False,
        enrichment_arguments=None,
        phases=[ScanPhase(name="Host Discovery", arguments="-sn", elapsed_seconds=0.1)],
    )


class ApplicationCliTest(unittest.TestCase):
    def _run_application(self, argv: list[str], run_diagnostics: RunDiagnostics | None = None):
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
            provider_mock.return_value.run_diagnostics = run_diagnostics or _default_run_diagnostics(
                ScanProfile.FAST
            )

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
                    provider_mock.return_value.run_diagnostics = _default_run_diagnostics(
                        ScanProfile.FAST
                    )

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

    def test_fast_profile_prints_enrichment_disabled_message(self):
        result = self._run_application(
            ["networkmapper", "--scan-profile", "fast"],
            run_diagnostics=_default_run_diagnostics(ScanProfile.FAST),
        )

        self.assertIn("Discovery Diagnostics", result["stdout"])
        self.assertIn("Scan Profile: FAST", result["stdout"])
        self.assertIn("Enrichment Enabled: No", result["stdout"])
        self.assertIn("FAST profile:", result["stdout"])
        self.assertIn("Service enrichment disabled by design.", result["stdout"])

    def test_deep_profile_prints_expanded_capabilities_and_message(self):
        run_diagnostics = RunDiagnostics(
            scan_profile=ScanProfile.DEEP,
            hosts_discovered=1,
            enrichment_enabled=True,
            enrichment_arguments=(
                "-Pn -sV --version-all --script http-title --top-ports 1000 "
                "--max-retries 6 --host-timeout 15m"
            ),
            phases=[
                ScanPhase(name="Host Discovery", arguments="-sn", elapsed_seconds=1.0),
                ScanPhase(
                    name="Service Enrichment",
                    arguments=(
                        "-Pn -sV --version-all --script http-title --top-ports 1000 "
                        "--max-retries 6 --host-timeout 15m"
                    ),
                    elapsed_seconds=20.0,
                ),
            ],
            expanded_capabilities=[
                "Expanded TCP port coverage: top 1000 ports (STANDARD scans a curated 16-port set).",
                "Version detection intensity: --version-all, maximum (STANDARD uses --version-light).",
                "Additional enrichment script: sip-methods (STANDARD's script set plus this).",
                "Retry/timeout patience: --max-retries 6 --host-timeout 15m (STANDARD uses Nmap's built-in defaults).",
            ],
        )

        result = self._run_application(
            ["networkmapper", "--scan-profile", "deep"],
            run_diagnostics=run_diagnostics,
        )

        stdout = result["stdout"]
        self.assertIn("Scan Profile: DEEP", stdout)
        self.assertIn("Enrichment Enabled: Yes", stdout)
        self.assertIn("DEEP profile:", stdout)
        self.assertIn("top 1000 TCP", stdout)
        self.assertIn("unauthenticated", stdout)
        self.assertIn("Additional Capabilities Enabled:", stdout)
        self.assertIn("- Expanded TCP port coverage: top 1000 ports", stdout)
        self.assertIn("- Version detection intensity: --version-all, maximum", stdout)
        self.assertIn("- Additional enrichment script: sip-methods", stdout)
        self.assertIn("- Retry/timeout patience: --max-retries 6 --host-timeout 15m", stdout)

    def test_fast_profile_omits_additional_capabilities_section(self):
        result = self._run_application(
            ["networkmapper", "--scan-profile", "fast"],
            run_diagnostics=_default_run_diagnostics(ScanProfile.FAST),
        )

        self.assertNotIn("Additional Capabilities Enabled", result["stdout"])

    def test_standard_profile_prints_phases_and_enrichment_arguments(self):
        run_diagnostics = RunDiagnostics(
            scan_profile=ScanProfile.STANDARD,
            hosts_discovered=2,
            enrichment_enabled=True,
            enrichment_arguments="-Pn -sV --version-light --script http-title -p 80,443",
            phases=[
                ScanPhase(name="Host Discovery", arguments="-sn", elapsed_seconds=1.23),
                ScanPhase(
                    name="Service Enrichment",
                    arguments="-Pn -sV --version-light --script http-title -p 80,443",
                    elapsed_seconds=8.42,
                ),
            ],
            host_diagnostics={
                "172.16.100.10": HostDiagnostics(
                    enriched=True,
                    has_service_evidence=True,
                    has_smb_identity=False,
                    has_rdp_identity=False,
                    has_http_title=True,
                    has_tls_certificate=False,
                    has_http_auth_realm=False,
                ),
                "172.16.100.11": HostDiagnostics(
                    enriched=False,
                    has_service_evidence=False,
                    has_smb_identity=False,
                    has_rdp_identity=False,
                    has_http_title=False,
                    has_tls_certificate=False,
                    has_http_auth_realm=False,
                    missing_evidence_reasons=[
                        "No curated ports open.",
                        "SMB unreachable (port 445 not open).",
                        "RDP unreachable (port 3389 not open).",
                        "HTTP service not present.",
                    ],
                ),
            },
        )

        result = self._run_application(
            ["networkmapper", "--scan-profile", "standard"],
            run_diagnostics=run_diagnostics,
        )

        stdout = result["stdout"]
        self.assertIn("Scan Profile: STANDARD", stdout)
        self.assertIn("Enrichment Enabled: Yes", stdout)
        self.assertIn(
            "Enrichment Arguments: -Pn -sV --version-light --script http-title -p 80,443",
            stdout,
        )
        self.assertIn("- Host Discovery (-sn) — 1.23s", stdout)
        self.assertIn(
            "- Service Enrichment (-Pn -sV --version-light --script http-title -p 80,443) — 8.42s",
            stdout,
        )
        self.assertIn("Hosts Discovered            : 2", stdout)
        self.assertIn("Hosts Enriched              : 1", stdout)
        self.assertIn("Hosts with Service Evidence : 1", stdout)
        self.assertIn("Hosts with HTTP Titles      : 1", stdout)
        self.assertIn("Per-Host Diagnostics (no enrichment evidence collected)", stdout)
        self.assertIn("172.16.100.11:", stdout)
        self.assertIn("  - No curated ports open.", stdout)
        self.assertIn("  - SMB unreachable (port 445 not open).", stdout)
        self.assertNotIn("172.16.100.10:", stdout)

    def test_fully_enriched_run_omits_per_host_diagnostics_section(self):
        run_diagnostics = RunDiagnostics(
            scan_profile=ScanProfile.STANDARD,
            hosts_discovered=1,
            enrichment_enabled=True,
            enrichment_arguments="-Pn -sV --version-light --script http-title -p 80",
            phases=[
                ScanPhase(name="Host Discovery", arguments="-sn", elapsed_seconds=1.0),
                ScanPhase(
                    name="Service Enrichment",
                    arguments="-Pn -sV --version-light --script http-title -p 80",
                    elapsed_seconds=2.0,
                ),
            ],
            host_diagnostics={
                "172.16.100.20": HostDiagnostics(
                    enriched=True,
                    has_service_evidence=True,
                    has_smb_identity=False,
                    has_rdp_identity=False,
                    has_http_title=True,
                    has_tls_certificate=False,
                    has_http_auth_realm=False,
                ),
            },
        )

        result = self._run_application(
            ["networkmapper", "--scan-profile", "standard"],
            run_diagnostics=run_diagnostics,
        )

        self.assertNotIn("Per-Host Diagnostics", result["stdout"])

    def test_phase_without_elapsed_time_prints_unknown(self):
        run_diagnostics = RunDiagnostics(
            scan_profile=ScanProfile.FAST,
            hosts_discovered=0,
            enrichment_enabled=False,
            enrichment_arguments=None,
            phases=[ScanPhase(name="Host Discovery", arguments="-sn", elapsed_seconds=None)],
        )

        result = self._run_application(
            ["networkmapper", "--scan-profile", "fast"],
            run_diagnostics=run_diagnostics,
        )

        self.assertIn("- Host Discovery (-sn) — unknown", result["stdout"])


if __name__ == "__main__":
    unittest.main()

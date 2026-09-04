import io
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import ANY, patch

from networkmapper.application import Application, SNMP_COMMUNITY_ENV_VAR
from networkmapper.discovery.local_subnet import DetectedLocalSubnet
from networkmapper.discovery.run_diagnostics import HostDiagnostics, RunDiagnostics, ScanPhase
from networkmapper.discovery.scan_profile import ScanProfile
from networkmapper.discovery.snmp_bridge_fdb_diagnostics import SnmpBridgeFdbRunDiagnostics
from networkmapper.discovery.snmp_diagnostics import SnmpRunDiagnostics
from networkmapper.reporting.report_run import ReportRunPaths


def _fake_report_run_paths() -> ReportRunPaths:
    """A stand-in ReportRunPaths that avoids touching the real filesystem.

    build_report_run_paths() creates a real directory as a side effect
    (REPORT-002); tests that don't explicitly isolate a temp working
    directory must mock it out, the same way CsvExporter/MarkdownExporter
    are already mocked below, so test runs don't litter the repo's real
    output/ directory.
    """
    return ReportRunPaths(
        run_directory=Path("output/fake-run"),
        markdown_path=Path("output/fake-run/report.md"),
        csv_path=Path("output/fake-run/devices.csv"),
    )


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
    def _run_application(
        self,
        argv: list[str],
        run_diagnostics: RunDiagnostics | None = None,
        snmp_run_diagnostics: SnmpRunDiagnostics | None = None,
        bridge_fdb_run_diagnostics: SnmpBridgeFdbRunDiagnostics | None = None,
        env: dict[str, str] | None = None,
        detected_local_subnet: DetectedLocalSubnet | None = None,
    ):
        with patch("networkmapper.application.DiscoveryEngine") as discovery_engine_mock, patch(
            "networkmapper.application.NmapProvider"
        ) as provider_mock, patch(
            "networkmapper.application.detect_local_subnet"
        ) as detect_local_subnet_mock, patch(
            "networkmapper.application.SnmpEnrichmentProvider"
        ) as snmp_provider_mock, patch(
            "networkmapper.application.SnmpArpNeighborProvider"
        ) as arp_provider_mock, patch(
            "networkmapper.application.SnmpLldpNeighborProvider"
        ) as lldp_provider_mock, patch(
            "networkmapper.application.SnmpBridgeFdbProvider"
        ) as fdb_provider_mock, patch(
            "networkmapper.application.CsvExporter"
        ) as csv_exporter_mock, patch(
            "networkmapper.application.MarkdownExporter"
        ) as markdown_exporter_mock, patch(
            "networkmapper.application.ProjectSerializer"
        ) as serializer_mock, patch(
            "networkmapper.application.ClassificationWorkbench"
        ) as workbench_mock, patch(
            "networkmapper.application.build_report_run_paths"
        ) as report_run_paths_mock, patch("sys.argv", argv), patch.dict(
            os.environ, env or {}, clear=False
        ):
            graph = type("Graph", (), {"device_count": lambda self: 1, "all_devices": lambda self: []})()
            discovery_engine_mock.return_value.discover.return_value = graph
            serializer_mock.load.return_value.network_graph.device_count.return_value = 1
            provider_mock.return_value.run_diagnostics = run_diagnostics or _default_run_diagnostics(
                ScanProfile.FAST
            )
            detect_local_subnet_mock.return_value = detected_local_subnet
            snmp_provider_mock.return_value.run_diagnostics = snmp_run_diagnostics
            fdb_provider_mock.return_value.run_diagnostics = bridge_fdb_run_diagnostics
            report_run_paths_mock.return_value = _fake_report_run_paths()

            stdout = io.StringIO()
            stderr = io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                Application().run()

        return {
            "provider_mock": provider_mock,
            "detect_local_subnet_mock": detect_local_subnet_mock,
            "snmp_provider_mock": snmp_provider_mock,
            "arp_provider_mock": arp_provider_mock,
            "lldp_provider_mock": lldp_provider_mock,
            "fdb_provider_mock": fdb_provider_mock,
            "discovery_engine_mock": discovery_engine_mock,
            "csv_exporter_mock": csv_exporter_mock,
            "markdown_exporter_mock": markdown_exporter_mock,
            "workbench_mock": workbench_mock,
            "report_run_paths_mock": report_run_paths_mock,
            "stdout": stdout.getvalue(),
            "stderr": stderr.getvalue(),
        }

    def test_application_without_arguments_preserves_existing_behavior(self):
        result = self._run_application(["networkmapper", "--subnet", "172.16.100.0/24"])

        self.assertIn("NetworkMapper is starting", result["stdout"])
        self.assertIn("✓ CSV exported", result["stdout"])
        self.assertIn("✓ Markdown exported", result["stdout"])
        result["workbench_mock"].assert_not_called()
        result["csv_exporter_mock"].assert_called_once()
        result["markdown_exporter_mock"].assert_called_once()
        result["provider_mock"].assert_called_once_with(
            "172.16.100.0/24",
            scan_profile=ScanProfile.FAST,
            event_bus=ANY,
        )
        result["detect_local_subnet_mock"].assert_not_called()

    def test_report_artifacts_are_written_to_a_unique_run_directory(self):
        result = self._run_application(
            ["networkmapper", "--subnet", "172.16.100.0/24", "--scan-profile", "standard"]
        )

        report_run_paths_mock = result["report_run_paths_mock"]
        report_run_paths_mock.assert_called_once()
        output_root, run_metadata = report_run_paths_mock.call_args.args
        self.assertEqual(output_root, "output")
        self.assertEqual(run_metadata.scan_profile, ScanProfile.STANDARD)
        self.assertEqual(run_metadata.customer_name, "Test Network")
        self.assertEqual(run_metadata.device_count, 1)

        fake_paths = _fake_report_run_paths()
        result["csv_exporter_mock"].return_value.export.assert_called_once_with(
            ANY, str(fake_paths.csv_path)
        )
        result["markdown_exporter_mock"].return_value.export.assert_called_once_with(
            ANY, str(fake_paths.markdown_path), run_metadata=run_metadata
        )
        self.assertIn(f"✓ CSV exported to {fake_paths.csv_path}", result["stdout"])
        self.assertIn(f"✓ Markdown exported to {fake_paths.markdown_path}", result["stdout"])

    def test_scan_profile_fast_is_supported(self):
        result = self._run_application(
            ["networkmapper", "--subnet", "172.16.100.0/24", "--scan-profile", "fast"]
        )

        result["provider_mock"].assert_called_once_with(
            "172.16.100.0/24",
            scan_profile=ScanProfile.FAST,
            event_bus=ANY,
        )

    def test_scan_profile_standard_is_supported(self):
        result = self._run_application(
            ["networkmapper", "--subnet", "172.16.100.0/24", "--scan-profile", "standard"]
        )

        result["provider_mock"].assert_called_once_with(
            "172.16.100.0/24",
            scan_profile=ScanProfile.STANDARD,
            event_bus=ANY,
        )

    def test_scan_profile_deep_is_supported(self):
        result = self._run_application(
            ["networkmapper", "--subnet", "172.16.100.0/24", "--scan-profile", "deep"]
        )

        result["provider_mock"].assert_called_once_with(
            "172.16.100.0/24",
            scan_profile=ScanProfile.DEEP,
            event_bus=ANY,
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
                ) as provider_mock, patch(
                    "networkmapper.application.detect_local_subnet"
                ) as detect_local_subnet_mock, patch(
                    "networkmapper.application.CsvExporter"
                ) as csv_exporter_mock, patch(
                    "networkmapper.application.MarkdownExporter"
                ) as markdown_exporter_mock, patch(
                    "networkmapper.application.ProjectSerializer"
                ) as serializer_mock, patch(
                    "networkmapper.application.ClassificationWorkbench"
                ) as workbench_mock, patch(
                    "networkmapper.application.build_report_run_paths"
                ) as report_run_paths_mock:
                    graph = type("Graph", (), {"device_count": lambda self: 1, "all_devices": lambda self: []})()
                    discovery_engine_mock.return_value.discover.return_value = graph
                    serializer_mock.load.return_value.network_graph.device_count.return_value = 1
                    workbench_mock.return_value.generate.return_value = "workbench output"
                    provider_mock.return_value.run_diagnostics = _default_run_diagnostics(
                        ScanProfile.FAST
                    )
                    report_run_paths_mock.return_value = _fake_report_run_paths()

                    with patch(
                        "sys.argv",
                        ["networkmapper", "--subnet", "172.16.100.0/24", "--workbench"],
                    ):
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
                        event_bus=ANY,
                    )
                    detect_local_subnet_mock.assert_not_called()
            finally:
                os.chdir(current_dir)

    def test_fast_profile_prints_enrichment_disabled_message(self):
        result = self._run_application(
            ["networkmapper", "--subnet", "172.16.100.0/24", "--scan-profile", "fast"],
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
            ["networkmapper", "--subnet", "172.16.100.0/24", "--scan-profile", "deep"],
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
            ["networkmapper", "--subnet", "172.16.100.0/24", "--scan-profile", "fast"],
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
            ["networkmapper", "--subnet", "172.16.100.0/24", "--scan-profile", "standard"],
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
            ["networkmapper", "--subnet", "172.16.100.0/24", "--scan-profile", "standard"],
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
            ["networkmapper", "--subnet", "172.16.100.0/24", "--scan-profile", "fast"],
            run_diagnostics=run_diagnostics,
        )

        self.assertIn("- Host Discovery (-sn) — unknown", result["stdout"])

    def test_snmp_flag_absent_by_default(self):
        result = self._run_application(["networkmapper", "--subnet", "172.16.100.0/24"])

        result["snmp_provider_mock"].assert_not_called()
        engine_call = result["discovery_engine_mock"].call_args
        self.assertEqual(engine_call.kwargs["enrichment_providers"], [])

    def test_snmp_flag_without_community_env_var_exits_with_non_zero_code(self):
        with patch("networkmapper.application.DiscoveryEngine"), patch(
            "networkmapper.application.NmapProvider"
        ) as provider_mock, patch("networkmapper.application.detect_local_subnet"), patch(
            "sys.argv", ["networkmapper", "--subnet", "172.16.100.0/24", "--snmp"]
        ), patch.dict(
            os.environ, {}, clear=False
        ):
            os.environ.pop(SNMP_COMMUNITY_ENV_VAR, None)
            provider_mock.return_value.run_diagnostics = _default_run_diagnostics(ScanProfile.FAST)

            stdout = io.StringIO()
            stderr = io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                with self.assertRaises(SystemExit) as context:
                    Application().run()

        self.assertNotEqual(context.exception.code, 0)
        self.assertIn(SNMP_COMMUNITY_ENV_VAR, stderr.getvalue())

    def test_snmp_flag_with_community_env_var_enables_snmp_enrichment(self):
        result = self._run_application(
            ["networkmapper", "--subnet", "172.16.100.0/24", "--snmp"],
            env={SNMP_COMMUNITY_ENV_VAR: "s3cr3t-community"},
            snmp_run_diagnostics=SnmpRunDiagnostics(
                hosts_eligible=2,
                hosts_queried=2,
                hosts_responded=1,
                hosts_timed_out=1,
                version="v2c",
            ),
        )

        result["snmp_provider_mock"].assert_called_once()
        credentials = result["snmp_provider_mock"].call_args.args[0]
        self.assertEqual(credentials.community, "s3cr3t-community")

        engine_call = result["discovery_engine_mock"].call_args
        self.assertEqual(
            engine_call.kwargs["enrichment_providers"],
            [result["snmp_provider_mock"].return_value],
        )

        stdout = result["stdout"]
        self.assertIn("SNMP Diagnostics", stdout)
        self.assertIn("Hosts Eligible: 2", stdout)
        self.assertIn("Hosts Responded: 1", stdout)
        self.assertIn("Hosts Timed Out: 1", stdout)
        self.assertNotIn("s3cr3t-community", stdout)

    def test_snmp_flag_absent_prints_no_snmp_diagnostics(self):
        result = self._run_application(["networkmapper", "--subnet", "172.16.100.0/24"])

        self.assertNotIn("SNMP Diagnostics", result["stdout"])

    def test_snmp_bridge_fdb_flag_absent_by_default(self):
        result = self._run_application(["networkmapper", "--subnet", "172.16.100.0/24"])

        result["fdb_provider_mock"].assert_not_called()
        engine_call = result["discovery_engine_mock"].call_args
        self.assertEqual(engine_call.kwargs["enrichment_providers"], [])

    def test_snmp_bridge_fdb_flag_without_community_env_var_exits_with_non_zero_code(self):
        with patch("networkmapper.application.DiscoveryEngine"), patch(
            "networkmapper.application.NmapProvider"
        ) as provider_mock, patch("networkmapper.application.detect_local_subnet"), patch(
            "sys.argv", ["networkmapper", "--subnet", "172.16.100.0/24", "--snmp-bridge-fdb"]
        ), patch.dict(os.environ, {}, clear=False):
            os.environ.pop(SNMP_COMMUNITY_ENV_VAR, None)
            provider_mock.return_value.run_diagnostics = _default_run_diagnostics(ScanProfile.FAST)

            stdout = io.StringIO()
            stderr = io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                with self.assertRaises(SystemExit) as context:
                    Application().run()

        self.assertNotEqual(context.exception.code, 0)
        self.assertIn(SNMP_COMMUNITY_ENV_VAR, stderr.getvalue())

    def test_snmp_bridge_fdb_flag_with_community_env_var_enables_bridge_fdb_enrichment(self):
        result = self._run_application(
            ["networkmapper", "--subnet", "172.16.100.0/24", "--snmp-bridge-fdb"],
            env={SNMP_COMMUNITY_ENV_VAR: "s3cr3t-community"},
            bridge_fdb_run_diagnostics=SnmpBridgeFdbRunDiagnostics(
                hosts_eligible=2,
                hosts_queried=2,
                hosts_responded=1,
                hosts_timed_out=1,
                version="v2c",
            ),
        )

        result["fdb_provider_mock"].assert_called_once()
        credentials = result["fdb_provider_mock"].call_args.args[0]
        self.assertEqual(credentials.community, "s3cr3t-community")

        engine_call = result["discovery_engine_mock"].call_args
        self.assertEqual(
            engine_call.kwargs["enrichment_providers"],
            [result["fdb_provider_mock"].return_value],
        )

        stdout = result["stdout"]
        self.assertIn("Bridge FDB Diagnostics", stdout)
        self.assertIn("Hosts Eligible: 2", stdout)
        self.assertIn("Hosts Responded: 1", stdout)
        self.assertIn("Hosts Timed Out: 1", stdout)
        self.assertNotIn("s3cr3t-community", stdout)

    def test_snmp_bridge_fdb_flag_absent_prints_no_bridge_fdb_diagnostics(self):
        result = self._run_application(["networkmapper", "--subnet", "172.16.100.0/24"])

        self.assertNotIn("Bridge FDB Diagnostics", result["stdout"])

    def test_snmp_bridge_fdb_flag_combines_with_arp_and_lldp_flags(self):
        result = self._run_application(
            [
                "networkmapper",
                "--subnet",
                "172.16.100.0/24",
                "--snmp-arp",
                "--snmp-lldp",
                "--snmp-bridge-fdb",
            ],
            env={SNMP_COMMUNITY_ENV_VAR: "s3cr3t-community"},
            bridge_fdb_run_diagnostics=SnmpBridgeFdbRunDiagnostics(
                hosts_eligible=1, hosts_queried=1, hosts_responded=1, hosts_timed_out=0, version="v2c"
            ),
        )

        result["arp_provider_mock"].assert_called_once()
        result["lldp_provider_mock"].assert_called_once()
        result["fdb_provider_mock"].assert_called_once()

        engine_call = result["discovery_engine_mock"].call_args
        self.assertEqual(
            engine_call.kwargs["enrichment_providers"],
            [
                result["arp_provider_mock"].return_value,
                result["lldp_provider_mock"].return_value,
                result["fdb_provider_mock"].return_value,
            ],
        )
        self.assertIn("Bridge FDB Diagnostics", result["stdout"])
        self.assertNotIn("s3cr3t-community", result["stdout"])

    # ------------------------------------------------------------------
    # FEAT-013A: configurable multi-subnet discovery / local-subnet
    # auto-detection (PLAN-013A Revision 3)
    # ------------------------------------------------------------------

    def test_explicit_single_subnet_overrides_local_detection(self):
        result = self._run_application(
            ["networkmapper", "--subnet", "172.16.100.0/24"],
            detected_local_subnet=DetectedLocalSubnet(
                source_address="10.0.0.5", subnet_cidr="10.0.0.0/24"
            ),
        )

        result["detect_local_subnet_mock"].assert_not_called()
        result["provider_mock"].assert_called_once_with(
            "172.16.100.0/24", scan_profile=ScanProfile.FAST, event_bus=ANY
        )

    def test_explicit_multiple_subnets_bypass_local_detection(self):
        result = self._run_application(
            ["networkmapper", "--subnet", "172.16.100.0/24", "--subnet", "172.16.101.0/24"],
            detected_local_subnet=DetectedLocalSubnet(
                source_address="10.0.0.5", subnet_cidr="10.0.0.0/24"
            ),
        )

        result["detect_local_subnet_mock"].assert_not_called()
        self.assertEqual(result["provider_mock"].call_count, 2)
        self.assertEqual(
            [call.args[0] for call in result["provider_mock"].call_args_list],
            ["172.16.100.0/24", "172.16.101.0/24"],
        )

    def test_no_subnet_supplied_uses_detected_local_subnet(self):
        result = self._run_application(
            ["networkmapper"],
            detected_local_subnet=DetectedLocalSubnet(
                source_address="192.168.1.55", subnet_cidr="192.168.1.0/24"
            ),
        )

        result["detect_local_subnet_mock"].assert_called_once()
        result["provider_mock"].assert_called_once_with(
            "192.168.1.0/24", scan_profile=ScanProfile.FAST, event_bus=ANY
        )

    def test_detected_source_address_and_subnet_are_both_printed_before_discovery_begins(self):
        result = self._run_application(
            ["networkmapper"],
            detected_local_subnet=DetectedLocalSubnet(
                source_address="192.168.1.55", subnet_cidr="192.168.1.0/24"
            ),
        )

        stdout = result["stdout"]
        self.assertIn("192.168.1.55", stdout)
        self.assertIn("192.168.1.0/24", stdout)

        announcement_index = stdout.index("192.168.1.55")
        diagnostics_index = stdout.index("Discovery Diagnostics")
        self.assertLess(announcement_index, diagnostics_index)

    def test_local_detection_failure_exits_cleanly(self):
        with patch("networkmapper.application.DiscoveryEngine") as discovery_engine_mock, patch(
            "networkmapper.application.NmapProvider"
        ) as provider_mock, patch(
            "networkmapper.application.detect_local_subnet"
        ) as detect_local_subnet_mock, patch("sys.argv", ["networkmapper"]):
            detect_local_subnet_mock.return_value = None

            stdout = io.StringIO()
            stderr = io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                with self.assertRaises(SystemExit) as context:
                    Application().run()

        self.assertNotEqual(context.exception.code, 0)
        self.assertIn("--subnet", stderr.getvalue())
        provider_mock.assert_not_called()
        discovery_engine_mock.assert_not_called()

    def test_duplicate_subnets_construct_only_one_provider(self):
        result = self._run_application(
            ["networkmapper", "--subnet", "172.16.100.0/24", "--subnet", "172.16.100.0/24"]
        )

        result["provider_mock"].assert_called_once_with(
            "172.16.100.0/24", scan_profile=ScanProfile.FAST, event_bus=ANY
        )

    def test_invalid_subnet_exits_before_any_provider_is_constructed(self):
        with patch("networkmapper.application.DiscoveryEngine") as discovery_engine_mock, patch(
            "networkmapper.application.NmapProvider"
        ) as provider_mock, patch("networkmapper.application.detect_local_subnet") as detect_mock, patch(
            "sys.argv", ["networkmapper", "--subnet", "not-a-cidr"]
        ):
            stdout = io.StringIO()
            stderr = io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                with self.assertRaises(SystemExit) as context:
                    Application().run()

        self.assertNotEqual(context.exception.code, 0)
        self.assertIn("not-a-cidr", stderr.getvalue())
        provider_mock.assert_not_called()
        discovery_engine_mock.assert_not_called()
        detect_mock.assert_not_called()

    def test_diagnostics_are_printed_once_per_subnet_each_labeled_with_its_cidr(self):
        first_diagnostics = RunDiagnostics(
            scan_profile=ScanProfile.FAST,
            hosts_discovered=3,
            enrichment_enabled=False,
            enrichment_arguments=None,
            phases=[ScanPhase(name="Host Discovery", arguments="-sn", elapsed_seconds=1.0)],
        )
        second_diagnostics = RunDiagnostics(
            scan_profile=ScanProfile.FAST,
            hosts_discovered=7,
            enrichment_enabled=False,
            enrichment_arguments=None,
            phases=[ScanPhase(name="Host Discovery", arguments="-sn", elapsed_seconds=2.0)],
        )

        with patch("networkmapper.application.DiscoveryEngine") as discovery_engine_mock, patch(
            "networkmapper.application.NmapProvider"
        ) as provider_mock, patch("networkmapper.application.detect_local_subnet"), patch(
            "networkmapper.application.CsvExporter"
        ), patch("networkmapper.application.MarkdownExporter"), patch(
            "networkmapper.application.ProjectSerializer"
        ) as serializer_mock, patch(
            "networkmapper.application.build_report_run_paths"
        ) as report_run_paths_mock, patch(
            "sys.argv",
            ["networkmapper", "--subnet", "172.16.100.0/24", "--subnet", "172.16.101.0/24"],
        ):
            first_provider = type("Provider", (), {"run_diagnostics": first_diagnostics})()
            second_provider = type("Provider", (), {"run_diagnostics": second_diagnostics})()
            provider_mock.side_effect = [first_provider, second_provider]

            graph = type("Graph", (), {"device_count": lambda self: 1, "all_devices": lambda self: []})()
            discovery_engine_mock.return_value.discover.return_value = graph
            serializer_mock.load.return_value.network_graph.device_count.return_value = 1
            report_run_paths_mock.return_value = _fake_report_run_paths()

            stdout = io.StringIO()
            with redirect_stdout(stdout):
                Application().run()

        output = stdout.getvalue()
        first_subnet_index = output.index("Subnet: 172.16.100.0/24")
        second_subnet_index = output.index("Subnet: 172.16.101.0/24")
        self.assertLess(first_subnet_index, second_subnet_index)
        self.assertIn("Hosts Discovered: 3", output)
        self.assertIn("Hosts Discovered: 7", output)
        # DiscoveryEngine itself is constructed exactly once, with both providers.
        discovery_engine_mock.assert_called_once()
        self.assertEqual(list(discovery_engine_mock.call_args.args[0]), [first_provider, second_provider])

    def test_existing_single_subnet_diagnostics_output_is_unchanged(self):
        result = self._run_application(
            ["networkmapper", "--subnet", "172.16.100.0/24"],
            run_diagnostics=_default_run_diagnostics(ScanProfile.FAST),
        )

        stdout = result["stdout"]
        self.assertIn("Subnet: 172.16.100.0/24", stdout)
        self.assertIn("Discovery Diagnostics", stdout)
        self.assertIn("Scan Profile: FAST", stdout)

    def test_snmp_flags_compose_with_multiple_subnets(self):
        result = self._run_application(
            [
                "networkmapper",
                "--subnet",
                "172.16.100.0/24",
                "--subnet",
                "172.16.101.0/24",
                "--snmp",
                "--snmp-arp",
                "--snmp-lldp",
                "--snmp-bridge-fdb",
            ],
            env={SNMP_COMMUNITY_ENV_VAR: "s3cr3t-community"},
        )

        self.assertEqual(result["provider_mock"].call_count, 2)
        result["snmp_provider_mock"].assert_called_once()
        result["arp_provider_mock"].assert_called_once()
        result["lldp_provider_mock"].assert_called_once()
        result["fdb_provider_mock"].assert_called_once()

        engine_call = result["discovery_engine_mock"].call_args
        self.assertEqual(
            engine_call.kwargs["enrichment_providers"],
            [
                result["snmp_provider_mock"].return_value,
                result["arp_provider_mock"].return_value,
                result["lldp_provider_mock"].return_value,
                result["fdb_provider_mock"].return_value,
            ],
        )


if __name__ == "__main__":
    unittest.main()

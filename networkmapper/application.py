"""
Main application controller for NetworkMapper.
"""


import argparse
import sys
from datetime import datetime
from pathlib import Path

from networkmapper.developer.classification_workbench import ClassificationWorkbench
from networkmapper.discovery.discovery_engine import DiscoveryEngine
from networkmapper.discovery.nmap_provider import NmapProvider
from networkmapper.discovery.run_diagnostics import RunDiagnostics, profile_message
from networkmapper.discovery.scan_profile import ScanProfile
from networkmapper.project.models import Project
from networkmapper.project.serializer import ProjectSerializer
from networkmapper.exporters.csv_exporter import CsvExporter
from networkmapper.exporters.markdown_exporter import MarkdownExporter
from networkmapper.reporting.discovery_summary import DiscoverySummary
from networkmapper.reporting.report_run import RunMetadata, build_report_run_paths


class Application:
    """Coordinates the execution of the NetworkMapper application."""

    def __init__(self) -> None:
        """Initialize the application."""
        print("Application initialized.")

    def run(self) -> None:
        """Run the temporary persistence validation harness."""
        print("NetworkMapper is starting...\n")

        parser = argparse.ArgumentParser(add_help=False)
        parser.add_argument("--workbench", action="store_true")
        parser.add_argument("--scan-profile", default="fast")
        args, _ = parser.parse_known_args()

        scan_profile = self._parse_scan_profile(args.scan_profile)

        provider = NmapProvider("172.16.100.0/24", scan_profile=scan_profile)
        engine = DiscoveryEngine([provider])

        graph = engine.discover()

        if provider.run_diagnostics is not None:
            self._print_discovery_diagnostics(scan_profile, provider.run_diagnostics)

        before_save_count = graph.device_count()
        print("\nClassification Summary")
        print("-" * 40)

        classification_counts = {}

        for device in graph.all_devices():
            device_type = device.device_type.name

            if device_type not in classification_counts:
                classification_counts[device_type] = 0

            classification_counts[device_type] += 1

        for device_type in sorted(classification_counts):
            print(f"{device_type:<15} {classification_counts[device_type]}")

        print("\nSample Classifications")
        print("-" * 80)
        print(f"{'IP Address':<16} {'Hostname':<30} {'Vendor':<20} {'Type'}")

        for device in list(graph.all_devices())[:20]:
            print(
                f"{device.ip_address:<16} "
                f"{(device.hostname or 'Unknown'):<30} "
                f"{(device.vendor or 'Unknown'):<20} "
                f"{device.device_type.name}"
            )

        print()

        project = Project(
            customer_name="Test Network",
            network_graph=graph,
        )

        if args.workbench:
            workbench_path = Path("output") / f"{project.customer_name}.workbench.txt"
            workbench_path.parent.mkdir(parents=True, exist_ok=True)
            workbench_path.write_text(
                ClassificationWorkbench().generate(project),
                encoding="utf-8",
            )
            print(f"✓ Classification Workbench exported to {workbench_path}")

        run_metadata = RunMetadata(
            generated_at=datetime.now(),
            scan_profile=scan_profile,
            customer_name=project.customer_name,
            device_count=before_save_count,
        )
        report_paths = build_report_run_paths("output", run_metadata)

        CsvExporter().export(
            project,
            str(report_paths.csv_path),
        )

        MarkdownExporter().export(
            project,
            str(report_paths.markdown_path),
            run_metadata=run_metadata,
        )

        print(f"✓ CSV exported to {report_paths.csv_path}")
        print(f"✓ Markdown exported to {report_paths.markdown_path}")

        ProjectSerializer.save(project, "output/Test Network.nmproj")

        loaded_project = ProjectSerializer.load(
            "output/Test Network.nmproj"
        )

        after_save_count = loaded_project.network_graph.device_count()

        print(f"Customer Name          : {loaded_project.customer_name}")
        print(f"Device Count (Before)  : {before_save_count}")
        print(f"Device Count (After)   : {after_save_count}")

        if before_save_count == after_save_count:
            print("\n✓ Persistence validation successful.")
        else:
            print("\n✗ Persistence validation FAILED.")

            raise RuntimeError(
                "Loaded project device count does not match saved project."
            )

    def _print_discovery_diagnostics(
        self,
        scan_profile: ScanProfile,
        run_diagnostics: RunDiagnostics,
    ) -> None:
        """Print run-level discovery diagnostics: selected profile, phases
        executed, enrichment configuration, aggregate evidence-coverage
        statistics, and per-host reasons for hosts where enrichment
        produced no evidence at all. Observability only — this prints
        information already captured during discovery; it collects
        nothing new and changes no discovery behavior."""
        print("Discovery Diagnostics")
        print("-" * 40)
        print(f"Scan Profile: {scan_profile.value.upper()}")
        print(f"Hosts Discovered: {run_diagnostics.hosts_discovered}")
        print(f"Enrichment Enabled: {'Yes' if run_diagnostics.enrichment_enabled else 'No'}")
        if run_diagnostics.enrichment_arguments:
            print(f"Enrichment Arguments: {run_diagnostics.enrichment_arguments}")

        if run_diagnostics.expanded_capabilities:
            print("\nAdditional Capabilities Enabled:")
            for capability in run_diagnostics.expanded_capabilities:
                print(f"- {capability}")

        print("\nPhases Executed:")
        for phase in run_diagnostics.phases:
            if phase.elapsed_seconds is not None:
                elapsed_display = f"{phase.elapsed_seconds:.2f}s"
            else:
                elapsed_display = "unknown"
            print(f"- {phase.name} ({phase.arguments}) — {elapsed_display}")

        print()
        print(profile_message(scan_profile))
        print()

        summary = DiscoverySummary.from_run_diagnostics(run_diagnostics)
        print("Discovery Summary")
        print("-" * 40)
        print(f"Hosts Discovered            : {summary.hosts_discovered}")
        print(f"Hosts Enriched              : {summary.hosts_enriched}")
        print(f"Hosts with Service Evidence : {summary.hosts_with_service_evidence}")
        print(f"Hosts with SMB Identity     : {summary.hosts_with_smb_identity}")
        print(f"Hosts with RDP Identity     : {summary.hosts_with_rdp_identity}")
        print(f"Hosts with HTTP Titles      : {summary.hosts_with_http_titles}")
        print(f"Hosts with TLS Certificates : {summary.hosts_with_tls_certificates}")
        print(f"Hosts with HTTP Auth Realms : {summary.hosts_with_http_auth_realms}")
        print()

        dark_hosts = {
            ip_address: diagnostics
            for ip_address, diagnostics in run_diagnostics.host_diagnostics.items()
            if not diagnostics.enriched
        }
        if dark_hosts:
            print("Per-Host Diagnostics (no enrichment evidence collected)")
            print("-" * 40)
            for ip_address, diagnostics in dark_hosts.items():
                print(f"{ip_address}:")
                for reason in diagnostics.missing_evidence_reasons:
                    print(f"  - {reason}")
            print()

    def _parse_scan_profile(self, value: str) -> ScanProfile:
        """Parse CLI scan profile value into a ScanProfile enum."""
        normalized_value = (value or "").strip().lower()
        profile_map = {
            "fast": ScanProfile.FAST,
            "standard": ScanProfile.STANDARD,
            "deep": ScanProfile.DEEP,
        }

        if normalized_value not in profile_map:
            print(
                "Error: invalid --scan-profile value. "
                "Use one of: fast, standard, deep.",
                file=sys.stderr,
            )
            raise SystemExit(2)

        return profile_map[normalized_value]
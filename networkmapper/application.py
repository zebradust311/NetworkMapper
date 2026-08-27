"""
Main application controller for NetworkMapper.
"""


import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

from networkmapper.developer.classification_workbench import ClassificationWorkbench
from networkmapper.discovery.arp_neighbor_provider import SnmpArpNeighborProvider
from networkmapper.discovery.bridge_fdb_provider import SnmpBridgeFdbProvider
from networkmapper.discovery.discovery_engine import DiscoveryEngine
from networkmapper.discovery.lldp_neighbor_provider import SnmpLldpNeighborProvider
from networkmapper.discovery.nmap_provider import NmapProvider
from networkmapper.discovery.run_diagnostics import RunDiagnostics, profile_message
from networkmapper.discovery.scan_profile import ScanProfile
from networkmapper.discovery.snmp_arp_diagnostics import SnmpArpRunDiagnostics
from networkmapper.discovery.snmp_bridge_fdb_diagnostics import SnmpBridgeFdbRunDiagnostics
from networkmapper.discovery.snmp_credentials import SnmpCredentials, SnmpVersion
from networkmapper.discovery.snmp_diagnostics import SnmpRunDiagnostics
from networkmapper.discovery.snmp_lldp_diagnostics import SnmpLldpRunDiagnostics
from networkmapper.discovery.snmp_provider import SnmpEnrichmentProvider
from networkmapper.identity.resolver import IdentityResolver
from networkmapper.relationships.resolver import RelationshipResolver
from networkmapper.project.models import Project
from networkmapper.project.serializer import ProjectSerializer
from networkmapper.exporters.csv_exporter import CsvExporter
from networkmapper.exporters.markdown_exporter import MarkdownExporter
from networkmapper.reporting.discovery_summary import DiscoverySummary
from networkmapper.reporting.report_run import RunMetadata, build_report_run_paths
from networkmapper.runtime.cli_renderer import CliRuntimeEventRenderer, render_runtime_summary
from networkmapper.runtime.events import (
    RuntimeEvent,
    RuntimeEventBus,
    RuntimeEventKind,
    RuntimePhase,
)
from networkmapper.runtime.telemetry import RuntimeTelemetryRecorder

# ARCH-012 Credential Strategy: the community string is supplied via an
# environment variable, never a CLI argument (shell-history/process-list
# exposure) and never a config file (nothing here is persisted).
SNMP_COMMUNITY_ENV_VAR = "NETWORKMAPPER_SNMP_COMMUNITY"


class Application:
    """Coordinates the execution of the NetworkMapper application."""

    def __init__(self) -> None:
        """Initialize the application."""
        print("Application initialized.")

    def run(self) -> None:
        """Run the temporary persistence validation harness."""
        event_bus = RuntimeEventBus()
        telemetry = RuntimeTelemetryRecorder()
        event_bus.subscribe(CliRuntimeEventRenderer().handle_event)
        event_bus.subscribe(telemetry.handle_event)

        print("NetworkMapper is starting...\n")
        self._publish(
            event_bus,
            RuntimePhase.APPLICATION_STARTUP,
            RuntimeEventKind.PHASE_STARTED,
            activity="Parsing CLI arguments...",
        )

        parser = argparse.ArgumentParser(add_help=False)
        parser.add_argument("--workbench", action="store_true")
        parser.add_argument("--scan-profile", default="fast")
        parser.add_argument("--snmp", action="store_true")
        parser.add_argument("--snmp-arp", action="store_true")
        parser.add_argument("--snmp-lldp", action="store_true")
        parser.add_argument("--snmp-bridge-fdb", action="store_true")
        args, _ = parser.parse_known_args()

        scan_profile = self._parse_scan_profile(args.scan_profile)

        self._publish(
            event_bus,
            RuntimePhase.APPLICATION_STARTUP,
            RuntimeEventKind.PHASE_COMPLETED,
            activity=f"Scan profile: {scan_profile.value.upper()}",
        )

        provider = NmapProvider(
            "172.16.100.0/24", scan_profile=scan_profile, event_bus=event_bus
        )

        snmp_provider = None
        arp_provider = None
        lldp_provider = None
        fdb_provider = None
        if args.snmp or args.snmp_arp or args.snmp_lldp or args.snmp_bridge_fdb:
            snmp_credentials = self._resolve_snmp_credentials()
            if args.snmp:
                snmp_provider = SnmpEnrichmentProvider(snmp_credentials, event_bus=event_bus)
            if args.snmp_arp:
                arp_provider = SnmpArpNeighborProvider(snmp_credentials, event_bus=event_bus)
            if args.snmp_lldp:
                lldp_provider = SnmpLldpNeighborProvider(snmp_credentials, event_bus=event_bus)
            if args.snmp_bridge_fdb:
                fdb_provider = SnmpBridgeFdbProvider(snmp_credentials, event_bus=event_bus)

        enrichment_providers = [
            enrichment_provider
            for enrichment_provider in (snmp_provider, arp_provider, lldp_provider, fdb_provider)
            if enrichment_provider is not None
        ]

        engine = DiscoveryEngine(
            [provider],
            enrichment_providers=enrichment_providers,
            event_bus=event_bus,
        )

        graph = engine.discover()

        if provider.run_diagnostics is not None:
            self._print_discovery_diagnostics(scan_profile, provider.run_diagnostics)

        if snmp_provider is not None and snmp_provider.run_diagnostics is not None:
            self._print_snmp_diagnostics(snmp_provider.run_diagnostics)

        if arp_provider is not None and arp_provider.run_diagnostics is not None:
            self._print_arp_diagnostics(arp_provider.run_diagnostics)

        if lldp_provider is not None and lldp_provider.run_diagnostics is not None:
            self._print_lldp_diagnostics(lldp_provider.run_diagnostics)

        if fdb_provider is not None and fdb_provider.run_diagnostics is not None:
            self._print_bridge_fdb_diagnostics(fdb_provider.run_diagnostics)

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

        identities = IdentityResolver().resolve(engine.observations)
        relationships = RelationshipResolver().resolve(engine.observations, identities)

        project = Project(
            customer_name="Test Network",
            network_graph=graph,
            observations=engine.observations,
            canonical_identities=identities,
            canonical_relationships=relationships,
        )

        if args.workbench:
            workbench_path = Path("output") / f"{project.customer_name}.workbench.txt"
            workbench_path.parent.mkdir(parents=True, exist_ok=True)
            workbench_path.write_text(
                ClassificationWorkbench().generate(project),
                encoding="utf-8",
            )
            print(f"✓ Classification Workbench exported to {workbench_path}")

        self._publish(
            event_bus,
            RuntimePhase.REPORT_GENERATION,
            RuntimeEventKind.PHASE_STARTED,
            activity="Generating Markdown and CSV reports...",
        )

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
        self._publish(
            event_bus, RuntimePhase.REPORT_GENERATION, RuntimeEventKind.PHASE_COMPLETED
        )

        self._publish(
            event_bus,
            RuntimePhase.COMPLETION,
            RuntimeEventKind.PHASE_STARTED,
            activity="Finalizing project persistence...",
        )

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

        self._publish(event_bus, RuntimePhase.COMPLETION, RuntimeEventKind.PHASE_COMPLETED)
        print(render_runtime_summary(telemetry))

    def _publish(
        self,
        event_bus: RuntimeEventBus,
        phase: RuntimePhase,
        kind: RuntimeEventKind,
        *,
        activity: str | None = None,
    ) -> None:
        """Publish one OBS-002 runtime event for a phase orchestrated directly
        by `Application` (Application Startup, Report Generation, Completion).
        Host Discovery/Service Enrichment and Classification are published by
        `NmapProvider`/`DiscoveryEngine` themselves against the same bus."""
        event_bus.publish(
            RuntimeEvent(phase=phase, kind=kind, timestamp=datetime.now(), activity=activity)
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

    def _resolve_snmp_credentials(self) -> SnmpCredentials:
        """Resolve SNMP credentials from the environment when `--snmp`,
        `--snmp-arp`, `--snmp-lldp`, or `--snmp-bridge-fdb` is passed —
        shared between all four flags (FEAT-010A; FEAT-012A extended this
        to a third; ARCH-024/FEAT-012B extends it to a fourth), so the
        operator is only ever asked for the same credential once.

        ARCH-012 Credential Strategy / Failure Model: any flag without a
        resolvable credential is an operator configuration error, not a
        per-host SNMP failure — it fails fast at startup rather than
        silently skipping enrichment for the whole run.
        """
        community = os.environ.get(SNMP_COMMUNITY_ENV_VAR)
        if not community:
            print(
                f"Error: --snmp/--snmp-arp/--snmp-lldp/--snmp-bridge-fdb "
                f"requires the {SNMP_COMMUNITY_ENV_VAR} environment "
                f"variable to be set.",
                file=sys.stderr,
            )
            raise SystemExit(2)

        return SnmpCredentials(version=SnmpVersion.V2C, community=community)

    def _print_snmp_diagnostics(self, snmp_diagnostics: SnmpRunDiagnostics) -> None:
        """Print run-level SNMP observability data: hard, directly measured
        counts only — no fabricated percentages or ETAs (OBS-002)."""
        print("SNMP Diagnostics")
        print("-" * 40)
        print(f"SNMP Version: {snmp_diagnostics.version}")
        print(f"Hosts Eligible: {snmp_diagnostics.hosts_eligible}")
        print(f"Hosts Queried: {snmp_diagnostics.hosts_queried}")
        print(f"Hosts Responded: {snmp_diagnostics.hosts_responded}")
        print(f"Hosts Timed Out: {snmp_diagnostics.hosts_timed_out}")
        if snmp_diagnostics.hosts_timed_out:
            print(
                "Note: SNMPv2c cannot distinguish an incorrect community "
                "string from SNMP being disabled or the host being "
                "unreachable on UDP/161 — all three appear as a timeout."
            )
        print()

    def _print_arp_diagnostics(self, arp_diagnostics: SnmpArpRunDiagnostics) -> None:
        """Print run-level ARP-neighbor diagnostics: hard, directly
        measured counts only — no fabricated percentages or ETAs
        (OBS-002), mirroring `_print_snmp_diagnostics`."""
        total_entries = sum(
            host.entries_returned for host in arp_diagnostics.host_diagnostics.values()
        )
        print("ARP Neighbor Diagnostics")
        print("-" * 40)
        print(f"SNMP Version: {arp_diagnostics.version}")
        print(f"Hosts Eligible: {arp_diagnostics.hosts_eligible}")
        print(f"Hosts Queried: {arp_diagnostics.hosts_queried}")
        print(f"Hosts Responded: {arp_diagnostics.hosts_responded}")
        print(f"Hosts Timed Out: {arp_diagnostics.hosts_timed_out}")
        print(f"Total ARP Entries Collected: {total_entries}")
        if arp_diagnostics.hosts_timed_out:
            print(
                "Note: SNMPv2c cannot distinguish an incorrect community "
                "string from SNMP being disabled or the host being "
                "unreachable on UDP/161 — all three appear as a timeout."
            )
        print()

    def _print_lldp_diagnostics(self, lldp_diagnostics: SnmpLldpRunDiagnostics) -> None:
        """Print run-level LLDP-neighbor diagnostics: hard, directly
        measured counts only — no fabricated percentages or ETAs
        (OBS-002), mirroring `_print_arp_diagnostics`."""
        total_entries = sum(
            host.entries_returned for host in lldp_diagnostics.host_diagnostics.values()
        )
        total_management_addresses = sum(
            host.management_addresses_returned for host in lldp_diagnostics.host_diagnostics.values()
        )
        print("LLDP Neighbor Diagnostics")
        print("-" * 40)
        print(f"SNMP Version: {lldp_diagnostics.version}")
        print(f"Hosts Eligible: {lldp_diagnostics.hosts_eligible}")
        print(f"Hosts Queried: {lldp_diagnostics.hosts_queried}")
        print(f"Hosts Responded: {lldp_diagnostics.hosts_responded}")
        print(f"Hosts Timed Out: {lldp_diagnostics.hosts_timed_out}")
        print(f"Total LLDP Neighbor Entries Collected: {total_entries}")
        print(f"Total Management Addresses Collected: {total_management_addresses}")
        if lldp_diagnostics.hosts_timed_out:
            print(
                "Note: SNMPv2c cannot distinguish an incorrect community "
                "string from SNMP being disabled or the host being "
                "unreachable on UDP/161 — all three appear as a timeout."
            )
        print()

    def _print_bridge_fdb_diagnostics(self, fdb_diagnostics: SnmpBridgeFdbRunDiagnostics) -> None:
        """Print run-level Bridge-FDB diagnostics: hard, directly
        measured counts only — no fabricated percentages or ETAs
        (OBS-002), mirroring `_print_arp_diagnostics`/`_print_lldp_diagnostics`."""
        total_entries = sum(
            host.entries_returned for host in fdb_diagnostics.host_diagnostics.values()
        )
        print("Bridge FDB Diagnostics")
        print("-" * 40)
        print(f"SNMP Version: {fdb_diagnostics.version}")
        print(f"Hosts Eligible: {fdb_diagnostics.hosts_eligible}")
        print(f"Hosts Queried: {fdb_diagnostics.hosts_queried}")
        print(f"Hosts Responded: {fdb_diagnostics.hosts_responded}")
        print(f"Hosts Timed Out: {fdb_diagnostics.hosts_timed_out}")
        print(f"Total Bridge FDB Entries Collected: {total_entries}")
        if fdb_diagnostics.hosts_timed_out:
            print(
                "Note: SNMPv2c cannot distinguish an incorrect community "
                "string from SNMP being disabled or the host being "
                "unreachable on UDP/161 — all three appear as a timeout."
            )
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
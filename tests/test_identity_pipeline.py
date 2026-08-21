"""Architectural integration test for the observation/resolution pipeline.

Protects the architectural contract established by:

- ARCH-017 — Observation Collection Pipeline
- ADR-011 — Bounded Canonical Observation Model
- ADR-012 — Canonical Identity Resolution
- ARCH-019 / ADR-013 — Relationship Runtime Integration / Canonical
  Relationship Resolution

This test verifies that the following runtime pipeline remains intact:

    Application
        ↓
    DiscoveryEngine
        ↓
    Project.observations
        ↓
    IdentityResolver → Project.canonical_identities
        ↓
    RelationshipResolver → Project.canonical_relationships

Unlike the unit tests, this test exercises the complete composition of
these layers together, through Application.run()'s own internal wiring —
not by calling either resolver manually against a captured Project, which
would prove only that the resolvers work, not that Application actually
calls them. Only the network-facing NmapProvider and report/persistence
I/O are stubbed, the same way test_application_cli.py already stubs them.
"""

import io
import unittest
from contextlib import redirect_stdout
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from networkmapper.application import Application
from networkmapper.core.models import Device, DeviceType
from networkmapper.discovery.provider import DiscoveryProvider
from networkmapper.discovery.run_diagnostics import RunDiagnostics, ScanPhase
from networkmapper.discovery.scan_profile import ScanProfile
from networkmapper.identity.models import CanonicalIdentity, IdentityCorroborationState
from networkmapper.observations.models import IdentityObservation, RelationshipObservation
from networkmapper.observations.provenance import ObservationProvenance
from networkmapper.relationships.models import CanonicalRelationship, RelationshipCorroborationState
from networkmapper.reporting.report_run import ReportRunPaths


def _observation(subject: str, property_name: str, value: str, provider: str, method: str) -> IdentityObservation:
    return IdentityObservation(
        subject=subject,
        property_name=property_name,
        value=value,
        provenance=ObservationProvenance(
            provider=provider,
            collection_method=method,
            observed_at=datetime(2026, 8, 19, 9, 0, 0),
            source_run="identity-pipeline-test-run",
        ),
    )


def _relationship_observation(
    subject: str, related_subject: str, category: str, provider: str, method: str
) -> RelationshipObservation:
    return RelationshipObservation(
        subject=subject,
        related_subject=related_subject,
        category=category,
        provenance=ObservationProvenance(
            provider=provider,
            collection_method=method,
            observed_at=datetime(2026, 8, 19, 9, 0, 0),
            source_run="identity-pipeline-test-run",
        ),
    )


class _FakeNetworkProvider(DiscoveryProvider):
    """Stands in for NmapProvider: a real DiscoveryProvider that returns
    real Device and IdentityObservation instances without touching the
    network, so DiscoveryEngine's actual discovery/observation-collection
    code path runs unmodified."""

    run_diagnostics = RunDiagnostics(
        scan_profile=ScanProfile.FAST,
        hosts_discovered=2,
        enrichment_enabled=False,
        enrichment_arguments=None,
        phases=[ScanPhase(name="Host Discovery", arguments="-sn", elapsed_seconds=0.1)],
    )

    def __init__(self, *_args, **_kwargs) -> None:
        pass

    def discover(self) -> list[Device]:
        return [
            Device(ip_address="172.16.100.10", hostname="dc-01", device_type=DeviceType.UNKNOWN),
            Device(ip_address="172.16.100.11", hostname="sw-core-01", device_type=DeviceType.UNKNOWN),
        ]

    def collect_observations(self) -> list[IdentityObservation | RelationshipObservation]:
        return [
            _observation("172.16.100.10", "hostname", "dc-01", "nmap", "host-discovery"),
            _observation("172.16.100.10", "hostname", "dc-01", "snmp", "sysName"),
            _observation("172.16.100.11", "hostname", "sw-core-01", "nmap", "host-discovery"),
            _relationship_observation(
                "172.16.100.10", "172.16.100.11", "connected_to", "nmap", "lldp-neighbor"
            ),
        ]


class IdentityPipelineIntegrationTest(unittest.TestCase):
    """Application -> DiscoveryEngine -> Project.observations ->
    IdentityResolver -> RelationshipResolver, all wired inside
    Application.run() itself (ARCH-019 Stage 2 / FEAT-009B)."""

    def test_full_runtime_chain_resolves_canonical_identities_and_relationships(self):
        captured_projects: list = []

        def _capture_project(project, _path):
            captured_projects.append(project)

        fake_report_paths = ReportRunPaths(
            run_directory=Path("output/identity-pipeline-test-run"),
            markdown_path=Path("output/identity-pipeline-test-run/report.md"),
            csv_path=Path("output/identity-pipeline-test-run/devices.csv"),
        )

        with patch("networkmapper.application.NmapProvider", _FakeNetworkProvider), patch(
            "networkmapper.application.CsvExporter"
        ) as csv_exporter_mock, patch("networkmapper.application.MarkdownExporter") as markdown_exporter_mock, patch(
            "networkmapper.application.ProjectSerializer"
        ) as serializer_mock, patch(
            "networkmapper.application.build_report_run_paths", return_value=fake_report_paths
        ), patch("sys.argv", ["networkmapper"]):
            serializer_mock.save.side_effect = _capture_project
            serializer_mock.load.return_value.network_graph.device_count.return_value = 2

            stdout = io.StringIO()
            try:
                with redirect_stdout(stdout):
                    Application().run()
            except Exception as exc:  # noqa: BLE001 - validation must surface any exception
                self.fail(f"Application.run() raised an unexpected exception: {exc!r}")

        # Application completed successfully.
        self.assertIn("NetworkMapper is starting", stdout.getvalue())
        csv_exporter_mock.return_value.export.assert_called_once()
        markdown_exporter_mock.return_value.export.assert_called_once()

        # Discovery succeeded and Project.observations was populated.
        self.assertEqual(len(captured_projects), 1)
        project = captured_projects[0]
        self.assertEqual(project.network_graph.device_count(), 2)
        self.assertEqual(len(project.observations), 4)

        # Application.run() itself resolved canonical identities — no
        # manual resolver call here; asserting directly on
        # project.canonical_identities is what actually proves the
        # runtime wiring, as opposed to re-testing IdentityResolver's own
        # already-covered unit correctness.
        identities = project.canonical_identities
        self.assertEqual(len(identities), 2)
        self.assertTrue(all(isinstance(identity, CanonicalIdentity) for identity in identities))

        identities_by_subject = {identity.subject: identity for identity in identities}
        self.assertEqual(
            identities_by_subject["172.16.100.10"].state, IdentityCorroborationState.CONFIRMED
        )
        self.assertEqual(
            identities_by_subject["172.16.100.11"].state, IdentityCorroborationState.WEAK
        )

        # Application.run() itself resolved canonical relationships too,
        # in the same run, using the identities resolved above.
        relationships = project.canonical_relationships
        self.assertEqual(len(relationships), 1)
        relationship = relationships[0]
        self.assertIsInstance(relationship, CanonicalRelationship)
        self.assertEqual(relationship.subject, "172.16.100.10")
        self.assertEqual(relationship.category, "connected_to")
        self.assertEqual(relationship.state, RelationshipCorroborationState.WEAK)


if __name__ == "__main__":
    unittest.main()

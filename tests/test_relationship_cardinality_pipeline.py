"""End-to-end relationship cardinality tests (PLAN-028 Section 7.2; ADR-013
Amendment 1).

Each test runs real evidence through the real chain: a stubbed SNMP client →
the real relationship provider → `collect_observations()` (plus nmap-style
identity observations so every endpoint resolves) → `IdentityResolver` →
`RelationshipResolver`. Multi-valued fan-out — a gateway's ARP table, a
switch's forwarding table, a switch's LLDP neighbors — must surface as one
WEAK edge per related subject, never as CONFLICTING.
"""

from __future__ import annotations

import csv
import random
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from networkmapper.core.models import Device
from networkmapper.discovery.arp_neighbor_provider import ARP_NEIGHBOR_CATEGORY, SnmpArpNeighborProvider
from networkmapper.discovery.bridge_fdb_provider import BRIDGE_FDB_CATEGORY, SnmpBridgeFdbProvider
from networkmapper.discovery.lldp_neighbor_provider import LLDP_NEIGHBOR_CATEGORY, SnmpLldpNeighborProvider
from networkmapper.discovery.snmp_client import (
    SnmpArpTableEntry,
    SnmpArpTableResult,
    SnmpBridgeFdbEntry,
    SnmpBridgeFdbResult,
    SnmpClient,
    SnmpLldpNeighborEntry,
    SnmpLldpTableResult,
)
from networkmapper.discovery.snmp_credentials import SnmpCredentials, SnmpVersion
from networkmapper.exporters.markdown_exporter import MarkdownExporter
from networkmapper.exporters.relationship_csv_exporter import RelationshipCsvExporter
from networkmapper.identity.resolver import IdentityResolver
from networkmapper.observations.models import IdentityObservation
from networkmapper.observations.provenance import ObservationProvenance
from networkmapper.project.models import Project
from networkmapper.relationships.categories import RelationshipCardinality
from networkmapper.relationships.models import RelationshipCorroborationState
from networkmapper.relationships.resolver import RelationshipResolver

_CREDENTIALS = SnmpCredentials(version=SnmpVersion.V2C, community="s3cr3t-community")

_GATEWAY = "10.0.0.1"
_SWITCH = "10.0.0.2"
_HOSTS = ("10.0.0.10", "10.0.0.11", "10.0.0.12")
_HOST_MACS = {
    "10.0.0.10": "AA:BB:CC:00:00:10",
    "10.0.0.11": "AA:BB:CC:00:00:11",
    "10.0.0.12": "AA:BB:CC:00:00:12",
}


class _StubSnmpClient(SnmpClient):
    """Returns canned ARP, forwarding-table, and LLDP results per host;
    any host without a canned result times out."""

    def __init__(
        self,
        *,
        arp: dict[str, SnmpArpTableResult] | None = None,
        fdb: dict[str, SnmpBridgeFdbResult] | None = None,
        lldp: dict[str, SnmpLldpTableResult] | None = None,
    ) -> None:
        self._arp = arp or {}
        self._fdb = fdb or {}
        self._lldp = lldp or {}

    def get_arp_table(self, host, credentials, timeout, retries) -> SnmpArpTableResult:
        return self._arp.get(host, SnmpArpTableResult(responded=False, failure_reason="timeout"))

    def get_bridge_fdb(self, host, credentials, timeout, retries) -> SnmpBridgeFdbResult:
        return self._fdb.get(host, SnmpBridgeFdbResult(responded=False, failure_reason="timeout"))

    def get_lldp_neighbors(self, host, credentials, timeout, retries) -> SnmpLldpTableResult:
        return self._lldp.get(host, SnmpLldpTableResult(responded=False, failure_reason="timeout"))


def _nmap_identity_observations(subjects) -> list[IdentityObservation]:
    """One nmap-style MAC identity observation per subject, so every endpoint
    resolves to a canonical identity — the same shape NmapProvider emits."""
    provenance = ObservationProvenance(
        provider="nmap",
        collection_method="host-discovery",
        observed_at=datetime(2026, 10, 8, 9, 0, 0),
        source_run="run-e2e",
    )
    return [
        IdentityObservation(
            subject=subject,
            property_name="mac_address",
            value=_HOST_MACS.get(subject, f"AA:BB:CC:00:FF:{index:02X}"),
            provenance=provenance,
        )
        for index, subject in enumerate(sorted(subjects))
    ]


def _arp_result() -> SnmpArpTableResult:
    return SnmpArpTableResult(
        responded=True,
        entries=[
            SnmpArpTableEntry(
                interface_index=1, ip_address=host, mac_address=_HOST_MACS[host], entry_type="dynamic"
            )
            for host in _HOSTS
        ],
    )


def _fdb_result() -> SnmpBridgeFdbResult:
    return SnmpBridgeFdbResult(
        responded=True,
        entries=[
            SnmpBridgeFdbEntry(mac_address=_HOST_MACS[host], port=port, status="learned")
            for port, host in enumerate(_HOSTS[:2], start=1)
        ],
    )


def _lldp_entry(local_port_num: int, management_addresses: list[str]) -> SnmpLldpNeighborEntry:
    return SnmpLldpNeighborEntry(
        local_port_num=local_port_num,
        rem_index=1,
        chassis_id_subtype=4,
        chassis_id=f"AA:BB:CC:DD:00:{local_port_num:02X}",
        sys_name=None,
        management_addresses=management_addresses,
    )


def _resolve(observations):
    identities = IdentityResolver().resolve(observations)
    return identities, RelationshipResolver().resolve(observations, identities)


def _collect_arp_observations():
    provider = SnmpArpNeighborProvider(_CREDENTIALS, client=_StubSnmpClient(arp={_GATEWAY: _arp_result()}))
    provider.enrich([Device(ip_address=_GATEWAY)])
    return provider.collect_observations()


def _collect_fdb_observations(identity_observations):
    provider = SnmpBridgeFdbProvider(_CREDENTIALS, client=_StubSnmpClient(fdb={_SWITCH: _fdb_result()}))
    provider.receive_observations(tuple(identity_observations))
    provider.enrich([Device(ip_address=_SWITCH)])
    return provider.collect_observations()


def _collect_lldp_observations(lldp_entries):
    provider = SnmpLldpNeighborProvider(
        _CREDENTIALS,
        client=_StubSnmpClient(lldp={_SWITCH: SnmpLldpTableResult(responded=True, entries=lldp_entries)}),
    )
    provider.enrich([Device(ip_address=_SWITCH)])
    return provider.collect_observations()


def _edges_for(relationships, category):
    return [relationship for relationship in relationships if relationship.category == category]


class ArpFanOutPipelineTest(unittest.TestCase):
    def test_gateway_arp_table_fan_out_produces_one_weak_edge_per_host(self):
        observations = _nmap_identity_observations((_GATEWAY,) + _HOSTS) + _collect_arp_observations()

        _, relationships = _resolve(observations)

        edges = _edges_for(relationships, ARP_NEIGHBOR_CATEGORY)
        self.assertEqual([(e.subject, e.related_subject) for e in edges], [(_GATEWAY, host) for host in _HOSTS])
        for edge in edges:
            self.assertEqual(edge.cardinality, RelationshipCardinality.MULTIPLE)
            self.assertEqual(edge.state, RelationshipCorroborationState.WEAK)
        self.assertNotIn(RelationshipCorroborationState.CONFLICTING, {r.state for r in relationships})


class BridgeFdbFanOutPipelineTest(unittest.TestCase):
    def test_switch_forwarding_table_fan_out_produces_one_weak_edge_per_learned_host(self):
        identity_observations = _nmap_identity_observations((_SWITCH,) + _HOSTS)
        observations = identity_observations + _collect_fdb_observations(identity_observations)

        _, relationships = _resolve(observations)

        edges = _edges_for(relationships, BRIDGE_FDB_CATEGORY)
        self.assertEqual([(e.subject, e.related_subject) for e in edges], [(_SWITCH, host) for host in _HOSTS[:2]])
        self.assertTrue(all(e.state == RelationshipCorroborationState.WEAK for e in edges))
        self.assertNotIn(RelationshipCorroborationState.CONFLICTING, {r.state for r in relationships})


class LldpFanOutPipelineTest(unittest.TestCase):
    def test_switch_with_two_lldp_neighbors_produces_two_weak_edges(self):
        lldp = _collect_lldp_observations(
            [_lldp_entry(1, ["10.0.0.10"]), _lldp_entry(2, ["10.0.0.11"])]
        )
        observations = _nmap_identity_observations((_SWITCH,) + _HOSTS) + lldp

        _, relationships = _resolve(observations)

        edges = _edges_for(relationships, LLDP_NEIGHBOR_CATEGORY)
        self.assertEqual([e.related_subject for e in edges], ["10.0.0.10", "10.0.0.11"])
        self.assertTrue(all(e.state == RelationshipCorroborationState.WEAK for e in edges))

    def test_one_neighbor_with_two_management_addresses_produces_two_weak_edges(self):
        # Locks in today's documented behavior (ARCH-027 Open Question 2;
        # PLAN-028 R6): the provider emits one observation per management
        # address, so one neighbor appears as two edges. That is not fixed
        # here — but it must no longer surface as a false CONFLICTING.
        lldp = _collect_lldp_observations([_lldp_entry(1, ["10.0.0.10", "10.0.0.11"])])
        observations = _nmap_identity_observations((_SWITCH,) + _HOSTS) + lldp

        _, relationships = _resolve(observations)

        edges = _edges_for(relationships, LLDP_NEIGHBOR_CATEGORY)
        self.assertEqual([e.related_subject for e in edges], ["10.0.0.10", "10.0.0.11"])
        self.assertTrue(all(e.state == RelationshipCorroborationState.WEAK for e in edges))


def _combined_observations():
    identity_observations = _nmap_identity_observations((_GATEWAY, _SWITCH) + _HOSTS)
    return (
        identity_observations
        + _collect_arp_observations()
        + _collect_fdb_observations(identity_observations)
        + _collect_lldp_observations([_lldp_entry(1, ["10.0.0.10"]), _lldp_entry(2, ["10.0.0.11"])])
    )


class CombinedFanOutExportTest(unittest.TestCase):
    def test_exporters_render_fan_out_without_any_conflict(self):
        identities, relationships = _resolve(_combined_observations())
        project = Project(
            customer_name="Acme",
            created_date=datetime(2026, 10, 8, 9, 0, 0),
            modified_date=datetime(2026, 10, 8, 9, 0, 0),
            canonical_identities=identities,
            canonical_relationships=relationships,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            csv_path = Path(temp_dir) / "relationships.csv"
            markdown_path = Path(temp_dir) / "report.md"
            RelationshipCsvExporter().export(project, str(csv_path))
            MarkdownExporter().export(project, str(markdown_path))
            with open(csv_path, newline="", encoding="utf-8") as csv_file:
                rows = list(csv.reader(csv_file))
            markdown = markdown_path.read_text(encoding="utf-8")

        # 3 ARP + 2 FDB + 2 LLDP edges, one row each.
        self.assertEqual(len(rows) - 1, 7)
        self.assertEqual({row[5] for row in rows[1:]}, {"weak"})
        section = markdown[markdown.index("# Canonical Relationships") :]
        self.assertNotIn("Conflicting", section)
        self.assertIn("- Cardinality: Multi-valued", section)

    def test_mixed_evidence_resolves_identically_across_shuffles(self):
        observations = _combined_observations()
        baseline = _resolve(observations)[1]

        rng = random.Random(2028)
        for _ in range(50):
            shuffled = list(observations)
            rng.shuffle(shuffled)
            self.assertEqual(_resolve(shuffled)[1], baseline)


if __name__ == "__main__":
    unittest.main()

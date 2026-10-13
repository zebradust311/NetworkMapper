"""Observation replay exporter tests (ADR-011 Amendment 1; PLAN-029
Section 9.2).

All values are synthetic: documentation address ranges and invented MACs
and hostnames only (ARCH-028 Section 8).
"""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from networkmapper.core.models import Device
from networkmapper.discovery.arp_neighbor_provider import SnmpArpNeighborProvider
from networkmapper.discovery.bridge_fdb_provider import SnmpBridgeFdbProvider
from networkmapper.discovery.lldp_neighbor_provider import SnmpLldpNeighborProvider
from networkmapper.discovery.snmp_client import (
    SnmpArpTableEntry,
    SnmpArpTableResult,
    SnmpBridgeFdbEntry,
    SnmpBridgeFdbResult,
    SnmpClient,
    SnmpHostResult,
    SnmpLldpNeighborEntry,
    SnmpLldpTableResult,
)
from networkmapper.discovery.snmp_credentials import SnmpCredentials, SnmpVersion
from networkmapper.discovery.snmp_provider import SnmpEnrichmentProvider
from networkmapper.exporters.observation_json_exporter import ObservationJsonExporter
from networkmapper.identity.resolver import IdentityResolver
from networkmapper.observations.models import IdentityObservation, RelationshipObservation
from networkmapper.observations.provenance import ObservationProvenance
from networkmapper.observations.replay_format import serialize_observations
from networkmapper.project.models import Project
from networkmapper.project.serializer import ProjectSerializer
from networkmapper.relationships.resolver import RelationshipResolver

_SENTINEL_COMMUNITY = "SENTINEL-c0mmunity-7f3a91"

_GATEWAY = "192.0.2.1"
_SWITCH = "192.0.2.2"
_HOSTS = ("192.0.2.10", "192.0.2.11")
_MACS = {
    _GATEWAY: "02:00:5E:00:53:01",
    _SWITCH: "02:00:5E:00:53:02",
    "192.0.2.10": "02:00:5E:00:53:0A",
    "192.0.2.11": "02:00:5E:00:53:0B",
}


class _StubSnmpClient(SnmpClient):
    """Answers every SNMP query for the gateway and the switch with canned
    synthetic results; any other host times out."""

    def get_system_group(self, host, credentials, timeout, retries) -> SnmpHostResult:
        if host in (_GATEWAY, _SWITCH):
            return SnmpHostResult(responded=True, fields={"sysName": f"device-{host.rsplit('.', 1)[1]}.example"})
        return SnmpHostResult(responded=False, failure_reason="timeout")

    def get_arp_table(self, host, credentials, timeout, retries) -> SnmpArpTableResult:
        if host != _GATEWAY:
            return SnmpArpTableResult(responded=False, failure_reason="timeout")
        return SnmpArpTableResult(
            responded=True,
            entries=[
                SnmpArpTableEntry(
                    interface_index=1, ip_address=address, mac_address=_MACS[address], entry_type="dynamic"
                )
                for address in _HOSTS
            ],
        )

    def get_bridge_fdb(self, host, credentials, timeout, retries) -> SnmpBridgeFdbResult:
        if host != _SWITCH:
            return SnmpBridgeFdbResult(responded=False, failure_reason="timeout")
        return SnmpBridgeFdbResult(
            responded=True,
            entries=[
                SnmpBridgeFdbEntry(mac_address=_MACS[address], port=port, status="learned")
                for port, address in enumerate(_HOSTS, start=1)
            ],
        )

    def get_lldp_neighbors(self, host, credentials, timeout, retries) -> SnmpLldpTableResult:
        if host != _SWITCH:
            return SnmpLldpTableResult(responded=False, failure_reason="timeout")
        return SnmpLldpTableResult(
            responded=True,
            entries=[
                SnmpLldpNeighborEntry(
                    local_port_num=1,
                    rem_index=1,
                    chassis_id_subtype=4,
                    chassis_id=_MACS[_GATEWAY],
                    sys_name="device-1.example",
                    # 198.51.100.77 is never discovered: an unresolved endpoint.
                    management_addresses=[_GATEWAY, "198.51.100.77"],
                )
            ],
        )


def _nmap_identity_observations() -> list[IdentityObservation]:
    provenance = ObservationProvenance(
        provider="nmap",
        collection_method="host-discovery",
        observed_at=datetime(2026, 10, 13, 9, 0, 0, 250000),
        source_run="run-nmap",
    )
    return [
        IdentityObservation(subject=subject, property_name="mac_address", value=mac, provenance=provenance)
        for subject, mac in sorted(_MACS.items())
    ]


def _collect_all_provider_observations(community: str = _SENTINEL_COMMUNITY):
    """Drive all four real SNMP providers, with one shared credential,
    through a stub client, the way `DiscoveryEngine` does."""
    credentials = SnmpCredentials(version=SnmpVersion.V2C, community=community)
    devices = [Device(ip_address=address) for address in sorted(_MACS)]
    observations: list[IdentityObservation | RelationshipObservation] = list(_nmap_identity_observations())

    for provider_class in (
        SnmpEnrichmentProvider,
        SnmpArpNeighborProvider,
        SnmpLldpNeighborProvider,
        SnmpBridgeFdbProvider,
    ):
        provider = provider_class(credentials, client=_StubSnmpClient())
        provider.receive_observations(tuple(observations))
        provider.enrich(devices)
        observations.extend(provider.collect_observations())

    return observations


def _project(observations) -> Project:
    identities = IdentityResolver().resolve(observations)
    project = Project(
        customer_name="Synthetic Example",
        created_date=datetime(2026, 10, 13, 8, 0, 0),
        modified_date=datetime(2026, 10, 13, 8, 30, 0),
        observations=list(observations),
        canonical_identities=identities,
        canonical_relationships=RelationshipResolver().resolve(observations, identities),
    )
    for address in sorted(_MACS):
        project.network_graph.add_device(Device(ip_address=address, hostname=f"host-{address}", vendor="Example"))
    return project


def _export(project: Project) -> bytes:
    with tempfile.TemporaryDirectory() as temp_dir:
        path = Path(temp_dir) / "observations.json"
        ObservationJsonExporter().export(project, str(path))
        return path.read_bytes()


class ObservationJsonExporterTest(unittest.TestCase):
    def test_export_writes_exactly_the_serialized_observations(self):
        project = _project(_collect_all_provider_observations())

        payload = _export(project)

        self.assertEqual(payload, serialize_observations(project.observations))
        self.assertEqual(len(json.loads(payload)["observations"]), len(project.observations))

    def test_export_covers_identity_and_relationship_observations_from_every_provider(self):
        project = _project(_collect_all_provider_observations())

        records = json.loads(_export(project))["observations"]

        self.assertEqual({record["type"] for record in records}, {"identity", "relationship"})
        self.assertEqual(
            {record["category"] for record in records if record["type"] == "relationship"},
            {"arp_neighbor", "bridge_fdb", "connected_to"},
        )
        self.assertIn(
            ("snmp", "sysName"),
            {(record["provenance"]["provider"], record["provenance"]["collection_method"]) for record in records},
        )

    def test_export_of_a_project_without_observations_is_a_valid_empty_artifact(self):
        payload = _export(Project(customer_name="Synthetic Example"))

        self.assertEqual(payload, serialize_observations([]))
        self.assertEqual(json.loads(payload)["observations"], [])

    def test_export_overwrites_an_existing_file(self):
        # Written once per application run with plain overwrite, like the
        # other report artifacts (PLAN-029 D9).
        project = _project(_collect_all_provider_observations())

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "observations.json"
            path.write_bytes(b"stale content that is much longer than nothing" * 1000)
            ObservationJsonExporter().export(project, str(path))
            payload = path.read_bytes()

        self.assertEqual(payload, serialize_observations(project.observations))

    def test_export_is_read_only(self):
        project = _project(_collect_all_provider_observations())
        observation_objects = list(project.observations)
        identities = project.canonical_identities
        relationships = project.canonical_relationships
        devices = [(device.ip_address, device.hostname) for device in project.network_graph.all_devices()]
        modified_date = project.modified_date

        _export(project)

        self.assertEqual(len(project.observations), len(observation_objects))
        for original, current in zip(observation_objects, project.observations):
            self.assertIs(current, original)
        self.assertIs(project.canonical_identities, identities)
        self.assertIs(project.canonical_relationships, relationships)
        self.assertEqual(
            [(device.ip_address, device.hostname) for device in project.network_graph.all_devices()], devices
        )
        self.assertEqual(project.modified_date, modified_date)

    def test_export_contains_observations_only(self):
        project = _project(_collect_all_provider_observations())
        self.assertTrue(project.canonical_identities)
        self.assertTrue(project.canonical_relationships)

        payload = _export(project)
        text = payload.decode("ascii")

        self.assertEqual(sorted(json.loads(payload)), ["format", "format_version", "observations"])
        for absent in (
            "canonical",
            "devices",
            "customer_name",
            "Synthetic Example",
            "created_date",
            "generated_at",
            "scan_profile",
            "weak",
            "confirmed",
            "conflicting",
            "cardinality",
            "host-192.0.2.10",
        ):
            self.assertNotIn(absent, text)

    def test_credentials_never_appear_in_the_artifact(self):
        observations = _collect_all_provider_observations(_SENTINEL_COMMUNITY)
        # The providers really ran and really produced SNMP evidence.
        self.assertTrue(any(observation.provenance.provider == "snmp" for observation in observations))
        self.assertTrue(any(isinstance(observation, RelationshipObservation) for observation in observations))

        payload = _export(_project(observations))

        self.assertNotIn(_SENTINEL_COMMUNITY.encode("ascii"), payload)
        self.assertNotIn(_SENTINEL_COMMUNITY.lower().encode("ascii"), payload.lower())
        self.assertNotIn(b"community", payload.lower())
        self.assertNotIn(b"***", payload)

    def test_project_serializer_output_is_unaffected_by_observations(self):
        observations = _collect_all_provider_observations()
        with_observations = _project(observations)
        without_observations = _project(observations)
        without_observations.observations = []
        without_observations.canonical_identities = ()
        without_observations.canonical_relationships = ()

        with tempfile.TemporaryDirectory() as temp_dir:
            with_path = Path(temp_dir) / "with.nmproj"
            without_path = Path(temp_dir) / "without.nmproj"
            ProjectSerializer.save(with_observations, str(with_path))
            ProjectSerializer.save(without_observations, str(without_path))
            with_bytes = with_path.read_bytes()
            without_bytes = without_path.read_bytes()

        self.assertEqual(with_bytes, without_bytes)
        self.assertNotIn(b"observations", with_bytes)


if __name__ == "__main__":
    unittest.main()

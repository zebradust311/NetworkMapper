import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from networkmapper.core.models import Device, DeviceType, ServiceEvidence
from networkmapper.discovery.scan_profile import ScanProfile
from networkmapper.knowledge.capture import (
    build_observation,
    capture_unresolved_device,
    should_capture,
)
from networkmapper.knowledge.repository import ObservationRepository
from networkmapper.reporting.report_run import RunMetadata


def _run_metadata() -> RunMetadata:
    return RunMetadata(
        generated_at=datetime(2026, 7, 18, 9, 42, 11),
        scan_profile=ScanProfile.STANDARD,
        customer_name="Riverside Manufacturing",
        device_count=1,
        version="0.4.0",
    )


class ShouldCaptureTest(unittest.TestCase):
    def test_unknown_device_should_be_captured(self):
        device = Device(ip_address="192.168.10.55", device_type=DeviceType.UNKNOWN)

        self.assertTrue(should_capture(device))

    def test_classified_device_should_not_be_captured(self):
        device = Device(ip_address="192.168.10.10", device_type=DeviceType.SERVER)

        self.assertFalse(should_capture(device))


class BuildObservationTest(unittest.TestCase):
    def test_unknown_device_produces_no_rule_matched_reason(self):
        device = Device(
            ip_address="192.168.10.55",
            hostname="AP9631",
            vendor="APC",
            mac_address="00:C0:B7:4E:19:2A",
            discovery_sources=["nmap"],
            services=[
                ServiceEvidence(
                    port=80,
                    protocol="tcp",
                    service="http",
                    http_title="APC Network Management Card AOS v6.9.6",
                ),
            ],
            device_type=DeviceType.UNKNOWN,
        )

        observation = build_observation(
            device, observation_id=1, run_metadata=_run_metadata()
        )

        self.assertEqual(observation.classification.type, "unknown")
        self.assertEqual(observation.classification.reason, "No rule matched.")
        self.assertIsNone(observation.classification.matched_rule)

    def test_evidence_and_identity_are_mapped_from_the_canonical_device(self):
        device = Device(
            ip_address="192.168.10.55",
            hostname="AP9631",
            vendor="APC",
            mac_address="00:C0:B7:4E:19:2A",
            discovery_sources=["nmap"],
            services=[ServiceEvidence(port=443, protocol="tcp", tls_subject="CN=AP9631")],
            device_type=DeviceType.UNKNOWN,
        )

        observation = build_observation(
            device, observation_id=7, run_metadata=_run_metadata()
        )

        self.assertEqual(observation.observation_id, 7)
        self.assertEqual(observation.network.name, "Riverside Manufacturing")
        self.assertEqual(observation.scan.profile, "standard")
        self.assertEqual(observation.scan.networkmapper_version, "0.4.0")
        self.assertEqual(observation.device.ip, "192.168.10.55")
        self.assertEqual(observation.device.hostname, "AP9631")
        self.assertEqual(observation.device.vendor, "APC")
        self.assertEqual(observation.device.mac_address, "00:C0:B7:4E:19:2A")
        self.assertEqual(observation.evidence.discovery_sources, ["nmap"])
        self.assertEqual(observation.evidence.services[0].tls_subject, "CN=AP9631")

    def test_matched_device_records_matching_rule_and_reason(self):
        """Uses the same fixture as
        tests.test_network_appliance_rule.NetworkApplianceRuleTest — a
        device that NetworkApplianceRule actually classifies today — to
        confirm capture reports a real match rather than always defaulting
        to "No rule matched.\""""
        device = Device(
            ip_address="172.16.100.20",
            vendor=None,
            hostname=None,
            services=[
                ServiceEvidence(port=80, protocol="tcp", http_auth_realm="NETGEAR ReadyNAS"),
            ],
            device_type=DeviceType.SERVER,
        )

        observation = build_observation(
            device, observation_id=2, run_metadata=_run_metadata()
        )

        self.assertEqual(observation.classification.type, "server")
        self.assertEqual(observation.classification.matched_rule, "NetworkApplianceRule")
        self.assertIn("ReadyNAS", observation.classification.reason)

    def test_does_not_mutate_the_original_device(self):
        """ADR-005: presentation/reporting consumers classify a copy, never
        the original device."""
        device = Device(
            ip_address="172.16.100.20",
            services=[
                ServiceEvidence(port=80, protocol="tcp", http_auth_realm="NETGEAR ReadyNAS"),
            ],
            device_type=DeviceType.UNKNOWN,
        )

        build_observation(device, observation_id=1, run_metadata=_run_metadata())

        self.assertEqual(device.device_type, DeviceType.UNKNOWN)


class CaptureUnresolvedDeviceTest(unittest.TestCase):
    def setUp(self):
        self._temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._temp_dir.cleanup)
        self.repository = ObservationRepository(root=Path(self._temp_dir.name) / "observations")

    def test_captures_and_persists_an_unknown_device(self):
        device = Device(
            ip_address="192.168.10.55",
            vendor="APC",
            device_type=DeviceType.UNKNOWN,
        )

        observation = capture_unresolved_device(device, _run_metadata(), self.repository)

        self.assertIsNotNone(observation)
        self.assertEqual(self.repository.list_observation_ids(), (1,))

    def test_returns_none_and_writes_nothing_for_a_classified_device(self):
        device = Device(
            ip_address="192.168.10.10",
            device_type=DeviceType.SERVER,
        )

        observation = capture_unresolved_device(device, _run_metadata(), self.repository)

        self.assertIsNone(observation)
        self.assertEqual(self.repository.list_observation_ids(), ())

    def test_successive_captures_get_sequential_ids(self):
        first = capture_unresolved_device(
            Device(ip_address="10.0.0.1", device_type=DeviceType.UNKNOWN),
            _run_metadata(),
            self.repository,
        )
        second = capture_unresolved_device(
            Device(ip_address="10.0.0.2", device_type=DeviceType.UNKNOWN),
            _run_metadata(),
            self.repository,
        )

        self.assertEqual(first.observation_id, 1)
        self.assertEqual(second.observation_id, 2)


if __name__ == "__main__":
    unittest.main()

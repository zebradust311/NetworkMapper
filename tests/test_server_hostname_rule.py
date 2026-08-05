import unittest

from networkmapper.classification.rule_result import RuleResult
from networkmapper.classification.rules.server_hostname_rule import ServerHostnameRule
from networkmapper.core.models import Device, DeviceType


class ServerHostnameRuleTest(unittest.TestCase):
    def test_dc_hostname_returns_matching_rule_result(self):
        device = Device(
            ip_address="192.168.1.50",
            hostname="DC01",
            vendor="Unknown",
        )

        result = ServerHostnameRule().classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertTrue(result.matched)
        self.assertEqual(result.suggested_device_type, DeviceType.SERVER)
        self.assertEqual(
            result.reason,
            "Hostname 'DC01' matched known server naming convention.",
        )

    def test_cam_hostname_returns_matching_rule_result(self):
        device = Device(
            ip_address="192.168.1.51",
            hostname="CAM-01",
            vendor="Unknown",
        )

        result = ServerHostnameRule().classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertTrue(result.matched)
        self.assertEqual(result.suggested_device_type, DeviceType.SERVER)
        self.assertEqual(
            result.reason,
            "Hostname 'CAM-01' matched known server naming convention.",
        )

    def test_non_matching_hostname_returns_non_matching_rule_result(self):
        device = Device(
            ip_address="192.168.1.52",
            hostname="host-01",
            vendor="Unknown",
        )

        result = ServerHostnameRule().classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertFalse(result.matched)
        self.assertIsNone(result.suggested_device_type)
        self.assertEqual(result.confidence_contribution, 0)
        self.assertEqual(
            result.reason,
            "Hostname 'host-01' did not match known server naming patterns.",
        )

    def test_srv_hostname_returns_matching_rule_result(self):
        device = Device(
            ip_address="192.168.1.53",
            hostname="SRV-APP01",
            vendor="Unknown",
        )

        result = ServerHostnameRule().classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertTrue(result.matched)
        self.assertEqual(result.suggested_device_type, DeviceType.SERVER)
        self.assertEqual(
            result.reason,
            "Hostname 'SRV-APP01' matched known server naming pattern.",
        )

    def test_hostname_match_with_windows_server_os_corroborates_reason(self):
        device = Device(
            ip_address="192.168.1.54",
            hostname="SRV-APP02",
            vendor="Unknown",
            operating_system="Windows Server 2019 Standard 17763",
        )

        result = ServerHostnameRule().classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertTrue(result.matched)
        self.assertEqual(result.suggested_device_type, DeviceType.SERVER)
        self.assertEqual(
            result.reason,
            "Hostname 'SRV-APP02' matched known server naming pattern. Detected "
            "operating system 'Windows Server 2019 Standard 17763' corroborates "
            "known server evidence.",
        )

    def test_windows_server_os_alone_does_not_independently_trigger_a_match(self):
        """A non-matching hostname must not become SERVER on OS evidence alone —
        Hyper-V hosts, domain controllers, and other infrastructure also run
        Windows Server, so this rule (which runs first in DeviceClassifier's
        ordering) must not preempt more specific rules like
        HypervisorHostnameRule. See server_hostname_rule.py's
        SERVER_OPERATING_SYSTEM_KEYWORDS comment for the benchmark regression
        this originally caused."""
        device = Device(
            ip_address="192.168.1.55",
            hostname="hyperv-node-02",
            vendor="Unknown",
            operating_system="Windows Server 2016 Standard 14393",
        )

        result = ServerHostnameRule().classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertFalse(result.matched)
        self.assertIsNone(result.suggested_device_type)
        self.assertEqual(
            result.reason,
            "Hostname 'hyperv-node-02' did not match known server naming patterns.",
        )


if __name__ == "__main__":
    unittest.main()
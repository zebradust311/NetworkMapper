import unittest

from networkmapper.classification.rule_result import RuleResult
from networkmapper.classification.rules.ubiquiti_access_point_rule import UbiquitiAccessPointRule
from networkmapper.core.models import Device, DeviceType, ServiceEvidence


class UbiquitiAccessPointRuleTest(unittest.TestCase):
    def test_uap_hostname_classifies_as_access_point(self):
        device = Device(
            ip_address="192.168.1.20",
            hostname="UAP-AC-LR",
            vendor="Ubiquiti",
        )

        result = UbiquitiAccessPointRule().classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertTrue(result.matched)
        self.assertEqual(result.suggested_device_type, DeviceType.ACCESS_POINT)
        self.assertEqual(
            result.reason,
            "Vendor 'Ubiquiti' and hostname 'UAP-AC-LR' matched known wireless infrastructure vendor.",
        )

    def test_u6_hostname_classifies_as_access_point(self):
        device = Device(
            ip_address="192.168.1.21",
            hostname="U6-Pro",
            vendor="Ubiquiti",
        )

        result = UbiquitiAccessPointRule().classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertTrue(result.matched)
        self.assertEqual(result.suggested_device_type, DeviceType.ACCESS_POINT)
        self.assertEqual(
            result.reason,
            "Vendor 'Ubiquiti' and hostname 'U6-Pro' matched known wireless infrastructure vendor.",
        )

    def test_u7_hostname_classifies_as_access_point(self):
        device = Device(
            ip_address="192.168.1.22",
            hostname="U7-Pro",
            vendor="Ubiquiti",
        )

        result = UbiquitiAccessPointRule().classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertTrue(result.matched)
        self.assertEqual(result.suggested_device_type, DeviceType.ACCESS_POINT)
        self.assertEqual(
            result.reason,
            "Vendor 'Ubiquiti' and hostname 'U7-Pro' matched known wireless infrastructure vendor.",
        )

    def test_other_ubiquiti_devices_remain_unaffected(self):
        device = Device(
            ip_address="192.168.1.23",
            hostname="Switch-01",
            vendor="Ubiquiti",
        )

        result = UbiquitiAccessPointRule().classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertFalse(result.matched)
        self.assertIsNone(result.suggested_device_type)
        self.assertEqual(result.confidence_contribution, 0)
        self.assertEqual(
            result.reason,
            "Vendor 'Ubiquiti' and hostname 'Switch-01' did not match known wireless infrastructure vendor patterns.",
        )

    def test_non_ubiquiti_devices_are_ignored(self):
        device = Device(
            ip_address="192.168.1.24",
            hostname="UAP-AC-LR",
            vendor="Cisco",
        )

        result = UbiquitiAccessPointRule().classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertFalse(result.matched)
        self.assertIsNone(result.suggested_device_type)
        self.assertEqual(result.confidence_contribution, 0)
        self.assertEqual(
            result.reason,
            "Vendor 'Cisco' and hostname 'UAP-AC-LR' did not match known wireless infrastructure vendor patterns.",
        )

    def test_nanohd_hostname_classifies_as_access_point(self):
        device = Device(
            ip_address="192.168.1.25",
            hostname="office-nanohd-01",
            vendor="Ubiquiti",
        )

        result = UbiquitiAccessPointRule().classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertTrue(result.matched)
        self.assertEqual(result.suggested_device_type, DeviceType.ACCESS_POINT)
        self.assertEqual(
            result.reason,
            "Vendor 'Ubiquiti' and hostname 'office-nanohd-01' matched known wireless access point naming patterns.",
        )

    def test_guest_portal_redirect_classifies_as_access_point_with_no_hostname(self):
        """RULE-005: reproduces real production evidence exactly -- these
        access points report no hostname at all."""
        device = Device(
            ip_address="172.16.100.116",
            hostname=None,
            vendor="Ubiquiti",
            services=[
                ServiceEvidence(
                    port=80,
                    protocol="tcp",
                    http_title=(
                        "Did not follow redirect to "
                        "http://172.16.100.89:8880/guest/s/default/?ap=0c:ea:14:b7:41:9d"
                        "&ec=4i5lQ9ecDwcp-LCkH1697alvguXoqmWg3DshpMadGs7OTsAnAWcJPf0sYnKy8ojRBcJi"
                    ),
                ),
            ],
        )

        result = UbiquitiAccessPointRule().classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertTrue(result.matched)
        self.assertEqual(result.suggested_device_type, DeviceType.ACCESS_POINT)
        self.assertIn("guest-portal", result.reason)

    def test_guest_portal_redirect_is_also_recognized_when_a_hostname_is_present(self):
        device = Device(
            ip_address="172.16.100.117",
            hostname="some-generic-host",
            vendor="Ubiquiti",
            services=[
                ServiceEvidence(
                    port=80,
                    protocol="tcp",
                    http_title="Did not follow redirect to http://172.16.100.89:8880/guest/s/default/?ap=aa:bb:cc:dd:ee:ff",
                ),
            ],
        )

        result = UbiquitiAccessPointRule().classify(device)

        self.assertTrue(result.matched)
        self.assertEqual(result.suggested_device_type, DeviceType.ACCESS_POINT)

    def test_non_ubiquiti_vendor_with_guest_portal_title_is_ignored(self):
        device = Device(
            ip_address="172.16.100.118",
            hostname=None,
            vendor="Cisco",
            services=[
                ServiceEvidence(
                    port=80,
                    protocol="tcp",
                    http_title="Did not follow redirect to http://172.16.100.89:8880/guest/s/default/?ap=aa:bb:cc:dd:ee:ff",
                ),
            ],
        )

        result = UbiquitiAccessPointRule().classify(device)

        self.assertFalse(result.matched)
        self.assertIsNone(result.suggested_device_type)

    def test_ubiquiti_vendor_with_no_hostname_and_no_guest_portal_evidence_remains_unmatched(self):
        device = Device(
            ip_address="172.16.100.119",
            hostname=None,
            vendor="Ubiquiti",
            services=[
                ServiceEvidence(port=22, protocol="tcp", service="ssh"),
                ServiceEvidence(port=443, protocol="tcp", http_title="Did not follow redirect to https://172.16.100.119/"),
            ],
        )

        result = UbiquitiAccessPointRule().classify(device)

        self.assertFalse(result.matched)
        self.assertIsNone(result.suggested_device_type)
        self.assertEqual(
            result.reason,
            "Vendor 'Ubiquiti' and hostname None did not match known wireless "
            "infrastructure vendor patterns.",
        )


if __name__ == "__main__":
    unittest.main()

import unittest

from networkmapper.classification.rule_result import RuleResult
from networkmapper.classification.rules.hypervisor_hostname_rule import HypervisorHostnameRule
from networkmapper.core.models import Device, DeviceType, ServiceEvidence


class HypervisorHostnameRuleTest(unittest.TestCase):
    def test_vsh_hostname_returns_matching_rule_result(self):
        device = Device(
            ip_address="192.168.1.60",
            hostname="SCTVSH01",
            vendor="Unknown",
        )

        result = HypervisorHostnameRule().classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertTrue(result.matched)
        self.assertEqual(result.suggested_device_type, DeviceType.HYPERVISOR)
        self.assertEqual(
            result.reason,
            "Hostname 'SCTVSH01' matched known hypervisor naming convention.",
        )

    def test_case_insensitive_hostname_matching(self):
        device = Device(
            ip_address="192.168.1.61",
            hostname="node-VsH-01",
            vendor="Unknown",
        )

        result = HypervisorHostnameRule().classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertTrue(result.matched)
        self.assertEqual(result.suggested_device_type, DeviceType.HYPERVISOR)
        self.assertEqual(
            result.reason,
            "Hostname 'node-VsH-01' matched known hypervisor naming convention.",
        )

    def test_non_matching_hostname_returns_non_matching_rule_result(self):
        device = Device(
            ip_address="192.168.1.62",
            hostname="host-01",
            vendor="Unknown",
        )

        result = HypervisorHostnameRule().classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertFalse(result.matched)
        self.assertIsNone(result.suggested_device_type)
        self.assertEqual(result.confidence_contribution, 0)
        self.assertEqual(
            result.reason,
            "Hostname 'host-01' did not match known hypervisor naming conventions.",
        )

    def test_esxi_hostname_matches_hypervisor_pattern(self):
        device = Device(
            ip_address="192.168.1.63",
            hostname="ESXI-01",
            vendor="Unknown",
        )

        result = HypervisorHostnameRule().classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertTrue(result.matched)
        self.assertEqual(result.suggested_device_type, DeviceType.HYPERVISOR)
        self.assertEqual(
            result.reason,
            "Hostname 'ESXI-01' matched known hypervisor naming convention.",
        )

    def test_esx_hostname_matches_legacy_vmware_pattern(self):
        device = Device(
            ip_address="192.168.1.64",
            hostname="esx-01",
            vendor="Unknown",
        )

        result = HypervisorHostnameRule().classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertTrue(result.matched)
        self.assertEqual(result.suggested_device_type, DeviceType.HYPERVISOR)
        self.assertEqual(
            result.reason,
            "Hostname 'esx-01' matched known hypervisor naming convention.",
        )

    def test_hyperv_hostname_matches_microsoft_pattern(self):
        device = Device(
            ip_address="192.168.1.65",
            hostname="hyperv-node-01",
            vendor="Unknown",
        )

        result = HypervisorHostnameRule().classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertTrue(result.matched)
        self.assertEqual(result.suggested_device_type, DeviceType.HYPERVISOR)
        self.assertEqual(
            result.reason,
            "Hostname 'hyperv-node-01' matched known hypervisor naming convention.",
        )

    def test_vcenter_hostname_matches_management_appliance_pattern(self):
        device = Device(
            ip_address="192.168.1.66",
            hostname="vcenter-01",
            vendor="Unknown",
        )

        result = HypervisorHostnameRule().classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertTrue(result.matched)
        self.assertEqual(result.suggested_device_type, DeviceType.HYPERVISOR)
        self.assertEqual(
            result.reason,
            "Hostname 'vcenter-01' matched known hypervisor naming convention.",
        )

    def test_vmhost_hostname_matches_generic_administrator_pattern(self):
        device = Device(
            ip_address="192.168.1.67",
            hostname="vmhost-01",
            vendor="Unknown",
        )

        result = HypervisorHostnameRule().classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertTrue(result.matched)
        self.assertEqual(result.suggested_device_type, DeviceType.HYPERVISOR)
        self.assertEqual(
            result.reason,
            "Hostname 'vmhost-01' matched known hypervisor naming convention.",
        )

    def test_generic_vm_hostname_without_specific_keyword_does_not_match(self):
        device = Device(
            ip_address="192.168.1.68",
            hostname="vm-01",
            vendor="Unknown",
        )

        result = HypervisorHostnameRule().classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertFalse(result.matched)
        self.assertIsNone(result.suggested_device_type)
        self.assertEqual(
            result.reason,
            "Hostname 'vm-01' did not match known hypervisor naming conventions.",
        )

    def test_hostname_match_with_corroborating_port_enriches_reason(self):
        device = Device(
            ip_address="192.168.1.69",
            hostname="esxi-02",
            vendor="Unknown",
            services=[ServiceEvidence(port=443, protocol="tcp")],
        )

        result = HypervisorHostnameRule().classify(device)

        self.assertTrue(result.matched)
        self.assertEqual(result.suggested_device_type, DeviceType.HYPERVISOR)
        self.assertEqual(
            result.reason,
            "Hostname 'esxi-02' with open port 443 matched known hypervisor evidence.",
        )

    def test_hostname_match_with_corroborating_service_enriches_reason(self):
        device = Device(
            ip_address="192.168.1.70",
            hostname="vcenter-02",
            vendor="Unknown",
            services=[ServiceEvidence(port=8443, protocol="tcp", service="https")],
        )

        result = HypervisorHostnameRule().classify(device)

        self.assertTrue(result.matched)
        self.assertEqual(result.suggested_device_type, DeviceType.HYPERVISOR)
        self.assertEqual(
            result.reason,
            "Hostname 'vcenter-02' with service 'https' matched known hypervisor evidence.",
        )

    def test_hostname_match_with_port_and_service_enriches_reason(self):
        device = Device(
            ip_address="192.168.1.71",
            hostname="hyperv-02",
            vendor="Unknown",
            services=[ServiceEvidence(port=3389, protocol="tcp", service="ms-wbt-server")],
        )

        result = HypervisorHostnameRule().classify(device)

        self.assertTrue(result.matched)
        self.assertEqual(result.suggested_device_type, DeviceType.HYPERVISOR)
        self.assertEqual(
            result.reason,
            "Hostname 'hyperv-02' with open port 3389 and service 'ms-wbt-server' "
            "matched known hypervisor evidence.",
        )

    def test_hostname_match_with_vmware_product_enriches_reason(self):
        device = Device(
            ip_address="192.168.1.72",
            hostname="esxi-03",
            vendor="Unknown",
            services=[
                ServiceEvidence(
                    port=443,
                    protocol="tcp",
                    service="https",
                    product="VMware ESXi Server httpd",
                ),
            ],
        )

        result = HypervisorHostnameRule().classify(device)

        self.assertTrue(result.matched)
        self.assertEqual(result.suggested_device_type, DeviceType.HYPERVISOR)
        self.assertEqual(
            result.reason,
            "Hostname 'esxi-03' with open port 443 and service 'https' "
            "matched known hypervisor evidence. Detected service product "
            "'VMware ESXi Server httpd' matched known hypervisor product identifier.",
        )

    def test_hostname_match_with_vmware_product_and_no_port_or_service_signal(self):
        device = Device(
            ip_address="192.168.1.73",
            hostname="esxi-04",
            vendor="Unknown",
            services=[
                ServiceEvidence(port=8443, protocol="tcp", product="VMware vCenter Server"),
            ],
        )

        result = HypervisorHostnameRule().classify(device)

        self.assertTrue(result.matched)
        self.assertEqual(result.suggested_device_type, DeviceType.HYPERVISOR)
        self.assertEqual(
            result.reason,
            "Hostname 'esxi-04' matched known hypervisor naming convention. "
            "Detected service product 'VMware vCenter Server' matched known "
            "hypervisor product identifier.",
        )

    def test_hostname_match_without_vmware_product_is_unaffected(self):
        device = Device(
            ip_address="192.168.1.74",
            hostname="esxi-05",
            vendor="Unknown",
            services=[
                ServiceEvidence(port=443, protocol="tcp", service="https", product="nginx"),
            ],
        )

        result = HypervisorHostnameRule().classify(device)

        self.assertTrue(result.matched)
        self.assertEqual(
            result.reason,
            "Hostname 'esxi-05' with open port 443 and service 'https' "
            "matched known hypervisor evidence.",
        )


if __name__ == "__main__":
    unittest.main()
import unittest

from networkmapper.classification.classifier import DeviceClassifier
from networkmapper.classification.evidence_helpers import (
    first_containing,
    first_matching_identifier,
    first_matching_port,
    first_matching_product,
    first_matching_service,
    format_hostname_evidence_reason,
    normalize_hostname,
    normalize_vendor,
)
from networkmapper.core.models import Device, DeviceType, ServiceEvidence


class DeviceClassifierTest(unittest.TestCase):
    def test_hostname_rules_take_precedence_over_vendor_rules(self):
        device = Device(
            ip_address="192.168.1.10",
            hostname="DC-01",
            vendor="Cisco",
        )

        result = DeviceClassifier().classify(device)

        self.assertEqual(result.device_type, DeviceType.SERVER)

    def test_unknown_device_stays_unknown(self):
        device = Device(
            ip_address="192.168.1.99",
            hostname="host-01",
            vendor="Unknown Vendor",
        )

        result = DeviceClassifier().classify(device)

        self.assertEqual(result.device_type, DeviceType.UNKNOWN)

    def test_first_matching_rule_wins(self):
        device = Device(
            ip_address="192.168.1.50",
            hostname="CAM-01",
            vendor="Brother",
        )

        result = DeviceClassifier().classify(device)

        self.assertEqual(result.device_type, DeviceType.SERVER)

    def test_ubiquiti_access_point_rule_is_executed_in_classifier(self):
        device = Device(
            ip_address="192.168.1.60",
            hostname="UAP-AC-LR",
            vendor="Ubiquiti",
        )

        result = DeviceClassifier().classify(device)

        self.assertEqual(result.device_type, DeviceType.ACCESS_POINT)

    def test_sonicwall_firewall_rule_is_executed_in_classifier(self):
        device = Device(
            ip_address="192.168.1.61",
            hostname="fw-01",
            vendor="SonicWall",
        )

        result = DeviceClassifier().classify(device)

        self.assertEqual(result.device_type, DeviceType.FIREWALL)

    def test_voice_vendor_rule_is_executed_in_classifier(self):
        device = Device(
            ip_address="192.168.1.62",
            hostname="phone-01",
            vendor="Yealink",
        )

        result = DeviceClassifier().classify(device)

        self.assertEqual(result.device_type, DeviceType.PHONE)


class EvidenceHelpersTest(unittest.TestCase):
    def test_normalize_vendor_strip_defaults_to_true(self):
        self.assertEqual(normalize_vendor("  Cisco  "), "cisco")

    def test_normalize_vendor_can_preserve_whitespace(self):
        self.assertEqual(normalize_vendor("  Cisco  ", strip=False), "  cisco  ")

    def test_normalize_hostname_defaults_without_strip(self):
        self.assertEqual(normalize_hostname("  SW-01  "), "  sw-01  ")

    def test_normalize_hostname_with_strip(self):
        self.assertEqual(normalize_hostname("  SW-01  ", strip=True), "sw-01")

    def test_first_matching_port_returns_first_match_in_order(self):
        self.assertEqual(first_matching_port([8443, 443], {443, 8443}), 8443)

    def test_first_matching_port_returns_none_when_no_match(self):
        self.assertIsNone(first_matching_port([80, 53], {443, 8443}))

    def test_first_matching_service_can_return_lowercase_value(self):
        self.assertEqual(
            first_matching_service([" SNMP ", "ssh"], {"ssh", "snmp"}, return_lower=True),
            "snmp",
        )

    def test_first_matching_service_can_preserve_original_case(self):
        self.assertEqual(
            first_matching_service([" SIP ", "sips"], {"sip", "sips"}),
            "SIP",
        )

    def test_first_matching_service_returns_none_when_no_match(self):
        self.assertIsNone(first_matching_service(["dns", "http"], {"sip", "sips"}))

    def test_format_hostname_evidence_reason_with_port_and_service(self):
        self.assertEqual(
            format_hostname_evidence_reason("switch-01", 161, "snmp", "switch management"),
            "Hostname 'switch-01' with open port 161 and service 'snmp' matched known switch management evidence.",
        )

    def test_format_hostname_evidence_reason_with_port_only(self):
        self.assertEqual(
            format_hostname_evidence_reason("switch-01", 161, None, "switch management"),
            "Hostname 'switch-01' with open port 161 matched known switch management evidence.",
        )

    def test_format_hostname_evidence_reason_with_service_only(self):
        self.assertEqual(
            format_hostname_evidence_reason("switch-01", None, "snmp", "switch management"),
            "Hostname 'switch-01' with service 'snmp' matched known switch management evidence.",
        )

    def test_first_containing_returns_first_matching_value(self):
        self.assertEqual(
            first_containing(["Apache httpd", "VMware ESXi Server httpd"], {"vmware"}),
            "VMware ESXi Server httpd",
        )

    def test_first_containing_is_case_insensitive(self):
        self.assertEqual(first_containing(["SONICWALL"], {"sonicwall"}), "SONICWALL")

    def test_first_containing_skips_none_and_empty_values(self):
        self.assertEqual(first_containing([None, "", "Cisco SSH"], {"cisco"}), "Cisco SSH")

    def test_first_containing_returns_none_when_no_match(self):
        self.assertIsNone(first_containing(["nginx", "Apache httpd"], {"vmware"}))

    def test_first_matching_product_returns_first_matching_product_string(self):
        services = [
            ServiceEvidence(port=80, protocol="tcp", product="nginx"),
            ServiceEvidence(port=443, protocol="tcp", product="VMware ESXi Server httpd"),
        ]
        self.assertEqual(first_matching_product(services, {"vmware"}), "VMware ESXi Server httpd")

    def test_first_matching_product_returns_none_when_no_match(self):
        services = [ServiceEvidence(port=80, protocol="tcp", product="nginx")]
        self.assertIsNone(first_matching_product(services, {"vmware"}))

    def test_first_matching_identifier_checks_product_before_http_title(self):
        services = [
            ServiceEvidence(
                port=443,
                protocol="tcp",
                product="VMware ESXi Server httpd",
                http_title="VMware ESXi",
            ),
        ]
        self.assertEqual(
            first_matching_identifier(services, {"vmware"}),
            ("service product", "VMware ESXi Server httpd"),
        )

    def test_first_matching_identifier_falls_back_to_http_title(self):
        services = [ServiceEvidence(port=443, protocol="tcp", http_title="SonicWALL Login")]
        self.assertEqual(
            first_matching_identifier(services, {"sonicwall"}),
            ("HTTP title", "SonicWALL Login"),
        )

    def test_first_matching_identifier_falls_back_to_tls_subject(self):
        services = [ServiceEvidence(port=443, protocol="tcp", tls_subject="commonName=SonicWALL")]
        self.assertEqual(
            first_matching_identifier(services, {"sonicwall"}),
            ("TLS certificate subject", "commonName=SonicWALL"),
        )

    def test_first_matching_identifier_falls_back_to_tls_issuer(self):
        services = [ServiceEvidence(port=443, protocol="tcp", tls_issuer="commonName=SonicWALL")]
        self.assertEqual(
            first_matching_identifier(services, {"sonicwall"}),
            ("TLS certificate issuer", "commonName=SonicWALL"),
        )

    def test_first_matching_identifier_returns_none_when_no_evidence_matches(self):
        services = [ServiceEvidence(port=80, protocol="tcp", product="nginx", http_title="Welcome")]
        self.assertIsNone(first_matching_identifier(services, {"sonicwall"}))


if __name__ == "__main__":
    unittest.main()

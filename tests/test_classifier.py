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

    def test_edgeswitch_http_title_classifies_as_switch_not_unknown(self):
        device = Device(
            ip_address="192.168.1.63",
            hostname="edge-01",
            vendor="Ubiquiti",
            services=[
                ServiceEvidence(port=80, protocol="tcp", http_title="Ubiquiti EdgeSwitch"),
            ],
        )

        result = DeviceClassifier().classify(device)

        self.assertEqual(result.device_type, DeviceType.SWITCH)

    def test_hp_procurve_switch_identifier_beats_printer_vendor_match(self):
        device = Device(
            ip_address="192.168.1.64",
            hostname="hp-sw-core-01",
            vendor="HP",
            services=[
                ServiceEvidence(
                    port=80,
                    protocol="tcp",
                    http_title="ProCurve Switch 2530-24G",
                ),
            ],
        )

        result = DeviceClassifier().classify(device)

        self.assertEqual(result.device_type, DeviceType.SWITCH)

    def test_hp_printer_without_switch_identifier_still_classifies_as_printer(self):
        device = Device(
            ip_address="192.168.1.65",
            hostname="print-hp-01",
            vendor="HP",
            services=[
                ServiceEvidence(
                    port=631,
                    protocol="tcp",
                    service="ipp",
                    product="HP LaserJet 4250",
                ),
            ],
        )

        result = DeviceClassifier().classify(device)

        self.assertEqual(result.device_type, DeviceType.PRINTER)

    def test_cisco_ip_phone_still_classifies_as_phone_not_switch(self):
        device = Device(
            ip_address="192.168.1.66",
            hostname="phone-02",
            vendor="Cisco IP Phone",
        )

        result = DeviceClassifier().classify(device)

        self.assertEqual(result.device_type, DeviceType.PHONE)

    def test_bench_002_netgear_readynas_device_now_classifies_as_server(self):
        """RULE-003: the exact BENCH-002 netgear-nas-01 device (vendor,
        hostname, and HTTP auth realm evidence) stayed UNKNOWN across
        FAST/STANDARD/DEEP before this sprint; it must now resolve."""
        device = Device(
            ip_address="172.16.100.20",
            hostname="netgear-nas-01",
            vendor="Netgear",
            services=[
                ServiceEvidence(port=80, protocol="tcp", http_auth_realm="NETGEAR ReadyNAS"),
            ],
        )

        result = DeviceClassifier().classify(device)

        self.assertEqual(result.device_type, DeviceType.SERVER)

    def test_bare_netgear_router_without_nas_identifier_remains_unknown(self):
        """Guards against NetworkApplianceRule over-reaching on vendor
        alone: a Netgear device with no NAS-specific identifier evidence
        must not be swept into SERVER."""
        device = Device(
            ip_address="192.168.1.67",
            hostname="netgear-router-01",
            vendor="Netgear",
        )

        result = DeviceClassifier().classify(device)

        self.assertEqual(result.device_type, DeviceType.UNKNOWN)

    def test_snmp_only_procurve_sys_descr_classifies_as_switch_not_unknown(self):
        """RULE-004: a device with no vendor, hostname, or service evidence
        -- previously UNKNOWN -- now resolves via SNMP sysDescr alone,
        using the classifier's existing switch identifier keyword list."""
        device = Device(
            ip_address="192.168.1.68",
            hostname=None,
            vendor=None,
            snmp_sys_descr="HP ProCurve Switch 2530-24G",
        )

        result = DeviceClassifier().classify(device)

        self.assertEqual(result.device_type, DeviceType.SWITCH)

    def test_snmp_only_generic_sys_descr_remains_unknown(self):
        """Guards against over-reach: SNMP evidence that doesn't match any
        rule's existing, already-vetted keyword list must not manufacture a
        classification."""
        device = Device(
            ip_address="192.168.1.69",
            hostname=None,
            vendor=None,
            snmp_sys_descr="Linux 5.15.0-generic #1 SMP x86_64 GNU/Linux",
        )

        result = DeviceClassifier().classify(device)

        self.assertEqual(result.device_type, DeviceType.UNKNOWN)

    def test_axis_vendor_with_camera_station_evidence_classifies_as_camera_via_full_classifier(self):
        """RULE-005 (architect review correction): the exact real
        production evidence for 172.16.101.138 -- Axis vendor plus a TLS
        certificate issued by AXIS Camera Station -- must resolve to
        CAMERA instead of UNKNOWN."""
        device = Device(
            ip_address="172.16.101.138",
            hostname=None,
            vendor="Axis Communications AB",
            services=[
                ServiceEvidence(port=80, protocol="tcp", http_title="Did not follow redirect to https://172.16.101.138/"),
                ServiceEvidence(
                    port=443,
                    protocol="tcp",
                    http_title="Site doesn't have a title (text/html).",
                    tls_subject="commonName=172.16.101.138",
                    tls_issuer="commonName=AXIS Camera Station root certificate",
                ),
            ],
        )

        result = DeviceClassifier().classify(device)

        self.assertEqual(result.device_type, DeviceType.CAMERA)

    def test_axis_vendor_with_only_generic_evidence_remains_unknown_via_full_classifier(self):
        """RULE-005 (architect review correction): Axis vendor identity
        alone -- the real, majority pattern across the actual production
        scan (25 of 38 Axis devices: a generic embedded web server and no
        distinguishing title) -- must NOT classify as CAMERA. Vendor is
        manufacturer identity, not device-category identity."""
        device = Device(
            ip_address="172.16.101.100",
            hostname=None,
            vendor="Axis Communications AB",
            services=[
                ServiceEvidence(port=80, protocol="tcp", product="Apache httpd 2.4.17", http_title="Index page"),
            ],
        )

        result = DeviceClassifier().classify(device)

        self.assertEqual(result.device_type, DeviceType.UNKNOWN)

    def test_unifi_guest_portal_redirect_classifies_as_access_point_not_printer(self):
        """RULE-005: the exact real production defect -- a UniFi access
        point's guest-portal redirect HTTP title, with no hostname,
        previously misclassified as PRINTER via an incidental "hp"
        substring collision. UbiquitiAccessPointRule must now resolve it
        to ACCESS_POINT before PrinterVendorRule is ever reached."""
        device = Device(
            ip_address="172.16.100.116",
            hostname=None,
            vendor="Ubiquiti",
            services=[
                ServiceEvidence(
                    port=80,
                    protocol="tcp",
                    service="http",
                    http_title=(
                        "Did not follow redirect to "
                        "http://172.16.100.89:8880/guest/s/default/?ap=0c:ea:14:b7:41:9d"
                        "&ec=4i5lQ9ecDwcp-LCkH1697alvguXoqmWg3DshpMadGs7OTsAnAWcJPf0sYnKy8ojRBcJi"
                    ),
                ),
                ServiceEvidence(
                    port=443,
                    protocol="tcp",
                    service="https",
                    http_title=(
                        "Did not follow redirect to "
                        "http://172.16.100.89:8880/guest/s/default/?ap=0c:ea:14:b7:41:9d"
                        "&ec=4i5lQ9ecDwcp-LCkH1697alvguXoqmWg3DshpMadGs7OTsAnAWcJPf0sYnKy8ojRBcJi"
                    ),
                    tls_subject="commonName=ui/organizationName=Ubiquiti Networks, Inc.",
                ),
            ],
        )

        result = DeviceClassifier().classify(device)

        self.assertEqual(result.device_type, DeviceType.ACCESS_POINT)

    def test_ubiquiti_edgeswitch_still_classifies_as_switch_not_access_point(self):
        """Regression guard: a genuine Ubiquiti EdgeSwitch (matched by
        SwitchVendorRule's identifier tier, which runs after
        UbiquitiAccessPointRule) must not be captured by the new
        guest-portal evidence path."""
        device = Device(
            ip_address="172.16.100.10",
            hostname=None,
            vendor="Ubiquiti",
            services=[
                ServiceEvidence(port=443, protocol="tcp", http_title="Ubiquiti EdgeSwitch"),
            ],
        )

        result = DeviceClassifier().classify(device)

        self.assertEqual(result.device_type, DeviceType.SWITCH)

    def test_bench_002_generic_web_app_title_remains_unknown(self):
        """BENCH-002's web-app-01 device (a generic internal web app HTTP
        title with no vendor signal) was deliberately left UNKNOWN, not
        misclassified into a guessed category -- RULE-003 must not widen
        NetworkApplianceRule or any other rule to swallow generic titles."""
        device = Device(
            ip_address="172.16.100.21",
            hostname="web-app-01",
            services=[
                ServiceEvidence(
                    port=8090,
                    protocol="tcp",
                    http_title="Internal Web App - Login",
                ),
            ],
        )

        result = DeviceClassifier().classify(device)

        self.assertEqual(result.device_type, DeviceType.UNKNOWN)


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

    def test_first_matching_identifier_falls_back_to_snmp_sys_descr(self):
        """RULE-004: SNMP sysDescr is checked last, after every
        service-derived evidence type, when no service evidence matches."""
        services = [ServiceEvidence(port=80, protocol="tcp", product="nginx")]
        self.assertEqual(
            first_matching_identifier(
                services,
                {"sonicwall"},
                snmp_sys_descr="SonicWALL TZ370 SonicOS 7.0.1",
            ),
            ("SNMP sysDescr", "SonicWALL TZ370 SonicOS 7.0.1"),
        )

    def test_first_matching_identifier_prefers_service_evidence_over_snmp_sys_descr(self):
        services = [ServiceEvidence(port=443, protocol="tcp", http_title="SonicWALL Login")]
        self.assertEqual(
            first_matching_identifier(
                services,
                {"sonicwall"},
                snmp_sys_descr="SonicWALL TZ370 SonicOS 7.0.1",
            ),
            ("HTTP title", "SonicWALL Login"),
        )

    def test_first_matching_identifier_ignores_snmp_sys_descr_when_not_supplied(self):
        """Default behavior for every pre-existing caller is unchanged: a
        None snmp_sys_descr (the default) contributes no match."""
        services = [ServiceEvidence(port=80, protocol="tcp", product="nginx")]
        self.assertIsNone(first_matching_identifier(services, {"sonicwall"}))


if __name__ == "__main__":
    unittest.main()

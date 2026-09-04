import unittest

from networkmapper.classification.rules.camera_vendor_rule import CameraVendorRule
from networkmapper.classification.rule_result import RuleResult
from networkmapper.core.models import Device, DeviceType, ServiceEvidence


class CameraVendorRuleTest(unittest.TestCase):
    def setUp(self):
        self.rule = CameraVendorRule()

    def test_axis_vendor_with_camera_station_tls_issuer_classifies_as_camera(self):
        """RULE-005 (architect review correction): reproduces real
        production evidence exactly (172.16.101.138/.140/.143) -- Axis
        vendor plus a TLS certificate issued by AXIS Camera Station, the
        one evidence field confirmed to name Axis's actual camera/video
        product line, not just the Axis brand generally."""
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

        result = self.rule.classify(device)

        self.assertIsInstance(result, RuleResult)
        self.assertTrue(result.matched)
        self.assertEqual(result.suggested_device_type, DeviceType.CAMERA)
        self.assertIn("AXIS Camera Station root certificate", result.reason)

    def test_axis_vendor_with_camera_station_tls_subject_classifies_as_camera(self):
        device = Device(
            ip_address="172.16.101.200",
            vendor="Axis Communications AB",
            services=[
                ServiceEvidence(
                    port=443,
                    protocol="tcp",
                    tls_subject="commonName=AXIS Camera Station managed device",
                ),
            ],
        )

        result = self.rule.classify(device)

        self.assertTrue(result.matched)
        self.assertEqual(result.suggested_device_type, DeviceType.CAMERA)

    def test_matching_is_case_insensitive_on_both_vendor_and_product_evidence(self):
        device = Device(
            ip_address="172.16.101.201",
            vendor="axis communications ab",
            services=[
                ServiceEvidence(port=443, protocol="tcp", tls_issuer="commonName=axis camera station root certificate"),
            ],
        )

        result = self.rule.classify(device)

        self.assertTrue(result.matched)
        self.assertEqual(result.suggested_device_type, DeviceType.CAMERA)

    def test_axis_vendor_alone_with_no_product_evidence_does_not_classify_as_camera(self):
        """RULE-005 (architect review correction): this is the real,
        majority pattern across the actual production scan (25 of 38
        Axis devices) -- vendor identity plus a generic embedded web
        server and no distinguishing title. Vendor identity alone must
        NOT classify as CAMERA; these devices correctly remain UNKNOWN."""
        device = Device(
            ip_address="172.16.101.100",
            hostname=None,
            vendor="Axis Communications AB",
            services=[
                ServiceEvidence(port=80, protocol="tcp", product="Apache httpd 2.4.17", http_title="Index page"),
            ],
        )

        result = self.rule.classify(device)

        self.assertFalse(result.matched)
        self.assertIsNone(result.suggested_device_type)
        self.assertEqual(
            result.reason,
            "Vendor 'Axis Communications AB' matched known camera vendor, but no "
            "camera/video-specific product evidence was detected.",
        )

    def test_axis_branded_title_without_camera_station_reference_does_not_classify_as_camera(self):
        """A bare "AXIS"-branded web UI title and an Axis self-signed
        certificate CN (both observed on real devices, e.g.
        172.16.101.130/.134) confirm the device is genuinely
        manufactured by Axis, but not that it is specifically a camera --
        Axis also ships non-camera network products under the same
        branding and certificate-naming convention. This must not match
        without the more specific "AXIS Camera Station" reference."""
        device = Device(
            ip_address="172.16.101.130",
            vendor="Axis Communications AB",
            services=[
                ServiceEvidence(port=80, protocol="tcp", http_title="AXIS"),
                ServiceEvidence(
                    port=443,
                    protocol="tcp",
                    http_title="AXIS",
                    tls_subject="commonName=axis-accc8e71b9a7/organizationName=Axis Communications AB",
                    tls_issuer="commonName=axis-accc8e71b9a7/organizationName=Axis Communications AB",
                ),
            ],
        )

        result = self.rule.classify(device)

        self.assertFalse(result.matched)
        self.assertIsNone(result.suggested_device_type)

    def test_axis_device_id_ca_without_camera_station_reference_does_not_classify_as_camera(self):
        """Mirrors real devices (e.g. 172.16.101.136/.142/.144) whose TLS
        issuer names Axis's device-identity CA -- confirms Axis
        manufacturing identity, not camera-specific product identity."""
        device = Device(
            ip_address="172.16.101.136",
            vendor="Axis Communications AB",
            services=[
                ServiceEvidence(
                    port=443,
                    protocol="tcp",
                    tls_subject="commonName=axis-e827250a1a1b-eccp256-1/organizationName=Axis Communications AB",
                    tls_issuer="commonName=Axis device ID Intermediate CA ECC 3/organizationName=Axis Communications AB",
                ),
            ],
        )

        result = self.rule.classify(device)

        self.assertFalse(result.matched)
        self.assertIsNone(result.suggested_device_type)

    def test_non_axis_vendor_with_camera_station_evidence_does_not_classify_as_camera(self):
        """The vendor gate is required in addition to the product
        identifier, per the architect's explicit "vendor AND product
        evidence" requirement -- neither is sufficient alone."""
        device = Device(
            ip_address="172.16.101.202",
            vendor="Dell",
            services=[
                ServiceEvidence(port=443, protocol="tcp", tls_issuer="commonName=AXIS Camera Station root certificate"),
            ],
        )

        result = self.rule.classify(device)

        self.assertFalse(result.matched)
        self.assertIsNone(result.suggested_device_type)

    def test_empty_vendor_is_ignored(self):
        device = Device(ip_address="172.16.101.102", vendor="")

        result = self.rule.classify(device)

        self.assertFalse(result.matched)
        self.assertIsNone(result.suggested_device_type)
        self.assertEqual(result.reason, "Vendor '' is not a known camera vendor.")

    def test_none_vendor_is_ignored(self):
        device = Device(ip_address="172.16.101.103", vendor=None)

        result = self.rule.classify(device)

        self.assertFalse(result.matched)
        self.assertIsNone(result.suggested_device_type)
        self.assertEqual(result.reason, "Vendor None is not a known camera vendor.")


if __name__ == "__main__":
    unittest.main()

import unittest

from networkmapper.core.models import ServiceEvidence
from networkmapper.discovery.run_diagnostics import (
    PROFILE_MESSAGES,
    ScanProfile,
    diagnose_host,
    profile_message,
)


class ProfileMessageTest(unittest.TestCase):
    def test_every_scan_profile_has_a_message(self):
        for profile in ScanProfile:
            self.assertIn(profile, PROFILE_MESSAGES)

    def test_fast_message_states_enrichment_is_disabled_by_design(self):
        message = profile_message(ScanProfile.FAST)

        self.assertIn("Host discovery only.", message)
        self.assertIn("Service enrichment disabled by design.", message)

    def test_deep_message_states_it_is_currently_identical_to_fast(self):
        message = profile_message(ScanProfile.DEEP)

        self.assertIn("Currently identical to FAST", message)
        self.assertIn("Service enrichment disabled by design.", message)

    def test_standard_message_lists_enrichment_scripts(self):
        message = profile_message(ScanProfile.STANDARD)

        self.assertIn("service enrichment", message.lower())
        self.assertIn("smb-os-discovery", message)


class DiagnoseHostTest(unittest.TestCase):
    def test_no_open_ports_reports_no_curated_ports_open(self):
        diagnostics = diagnose_host(services=[], smb_identity={}, rdp_identity={})

        self.assertFalse(diagnostics.enriched)
        self.assertFalse(diagnostics.has_service_evidence)
        self.assertIn("No curated ports open.", diagnostics.missing_evidence_reasons)

    def test_open_ports_without_named_services_reports_no_supported_services(self):
        services = [ServiceEvidence(port=22, protocol="tcp", service=None)]

        diagnostics = diagnose_host(services=services, smb_identity={}, rdp_identity={})

        self.assertTrue(diagnostics.has_service_evidence)
        self.assertIn(
            "Open ports detected, but no supported services identified.",
            diagnostics.missing_evidence_reasons,
        )
        self.assertNotIn("No curated ports open.", diagnostics.missing_evidence_reasons)

    def test_smb_and_rdp_ports_closed_are_reported_unreachable(self):
        services = [ServiceEvidence(port=80, protocol="tcp", service="http")]

        diagnostics = diagnose_host(services=services, smb_identity={}, rdp_identity={})

        self.assertIn(
            "SMB unreachable (port 445 not open).", diagnostics.missing_evidence_reasons
        )
        self.assertIn(
            "RDP unreachable (port 3389 not open).", diagnostics.missing_evidence_reasons
        )

    def test_smb_and_rdp_ports_open_are_not_reported_unreachable(self):
        services = [
            ServiceEvidence(port=445, protocol="tcp", service="microsoft-ds"),
            ServiceEvidence(port=3389, protocol="tcp", service="ms-wbt-server"),
        ]

        diagnostics = diagnose_host(services=services, smb_identity={}, rdp_identity={})

        self.assertNotIn(
            "SMB unreachable (port 445 not open).", diagnostics.missing_evidence_reasons
        )
        self.assertNotIn(
            "RDP unreachable (port 3389 not open).", diagnostics.missing_evidence_reasons
        )

    def test_no_http_like_service_reports_http_service_not_present(self):
        services = [ServiceEvidence(port=22, protocol="tcp", service="ssh")]

        diagnostics = diagnose_host(services=services, smb_identity={}, rdp_identity={})

        self.assertIn("HTTP service not present.", diagnostics.missing_evidence_reasons)

    def test_https_service_without_tls_subject_reports_certificate_not_presented(self):
        services = [ServiceEvidence(port=443, protocol="tcp", service="https", tls_subject=None)]

        diagnostics = diagnose_host(services=services, smb_identity={}, rdp_identity={})

        self.assertIn("TLS certificate not presented.", diagnostics.missing_evidence_reasons)
        self.assertNotIn("HTTP service not present.", diagnostics.missing_evidence_reasons)

    def test_https_service_with_tls_subject_reports_no_tls_gap(self):
        services = [
            ServiceEvidence(
                port=443, protocol="tcp", service="https", tls_subject="commonName=example"
            )
        ]

        diagnostics = diagnose_host(services=services, smb_identity={}, rdp_identity={})

        self.assertNotIn("TLS certificate not presented.", diagnostics.missing_evidence_reasons)
        self.assertTrue(diagnostics.has_tls_certificate)

    def test_plain_http_service_does_not_trigger_tls_check(self):
        services = [ServiceEvidence(port=80, protocol="tcp", service="http")]

        diagnostics = diagnose_host(services=services, smb_identity={}, rdp_identity={})

        self.assertNotIn("TLS certificate not presented.", diagnostics.missing_evidence_reasons)
        self.assertNotIn("HTTP service not present.", diagnostics.missing_evidence_reasons)

    def test_smb_identity_flag_reflects_smb_dict_before_merge(self):
        diagnostics = diagnose_host(
            services=[ServiceEvidence(port=445, protocol="tcp", service="microsoft-ds")],
            smb_identity={"operating_system": "Windows Server 2019", "computer_name": None},
            rdp_identity={},
        )

        self.assertTrue(diagnostics.has_smb_identity)
        self.assertFalse(diagnostics.has_rdp_identity)

    def test_rdp_identity_flag_reflects_rdp_dict_before_merge(self):
        diagnostics = diagnose_host(
            services=[ServiceEvidence(port=3389, protocol="tcp", service="ms-wbt-server")],
            smb_identity={},
            rdp_identity={"computer_name": "HOST-01", "domain": None},
        )

        self.assertTrue(diagnostics.has_rdp_identity)
        self.assertFalse(diagnostics.has_smb_identity)

    def test_enriched_is_true_when_only_identity_evidence_is_present(self):
        diagnostics = diagnose_host(
            services=[],
            smb_identity={"computer_name": "HOST-01"},
            rdp_identity={},
        )

        self.assertTrue(diagnostics.enriched)
        self.assertFalse(diagnostics.has_service_evidence)

    def test_fully_dark_host_is_not_enriched(self):
        diagnostics = diagnose_host(services=[], smb_identity={}, rdp_identity={})

        self.assertFalse(diagnostics.enriched)


if __name__ == "__main__":
    unittest.main()

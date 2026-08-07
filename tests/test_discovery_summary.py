import unittest

from networkmapper.discovery.run_diagnostics import HostDiagnostics, RunDiagnostics
from networkmapper.discovery.scan_profile import ScanProfile
from networkmapper.reporting.discovery_summary import DiscoverySummary


class DiscoverySummaryTest(unittest.TestCase):
    def test_summary_is_all_zero_when_enrichment_never_ran(self):
        run_diagnostics = RunDiagnostics(
            scan_profile=ScanProfile.FAST,
            hosts_discovered=5,
            enrichment_enabled=False,
        )

        summary = DiscoverySummary.from_run_diagnostics(run_diagnostics)

        self.assertEqual(summary.hosts_discovered, 5)
        self.assertEqual(summary.hosts_enriched, 0)
        self.assertEqual(summary.hosts_with_service_evidence, 0)
        self.assertEqual(summary.hosts_with_smb_identity, 0)
        self.assertEqual(summary.hosts_with_rdp_identity, 0)
        self.assertEqual(summary.hosts_with_http_titles, 0)
        self.assertEqual(summary.hosts_with_tls_certificates, 0)
        self.assertEqual(summary.hosts_with_http_auth_realms, 0)

    def test_summary_counts_are_derived_from_host_diagnostics(self):
        run_diagnostics = RunDiagnostics(
            scan_profile=ScanProfile.STANDARD,
            hosts_discovered=3,
            enrichment_enabled=True,
            enrichment_arguments="-Pn -sV",
            host_diagnostics={
                "10.0.0.1": HostDiagnostics(
                    enriched=True,
                    has_service_evidence=True,
                    has_smb_identity=True,
                    has_rdp_identity=False,
                    has_http_title=True,
                    has_tls_certificate=True,
                    has_http_auth_realm=False,
                ),
                "10.0.0.2": HostDiagnostics(
                    enriched=True,
                    has_service_evidence=True,
                    has_smb_identity=False,
                    has_rdp_identity=True,
                    has_http_title=False,
                    has_tls_certificate=False,
                    has_http_auth_realm=True,
                ),
                "10.0.0.3": HostDiagnostics(
                    enriched=False,
                    has_service_evidence=False,
                    has_smb_identity=False,
                    has_rdp_identity=False,
                    has_http_title=False,
                    has_tls_certificate=False,
                    has_http_auth_realm=False,
                    missing_evidence_reasons=["No curated ports open."],
                ),
            },
        )

        summary = DiscoverySummary.from_run_diagnostics(run_diagnostics)

        self.assertEqual(summary.hosts_discovered, 3)
        self.assertEqual(summary.hosts_enriched, 2)
        self.assertEqual(summary.hosts_with_service_evidence, 2)
        self.assertEqual(summary.hosts_with_smb_identity, 1)
        self.assertEqual(summary.hosts_with_rdp_identity, 1)
        self.assertEqual(summary.hosts_with_http_titles, 1)
        self.assertEqual(summary.hosts_with_tls_certificates, 1)
        self.assertEqual(summary.hosts_with_http_auth_realms, 1)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import dataclasses

from networkmapper.classification.classification_rule import ClassificationRule
from networkmapper.classification.evidence_helpers import (
    first_matching_identifier,
    normalize_vendor,
)
from networkmapper.classification.rule_result import RuleResult
from networkmapper.core.models import Device, DeviceType, ServiceEvidence


SUPPORTED_PRINTER_VENDOR_KEYWORDS = (
    "brother",
    "hp",
    "hewlett-packard",
    "hewlett packard",
    "canon",
    "ricoh",
    "konica minolta",
    "epson",
    "xerox",
    "lexmark",
    "kyocera",
    "sharp",
    "toshiba",
    "zebra",
    "datamax",
    "fujifilm business innovation",
)

PRINTER_PROTOCOL_PORTS = {515, 631, 9100}
PRINTER_SERVICE_KEYWORDS = (
    "ipp",
    "ipps",
    "jetdirect",
    "lpd",
    "printer",
    "raw",
    "pdl-datastream",
)

# RULE-005: nmap's http-title script emits this fixed-format notice --
# scanner commentary, not device-reported identity text -- when a page
# redirects without being followed, and often embeds the full opaque
# redirect URL (including any query-string tokens) verbatim. A real-world
# UniFi guest-portal redirect's opaque ticket token was found to contain
# the bare "hp" keyword purely by incidental substring collision,
# misclassifying Ubiquiti access points as printers. Filtering this
# specific notice out of identifier matching (not any other HTTP title)
# closes that hole without touching genuine printer HTTP titles, which
# never take this fixed form.
_REDIRECT_NOTICE_PREFIX = "did not follow redirect"


class PrinterVendorRule(ClassificationRule):
    """Match vendors that indicate a printer device."""

    def classify(self, device: Device) -> RuleResult:
        """Return a rule result for printer vendor matching evidence."""
        raw_vendor = device.vendor
        vendor = normalize_vendor(raw_vendor, strip=True)

        if vendor and any(keyword in vendor for keyword in SUPPORTED_PRINTER_VENDOR_KEYWORDS):
            return RuleResult(
                matched=True,
                confidence_contribution=0,
                reason=f"Vendor {raw_vendor!r} matched known printer vendor.",
                suggested_device_type=DeviceType.PRINTER,
            )

        matched_identifier = self._find_printer_vendor_identifier(device)
        if matched_identifier is not None:
            label, value = matched_identifier
            return RuleResult(
                matched=True,
                confidence_contribution=0,
                reason=(
                    f"Detected {label} {value!r} matched known printer vendor "
                    "identifier."
                ),
                suggested_device_type=DeviceType.PRINTER,
            )

        matched_port, matched_service = self._find_printer_networking(device)
        if matched_port is not None or matched_service is not None:
            return RuleResult(
                matched=True,
                confidence_contribution=0,
                reason=self._format_networking_reason(matched_port, matched_service),
                suggested_device_type=DeviceType.PRINTER,
            )

        return RuleResult(
            matched=False,
            confidence_contribution=0,
            reason=(
                f"Vendor {raw_vendor!r} is not a known printer vendor and "
                "no printer networking protocols were detected."
            ),
            suggested_device_type=None,
        )

    def _find_printer_vendor_identifier(self, device: Device) -> tuple[str, str] | None:
        """Return a (label, value) evidence pair naming a known printer vendor, if any.

        Nmap's IPP (port 631) service probe commonly returns the exact
        printer make/model as the product string (e.g. "HP LaserJet
        4250"), and printer web management UIs commonly show the same
        make/model in their page title (FEAT-003F). Both reuse the same
        trusted vendor keyword list rather than introducing a new
        fingerprint.

        RULE-004: a printer's SNMP `sysDescr` is checked against this same
        keyword list too (via `first_matching_identifier`'s optional
        `snmp_sys_descr` parameter). ARCH-012 cites "HP LaserJet 4250,
        Firmware..." as a realistic printer `sysDescr` -- the same
        make/model text this rule already trusts from a product string or
        HTTP title, just reported over SNMP instead.
        """
        return first_matching_identifier(
            self._without_redirect_notice_titles(device.services),
            SUPPORTED_PRINTER_VENDOR_KEYWORDS,
            snmp_sys_descr=device.snmp_sys_descr,
        )

    def _without_redirect_notice_titles(
        self, services: list[ServiceEvidence]
    ) -> list[ServiceEvidence]:
        """Return `services` with any "Did not follow redirect..." HTTP
        title evidence removed before identifier matching.

        Only `http_title` is nulled, on a shallow per-entry copy --
        `product`, `tls_subject`, `tls_issuer`, `http_auth_realm`, and any
        other port's own (non-redirect-notice) `http_title` are
        untouched, so a real printer that happens to also show a redirect
        notice on an unrelated port remains correctly detected via its
        other evidence.
        """
        return [
            (
                dataclasses.replace(entry, http_title=None)
                if entry.http_title
                and entry.http_title.strip().lower().startswith(_REDIRECT_NOTICE_PREFIX)
                else entry
            )
            for entry in services
        ]

    def _find_printer_networking(self, device: Device) -> tuple[int | None, str | None]:
        """Return a (port, service) evidence pair from printer-networking
        protocols, if any.

        RULE-006: independently scans for a matching port and a matching
        service name (preserving the original two-tier behavior: a device
        can be caught by either signal, from different service-evidence
        entries), but excludes a candidate entry whose own `product`
        field names a Microsoft-branded implementation (e.g. "Microsoft
        lpd") -- a Windows host running a print-spooler service is not
        itself a printer. Confirmed against real production evidence:
        four Windows/Dell hosts running Terminal Services and SMB were
        misclassified PRINTER solely because their LPD daemon's product
        string is "Microsoft lpd," not a printer vendor's own LPD stack.
        Scoped to the exact evidence entry producing each match, not the
        device as a whole, so a genuine multi-function printer that also
        exposes SMB (e.g. for scan-to-network-share) is unaffected.
        """
        matched_port = self._find_printer_port(device.services)
        matched_service = self._find_printer_service(device.services)
        return matched_port, matched_service

    def _find_printer_port(self, services: list[ServiceEvidence]) -> int | None:
        for entry in services:
            if entry.port in PRINTER_PROTOCOL_PORTS and not self._is_microsoft_product(
                entry.product
            ):
                return entry.port
        return None

    def _find_printer_service(self, services: list[ServiceEvidence]) -> str | None:
        for entry in services:
            if not entry.service:
                continue
            value = entry.service.strip()
            if value.lower() in PRINTER_SERVICE_KEYWORDS and not self._is_microsoft_product(
                entry.product
            ):
                return value
        return None

    def _is_microsoft_product(self, product: str | None) -> bool:
        return bool(product) and "microsoft" in product.lower()

    def _format_networking_reason(
        self,
        matched_port: int | None,
        matched_service: str | None,
    ) -> str:
        if matched_port is not None and matched_service is not None:
            return (
                f"Open TCP port {matched_port}{self._port_label(matched_port)} indicates "
                "printer networking. "
                f"Detected {self._service_label(matched_service)} service indicates "
                "printer networking."
            )

        if matched_port is not None:
            return (
                f"Open TCP port {matched_port}{self._port_label(matched_port)} indicates "
                "printer networking."
            )

        return (
            f"Detected {self._service_label(matched_service)} service indicates printer "
            "networking."
        )

    def _port_label(self, port: int) -> str:
        if port == 9100:
            return " (JetDirect)"
        if port == 631:
            return " (IPP)"
        if port == 515:
            return " (LPD)"
        return ""

    def _service_label(self, service: str | None) -> str:
        if service is None:
            return "Unknown"
        return service.upper()

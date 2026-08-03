from __future__ import annotations

from networkmapper.classification.classification_rule import ClassificationRule
from networkmapper.classification.evidence_helpers import (
    first_matching_port,
    first_matching_product,
    first_matching_service,
    normalize_vendor,
    service_names,
    service_ports,
)
from networkmapper.classification.rule_result import RuleResult
from networkmapper.core.models import Device, DeviceType


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

        matched_product = self._find_printer_vendor_product(device)
        if matched_product is not None:
            return RuleResult(
                matched=True,
                confidence_contribution=0,
                reason=(
                    f"Detected service product {matched_product!r} matched known "
                    "printer vendor identifier."
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

    def _find_printer_vendor_product(self, device: Device) -> str | None:
        """Return a service product string that names a known printer vendor, if any.

        Nmap's IPP (port 631) service probe commonly returns the exact
        printer make/model as the product string (e.g. "HP LaserJet
        4250"), which is at least as strong an identifier as the vendor
        field and reuses the same trusted vendor keyword list rather than
        introducing a new fingerprint.
        """
        return first_matching_product(device.services, SUPPORTED_PRINTER_VENDOR_KEYWORDS)

    def _find_printer_networking(self, device: Device) -> tuple[int | None, str | None]:
        matched_port = first_matching_port(
            service_ports(device.services),
            PRINTER_PROTOCOL_PORTS,
        )

        matched_service = first_matching_service(
            service_names(device.services),
            PRINTER_SERVICE_KEYWORDS,
            return_lower=False,
        )

        return matched_port, matched_service

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

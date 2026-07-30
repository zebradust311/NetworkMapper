from __future__ import annotations

from networkmapper.classification.classification_rule import ClassificationRule
from networkmapper.classification.evidence_helpers import (
    first_matching_port,
    first_matching_service,
    format_hostname_evidence_reason,
    normalize_hostname,
)
from networkmapper.classification.rule_result import RuleResult
from networkmapper.core.models import Device, DeviceType


# Vendor-defined and generic administrator naming conventions observed for
# hypervisor hosts. "vsh" is a single customer-observed convention (see
# docs/knowledge/FIELD-OBSERVATIONS.md #001) rather than a vendor or product
# naming standard. It is kept in this list for backward compatibility with
# the existing enterprise benchmark case, not because it generalizes to
# other environments.
HYPERVISOR_HOSTNAME_KEYWORDS = (
    "esx",
    "esxi",
    "hyperv",
    "vcenter",
    "vmhost",
    "vsh",
)

# Ports and services already collected under STANDARD-profile discovery that
# can corroborate a hostname match. Neither is hypervisor-exclusive on its
# own (443 is common to many web UIs; 3389 is common to any Windows host),
# so they only strengthen the explanation for an existing hostname match and
# are never used as an independent match condition.
HYPERVISOR_CORROBORATING_PORTS = {443, 3389}
HYPERVISOR_CORROBORATING_SERVICES = {"https", "ms-wbt-server"}


class HypervisorHostnameRule(ClassificationRule):
    """Match hostnames that indicate a hypervisor, such as those containing 'esxi' or 'vcenter'."""

    def classify(self, device: Device) -> RuleResult:
        """Return a rule result for hypervisor hostname matching evidence."""
        raw_hostname = device.hostname
        hostname = normalize_hostname(raw_hostname, strip=False)

        if not any(keyword in hostname for keyword in HYPERVISOR_HOSTNAME_KEYWORDS):
            return RuleResult(
                matched=False,
                confidence_contribution=0,
                reason=f"Hostname {raw_hostname!r} did not match known hypervisor naming conventions.",
                suggested_device_type=None,
            )

        matched_port = first_matching_port(device.open_ports, HYPERVISOR_CORROBORATING_PORTS)
        matched_service = first_matching_service(
            device.detected_services,
            HYPERVISOR_CORROBORATING_SERVICES,
            return_lower=True,
        )

        if matched_port is not None or matched_service is not None:
            reason = format_hostname_evidence_reason(
                raw_hostname,
                matched_port,
                matched_service,
                "hypervisor",
            )
        else:
            reason = f"Hostname {raw_hostname!r} matched known hypervisor naming convention."

        return RuleResult(
            matched=True,
            confidence_contribution=0,
            reason=reason,
            suggested_device_type=DeviceType.HYPERVISOR,
        )

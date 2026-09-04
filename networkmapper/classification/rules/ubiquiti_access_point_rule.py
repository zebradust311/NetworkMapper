from __future__ import annotations

from networkmapper.classification.classification_rule import ClassificationRule
from networkmapper.classification.evidence_helpers import (
    first_containing,
    normalize_hostname,
    normalize_vendor,
    service_http_titles,
)
from networkmapper.classification.rule_result import RuleResult
from networkmapper.core.models import Device, DeviceType


UBIQUITI_AP_HOSTNAME_KEYWORDS = (
    "nanohd",
    "ac-pro",
    "ac-lr",
    "unifi-ap",
)

# RULE-005: UniFi Network Controller's own guest-portal route name.
# A real-world Ubiquiti access point's guest network redirects
# unauthenticated clients here (surfaced by nmap's http-title script as
# "Did not follow redirect to http://<controller>/guest/s/default/?ap=...").
# This is strong, UniFi-specific evidence independent of whether the
# device ever self-reports a hostname -- real-world UniFi APs are
# frequently discovered with no hostname at all, which the hostname-only
# checks below cannot resolve on their own.
UNIFI_GUEST_PORTAL_TITLE_KEYWORDS = ("guest/s/default",)


class UbiquitiAccessPointRule(ClassificationRule):
    """Match Ubiquiti access points identified by hostname or guest-portal evidence."""

    def classify(self, device: Device) -> RuleResult:
        """Return a rule result for Ubiquiti wireless infrastructure evidence."""
        raw_vendor = device.vendor
        raw_hostname = device.hostname
        vendor = normalize_vendor(raw_vendor, strip=False)
        hostname = (raw_hostname or "").strip()
        hostname_normalized = normalize_hostname(raw_hostname, strip=True)

        if vendor != "ubiquiti":
            return self._not_matched(raw_vendor, raw_hostname)

        if hostname:
            hostname_prefix = hostname_normalized.split("-", 1)[0]
            if hostname_prefix in {"uap", "u6", "u7"}:
                return RuleResult(
                    matched=True,
                    confidence_contribution=0,
                    reason=(
                        f"Vendor {raw_vendor!r} and hostname {raw_hostname!r} matched "
                        "known wireless infrastructure vendor."
                    ),
                    suggested_device_type=DeviceType.ACCESS_POINT,
                )

            if any(keyword in hostname_normalized for keyword in UBIQUITI_AP_HOSTNAME_KEYWORDS):
                return RuleResult(
                    matched=True,
                    confidence_contribution=0,
                    reason=(
                        f"Vendor {raw_vendor!r} and hostname {raw_hostname!r} matched "
                        "known wireless access point naming patterns."
                    ),
                    suggested_device_type=DeviceType.ACCESS_POINT,
                )

        matched_title = self._find_guest_portal_identifier(device)
        if matched_title is not None:
            return RuleResult(
                matched=True,
                confidence_contribution=0,
                reason=(
                    f"Vendor {raw_vendor!r} and HTTP title {matched_title!r} matched "
                    "known UniFi guest-portal captive-redirect evidence."
                ),
                suggested_device_type=DeviceType.ACCESS_POINT,
            )

        return self._not_matched(raw_vendor, raw_hostname)

    def _find_guest_portal_identifier(self, device: Device) -> str | None:
        """Return the first HTTP title containing UniFi's guest-portal
        captive-redirect path, if any."""
        return first_containing(
            service_http_titles(device.services), UNIFI_GUEST_PORTAL_TITLE_KEYWORDS
        )

    def _not_matched(self, raw_vendor: str | None, raw_hostname: str | None) -> RuleResult:
        return RuleResult(
            matched=False,
            confidence_contribution=0,
            reason=(
                f"Vendor {raw_vendor!r} and hostname {raw_hostname!r} did not match "
                "known wireless infrastructure vendor patterns."
            ),
            suggested_device_type=None,
        )

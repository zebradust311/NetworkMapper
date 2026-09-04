from __future__ import annotations

from networkmapper.classification.classification_rule import ClassificationRule
from networkmapper.classification.evidence_helpers import first_matching_identifier, normalize_vendor
from networkmapper.classification.rule_result import RuleResult
from networkmapper.core.models import Device, DeviceType


# RULE-005: "axis communications" (the two-word phrase), not a bare
# "axis", is used deliberately -- directly applying the lesson RULE-005
# found in PrinterVendorRule's own "hp" keyword (a short substring
# incidentally colliding with unrelated evidence). A longer, more
# specific phrase avoids introducing that same class of risk here.
SUPPORTED_CAMERA_VENDOR_KEYWORDS = ("axis communications",)

# RULE-005 (architect review correction): vendor identity alone is
# manufacturer identity, not device-category identity -- Axis
# Communications also makes non-camera network products (door
# controllers, network audio, PoE switches, encoders), so "vendor is
# Axis" does not by itself mean "this device is a camera." This rule
# requires vendor evidence AND genuinely camera/video-specific product
# evidence together, never vendor alone.
#
# "axis camera station" is the one keyword confirmed, by direct
# investigation of real production evidence
# (output/2026-09-04_111544_standard/report.md), to name Axis's actual
# camera/video-surveillance product line by name (AXIS Camera Station is
# Axis's own VMS software, which issues TLS certificates to the camera
# fleet it manages) -- not merely "this is an Axis device" evidence like
# a bare "AXIS"-titled web UI or an "axis-<hex>" self-signed certificate
# CN, both of which the same investigation found on real devices but
# which equally describe any Axis network product, camera or not, and
# are deliberately NOT included here for that reason.
CAMERA_PRODUCT_IDENTIFIER_KEYWORDS = ("axis camera station",)


class CameraVendorRule(ClassificationRule):
    """Match vendor evidence combined with camera/video-specific product evidence."""

    def classify(self, device: Device) -> RuleResult:
        """Return a rule result for camera vendor plus product matching evidence."""
        raw_vendor = device.vendor
        vendor = normalize_vendor(raw_vendor, strip=True)
        vendor_matched = bool(vendor) and any(
            keyword in vendor for keyword in SUPPORTED_CAMERA_VENDOR_KEYWORDS
        )

        if not vendor_matched:
            return RuleResult(
                matched=False,
                confidence_contribution=0,
                reason=f"Vendor {raw_vendor!r} is not a known camera vendor.",
                suggested_device_type=None,
            )

        matched_identifier = first_matching_identifier(
            device.services,
            CAMERA_PRODUCT_IDENTIFIER_KEYWORDS,
            snmp_sys_descr=device.snmp_sys_descr,
        )
        if matched_identifier is None:
            return RuleResult(
                matched=False,
                confidence_contribution=0,
                reason=(
                    f"Vendor {raw_vendor!r} matched known camera vendor, but no "
                    "camera/video-specific product evidence was detected."
                ),
                suggested_device_type=None,
            )

        label, value = matched_identifier
        return RuleResult(
            matched=True,
            confidence_contribution=0,
            reason=(
                f"Vendor {raw_vendor!r} matched known camera vendor, and detected "
                f"{label} {value!r} matched known camera/video product evidence."
            ),
            suggested_device_type=DeviceType.CAMERA,
        )

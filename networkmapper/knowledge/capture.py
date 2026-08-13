from __future__ import annotations

from dataclasses import replace
from datetime import datetime

from networkmapper.classification.device_classifier import DeviceClassifier
from networkmapper.classification.rule_result import RuleResult
from networkmapper.core.models import Device, DeviceType
from networkmapper.knowledge.models import (
    Observation,
    ObservationClassification,
    ObservationDevice,
    ObservationEvidence,
    ObservationNetwork,
    ObservationScan,
    ObservationServiceEvidence,
)
from networkmapper.knowledge.repository import ObservationRepository
from networkmapper.reporting.report_run import RunMetadata

_NO_RULE_MATCHED_REASON = "No rule matched."


def should_capture(device: Device) -> bool:
    """Return True only for devices classification could not resolve.

    KNOW-003 scopes automatic capture to unresolved (UNKNOWN) devices —
    the repository exists to preserve high-value unresolved field
    evidence, not a second copy of every scan report. A device that
    already matched a rule has nothing this repository needs to add.
    """
    return device.device_type == DeviceType.UNKNOWN


def build_observation(
    device: Device,
    *,
    observation_id: int,
    run_metadata: RunMetadata,
    captured_at: datetime | None = None,
) -> Observation:
    """Build an Observation from a device's canonical discovery/classification
    state.

    Re-evaluates classification against a copy of the device (never the
    original) to recover the RuleResult evidence behind its current
    device_type, the same non-mutating pattern
    networkmapper.exporters.markdown_exporter.MarkdownExporter uses and
    ADR-005 requires for any presentation/reporting consumer. This does
    not change the device's stored classification.
    """
    classification_type, reason, matched_rule = _evaluate_classification(device)

    return Observation(
        observation_id=observation_id,
        captured_at=(captured_at or datetime.now()).isoformat(),
        network=ObservationNetwork(name=run_metadata.customer_name),
        scan=ObservationScan(
            profile=run_metadata.scan_profile.value,
            networkmapper_version=run_metadata.version,
        ),
        device=ObservationDevice(
            ip=device.ip_address,
            hostname=device.hostname,
            vendor=device.vendor,
            mac_address=device.mac_address,
        ),
        evidence=ObservationEvidence(
            operating_system=device.operating_system,
            computer_name=device.computer_name,
            domain=device.domain,
            smb_signing=device.smb_signing,
            discovery_sources=list(device.discovery_sources),
            services=[
                ObservationServiceEvidence(
                    port=entry.port,
                    protocol=entry.protocol,
                    service=entry.service,
                    product=entry.product,
                    version=entry.version,
                    http_title=entry.http_title,
                    tls_subject=entry.tls_subject,
                    tls_issuer=entry.tls_issuer,
                    http_auth_realm=entry.http_auth_realm,
                )
                for entry in device.services
            ],
        ),
        classification=ObservationClassification(
            type=classification_type,
            reason=reason,
            matched_rule=matched_rule,
        ),
    )


def capture_unresolved_device(
    device: Device,
    run_metadata: RunMetadata,
    repository: ObservationRepository | None = None,
) -> Observation | None:
    """Capture one device as a new observation, if it qualifies.

    Returns None without writing anything when should_capture(device) is
    False. This is a plain, callable function — nothing in NetworkMapper
    calls it automatically today. See KNOW-003's sprint report ("Capture
    Policy") for why automatic runtime wiring was deliberately left as an
    open architectural decision rather than implemented in this sprint.
    """
    if not should_capture(device):
        return None

    repository = repository or ObservationRepository()
    observation = build_observation(
        device,
        observation_id=repository.next_observation_id(),
        run_metadata=run_metadata,
    )
    repository.save(observation)
    return observation


def _evaluate_classification(device: Device) -> tuple[str, str, str | None]:
    """Return (device_type_value, reason, matched_rule_name) for a device,
    without mutating it."""
    classifier = DeviceClassifier()
    classifier.classify(replace(device))
    rule_results = classifier.get_last_rule_results()
    rule_names = [rule.__class__.__name__ for rule in classifier._rules][: len(rule_results)]

    if device.device_type == DeviceType.UNKNOWN or not rule_results:
        return DeviceType.UNKNOWN.value, _NO_RULE_MATCHED_REASON, None

    matched_rule_name, matched_result = _matching_rule(rule_names, rule_results)
    if matched_result is None:
        return DeviceType.UNKNOWN.value, _NO_RULE_MATCHED_REASON, None

    return device.device_type.value, matched_result.reason, matched_rule_name


def _matching_rule(
    rule_names: list[str],
    rule_results: tuple[RuleResult, ...],
) -> tuple[str | None, RuleResult | None]:
    """Return the name and result of the rule that matched, if any.

    DeviceClassifier is first-match-wins and stops evaluating as soon as
    a rule matches, so the last evaluated result is the matching one
    whenever the device isn't UNKNOWN.
    """
    if not rule_results:
        return None, None

    last_result = rule_results[-1]
    if not last_result.matched:
        return None, None

    return rule_names[-1], last_result

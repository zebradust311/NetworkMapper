from __future__ import annotations

from dataclasses import replace

from networkmapper.classification.device_classifier import DeviceClassifier
from networkmapper.core.models import Device, DeviceType
from networkmapper.project.models import Project


class ClassificationWorkbench:
    """Generate a developer-only evidence report for devices classified as UNKNOWN."""

    def generate(self, project: Project) -> str:
        """Create a plain-text report that exposes evidence for UNKNOWN devices.

        Args:
            project: The project snapshot to inspect for unknown-device evidence.

        Returns:
            A deterministic plain-text report intended for developer use.
        """
        unknown_devices = [
            device
            for device in project.network_graph.all_devices()
            if device.device_type == DeviceType.UNKNOWN
        ]

        if not unknown_devices:
            return "No UNKNOWN devices found."

        sections: list[str] = []
        classifier = DeviceClassifier()
        for device in unknown_devices:
            evidence = self._build_rule_evidence(device, classifier)
            sections.append(self._render_device_section(device, evidence))

        return "\n\n".join(sections)

    def _render_device_section(self, device: Device, evidence: str) -> str:
        """Render a single UNKNOWN-device evidence section for developer inspection."""
        return (
            "=" * 50
            + "\n"
            + "UNKNOWN DEVICE\n"
            + "=" * 50
            + "\n\n"
            + f"IP Address:\n{self._display_value(device.ip_address)}\n\n"
            + f"Hostname:\n{self._display_value(device.hostname)}\n\n"
            + f"Vendor:\n{self._display_value(device.vendor)}\n\n"
            + f"MAC Address:\n{self._display_value(device.mac_address)}\n\n"
            + f"Operating System:\n{self._display_value(device.operating_system)}\n\n"
            + "Open Ports:\n"
            + f"{self._display_list(device.open_ports)}\n\n"
            + "Detected Services:\n"
            + f"{self._display_list(device.detected_services)}\n\n"
            + f"Current DeviceType:\n{self._display_value(device.device_type)}\n"
            + "\n"
            + "Rule Evidence:\n"
            + f"{evidence}\n"
            + "\n"
            + "=" * 50
        )

    def _build_rule_evidence(self, device: Device, classifier: DeviceClassifier) -> str:
        """Classify a copy of the device and render rule-by-rule evidence."""
        classifier.classify(replace(device))
        rule_results = classifier.get_last_rule_results()
        rule_names = [rule.__class__.__name__ for rule in classifier._rules]

        sections: list[str] = []
        for index, result in enumerate(rule_results):
            rule_name = (
                rule_names[index] if index < len(rule_names) else f"Rule{index + 1}"
            )
            matched = "Yes" if result.matched else "No"
            suggested_type = (
                result.suggested_device_type.name
                if result.suggested_device_type is not None
                else "None"
            )

            sections.append(
                "-" * 40
                + "\n"
                + f"Rule: {rule_name}\n"
                + f"Matched: {matched}\n"
                + f"Suggested Type: {suggested_type}\n"
                + "Reason:\n"
                + f"{self._display_value(result.reason)}"
            )

        return "\n\n".join(sections)

    def _display_list(self, values: list[object]) -> str:
        """Return one value per line for populated lists, otherwise Unknown."""
        if not values:
            return "Unknown"

        return "\n".join(str(value) for value in values)

    def _display_value(self, value: object) -> str:
        """Return a clean display string for missing values in the report."""
        if value is None:
            return "Unknown"
        if isinstance(value, str) and not value.strip():
            return "Unknown"
        return str(value)

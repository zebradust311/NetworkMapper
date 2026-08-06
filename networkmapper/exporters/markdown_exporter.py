from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import replace
from datetime import datetime

from networkmapper.classification.device_classifier import DeviceClassifier
from networkmapper.classification.rule_result import RuleResult
from networkmapper.core.models import Device, DeviceType, ServiceEvidence
from networkmapper.project.models import Project
from networkmapper.reporting.project_summary import ProjectSummary


class MarkdownExporter:
    """Export a project snapshot as an evidence-rich engineering Markdown report.

    REPORT-001 redesigned this report so an engineer can answer, per device,
    "what is this, why was it classified this way, and what evidence
    supports that" without reading source code. Presentation only: no
    field, evidence, or classification logic is introduced here that
    doesn't already exist on `Device`/`ServiceEvidence`/`RuleResult`.
    """

    def export(self, project: Project, output_path: str) -> None:
        """Write a Markdown report for a project to the given output path.

        Args:
            project: The project snapshot to export.
            output_path: The output file path for the Markdown report.
        """
        summary = ProjectSummary.from_project(project)
        classifier = DeviceClassifier()
        markdown_lines = self._render_markdown(project, summary, classifier)

        with open(output_path, "w", encoding="utf-8") as markdown_file:
            markdown_file.write("\n".join(markdown_lines) + "\n")

    def _render_markdown(
        self,
        project: Project,
        summary: ProjectSummary,
        classifier: DeviceClassifier,
    ) -> list[str]:
        """Render the full report: summary, classification overview,
        per-device inventory, then appendices — in that order, so an
        engineer sees identity/evidence/reasoning before aggregate stats."""
        lines: list[str] = []
        lines.extend(self._render_executive_summary(summary))
        lines.append("")
        lines.extend(self._render_classification_overview(project))
        lines.append("")
        lines.extend(self._render_device_inventory(project, classifier))
        lines.append("")
        lines.extend(self._render_appendices(project, summary))

        return lines

    # ------------------------------------------------------------------
    # Executive Summary (retained from the prior report, unchanged content)
    # ------------------------------------------------------------------

    def _render_executive_summary(self, summary: ProjectSummary) -> list[str]:
        """Render the Customer and Executive Summary sections."""
        lines: list[str] = []
        lines.append("# Customer")
        lines.append("")
        lines.append(f"- Customer Name: {self._display_value(summary.customer_name)}")
        lines.append(f"- Created: {self._display_value(summary.created_at)}")
        lines.append(f"- Last Updated: {self._display_value(summary.updated_at)}")
        lines.append("")
        lines.append("# Executive Summary")
        lines.append("")
        lines.append(f"- Total Devices: {summary.total_devices}")
        lines.append("")
        lines.append("## Device Types")
        lines.append("")
        for device_type, count in sorted(
            summary.device_type_counts.items(),
            key=lambda item: item[0].value,
        ):
            lines.append(f"- {self._display_title(device_type)}: {count}")

        return lines

    # ------------------------------------------------------------------
    # Classification Overview (new, REPORT-001)
    # ------------------------------------------------------------------

    def _render_classification_overview(self, project: Project) -> list[str]:
        """Summarize UNKNOWN-device statistics already derivable from the
        project's own data — no new discovery, no invented recommendations."""
        lines: list[str] = ["# Classification Overview", ""]

        all_devices = project.network_graph.all_devices()
        unknown_devices = [
            device for device in all_devices if device.device_type == DeviceType.UNKNOWN
        ]

        if not unknown_devices:
            lines.append("No UNKNOWN devices.")
            return lines

        total = len(all_devices)
        unknown_percentage = (len(unknown_devices) / total) * 100 if total else 0.0

        lines.append(f"- Total UNKNOWN Devices: {len(unknown_devices)}")
        lines.append(f"- UNKNOWN Devices as % of Total: {unknown_percentage:.1f}%")
        lines.append("")

        lines.append("## UNKNOWN Devices by Vendor")
        lines.append("")
        vendor_counts = Counter(
            self._display_value(device.vendor) for device in unknown_devices
        )
        for vendor, count in sorted(vendor_counts.items()):
            lines.append(f"- {vendor}: {count}")
        lines.append("")

        lines.append("## UNKNOWN Devices by Operating System (where known)")
        lines.append("")
        os_counts = Counter(
            device.operating_system or "Not Determined" for device in unknown_devices
        )
        for operating_system, count in sorted(os_counts.items()):
            lines.append(f"- {operating_system}: {count}")

        return lines

    # ------------------------------------------------------------------
    # Per-device inventory: Identity, Evidence, Classification
    # ------------------------------------------------------------------

    def _render_device_inventory(
        self,
        project: Project,
        classifier: DeviceClassifier,
    ) -> list[str]:
        """Render the redesigned per-device inventory, grouped by device type."""
        lines: list[str] = ["# Device Inventory", ""]

        inventory = self._group_devices_by_type(project)
        for device_type, devices in sorted(
            inventory.items(),
            key=lambda item: self._plural_title(item[0]),
        ):
            lines.append(f"## {self._plural_title(device_type)}")
            lines.append("")
            lines.append(f"Total: {len(devices)}")
            lines.append("")
            lines.extend(self._render_section_manufacturers(devices))
            lines.append("---")
            lines.append("")
            for device in devices:
                lines.extend(self._render_device_section(device, classifier))

        return lines

    def _render_device_section(
        self,
        device: Device,
        classifier: DeviceClassifier,
    ) -> list[str]:
        """Render one device's Identity, Evidence, and Classification blocks."""
        lines: list[str] = []
        lines.append(
            f"### {self._display_title(device.hostname or device.ip_address or 'Unknown')}"
        )
        lines.append("")
        lines.extend(self._render_identity(device))
        lines.append("")
        lines.extend(self._render_evidence(device))
        lines.append("")
        lines.extend(self._render_classification(device, classifier))
        lines.append("")

        return lines

    def _render_identity(self, device: Device) -> list[str]:
        """Render the Identity block: always-shown facts first, then the
        three SMB/RDP-sourced fields only when present."""
        lines = ["**Identity**", ""]
        lines.append(f"- Device Type: {self._display_title(device.device_type)}")
        lines.append(f"- IP Address: {self._display_value(device.ip_address)}")
        lines.append(f"- Hostname: {self._display_value(device.hostname)}")
        if device.computer_name:
            lines.append(f"- Computer Name: {device.computer_name}")
        if device.operating_system:
            lines.append(f"- Operating System: {device.operating_system}")
        if device.domain:
            lines.append(f"- Domain: {device.domain}")
        lines.append(f"- Vendor: {self._display_value(device.vendor)}")
        lines.append(f"- MAC Address: {self._display_value(device.mac_address)}")
        lines.append(
            f"- Discovery Sources: {self._display_value(','.join(device.discovery_sources or []))}"
        )

        return lines

    def _render_evidence(self, device: Device) -> list[str]:
        """Render the Evidence block: per-service evidence grouped together
        (per ADR-009, HTTP/TLS/auth-realm evidence is correlated to a
        specific port, not device-wide), plus device-level SMB signing.
        Omits fields with no collected value rather than showing "Unknown"
        — an empty evidence line isn't evidence."""
        lines = ["**Evidence**", ""]
        has_content = False

        if device.services:
            has_content = True
            lines.append("Services:")
            for entry in device.services:
                lines.append(f"- {self._format_service_summary(entry)}")
                lines.extend(self._format_service_detail(entry))
            if device.smb_signing:
                lines.append("")

        if device.smb_signing:
            has_content = True
            lines.append(f"SMB Signing: {device.smb_signing}")

        if not has_content:
            lines.append("No additional evidence collected.")

        return lines

    def _format_service_summary(self, entry: ServiceEvidence) -> str:
        """Render one service's port/protocol/service/product/version line."""
        line = f"{entry.port}/{entry.protocol}"
        if entry.service:
            line += f" {entry.service}"
        if entry.product:
            product_display = entry.product
            if entry.version:
                product_display += f" {entry.version}"
            line += f" ({product_display})"

        return line

    def _format_service_detail(self, entry: ServiceEvidence) -> list[str]:
        """Render one service's identifier-tier evidence as indented sub-bullets."""
        lines: list[str] = []
        if entry.http_title:
            lines.append(f"  - HTTP Title: {entry.http_title}")
        if entry.tls_subject:
            lines.append(f"  - TLS Subject: {entry.tls_subject}")
        if entry.tls_issuer:
            lines.append(f"  - TLS Issuer: {entry.tls_issuer}")
        if entry.http_auth_realm:
            lines.append(f"  - HTTP Authentication Realm: {entry.http_auth_realm}")

        return lines

    def _render_classification(
        self,
        device: Device,
        classifier: DeviceClassifier,
    ) -> list[str]:
        """Render the Classification block: the single matching rule for a
        classified device (concise, per REPORT-001 — do not list every
        skipped rule), or every evaluated rule's reason for an UNKNOWN
        device (there is no single winner to report, so "why no rule
        matched" is the full breakdown)."""
        lines = ["**Classification**", ""]
        lines.append(f"Final Device Type: {self._display_title(device.device_type)}")
        lines.append("")

        rule_results, rule_names = self._evaluate_rules(device, classifier)

        if device.device_type == DeviceType.UNKNOWN:
            lines.append("No rule matched. Evaluated rules:")
            for rule_name, result in zip(rule_names, rule_results):
                lines.append(f"- {rule_name}: {result.reason}")
            return lines

        matching_rule_name, matching_result = self._matching_rule(rule_names, rule_results)
        if matching_result is not None:
            lines.append(f"Matching Rule: {matching_rule_name}")
            lines.append(f"Reason: {matching_result.reason}")

        return lines

    def _evaluate_rules(
        self,
        device: Device,
        classifier: DeviceClassifier,
    ) -> tuple[tuple[RuleResult, ...], list[str]]:
        """Classify a copy of the device and return the rule results and
        rule names evaluated for it, without mutating the original device
        or the project's stored classification."""
        classifier.classify(replace(device))
        rule_results = classifier.get_last_rule_results()
        rule_names = [rule.__class__.__name__ for rule in classifier._rules]

        return rule_results, rule_names[: len(rule_results)]

    def _matching_rule(
        self,
        rule_names: list[str],
        rule_results: tuple[RuleResult, ...],
    ) -> tuple[str | None, RuleResult | None]:
        """Return the name and result of the rule that matched, if any.

        DeviceClassifier is first-match-wins and stops evaluating as soon
        as a rule matches, so the last evaluated result is the matching
        one whenever the device isn't UNKNOWN.
        """
        if not rule_results:
            return None, None

        last_result = rule_results[-1]
        if not last_result.matched:
            return None, None

        return rule_names[-1], last_result

    # ------------------------------------------------------------------
    # Appendices (new, REPORT-001)
    # ------------------------------------------------------------------

    def _render_appendices(self, project: Project, summary: ProjectSummary) -> list[str]:
        """Render summary tables of already-known information: vendor
        counts, service counts, and discovery evidence coverage."""
        lines: list[str] = ["# Appendices", ""]

        lines.append("## Vendor Counts")
        lines.append("")
        if not summary.vendor_counts:
            lines.append("No vendor data collected.")
        else:
            for vendor, count in sorted(summary.vendor_counts.items()):
                lines.append(f"- {vendor}: {count}")
        lines.append("")

        all_devices = project.network_graph.all_devices()
        all_services = [entry for device in all_devices for entry in device.services]

        lines.append("## Service Counts")
        lines.append("")
        service_counts = Counter(
            entry.service for entry in all_services if entry.service
        )
        if not service_counts:
            lines.append("No service data collected.")
        else:
            for service, count in sorted(service_counts.items()):
                lines.append(f"- {service}: {count}")
        lines.append("")

        lines.append("## Discovery Evidence Coverage")
        lines.append("")
        total_devices = len(all_devices)
        total_services = len(all_services)
        device_field_counts = {
            "Operating System": sum(1 for d in all_devices if d.operating_system),
            "Computer Name": sum(1 for d in all_devices if d.computer_name),
            "Domain": sum(1 for d in all_devices if d.domain),
            "SMB Signing": sum(1 for d in all_devices if d.smb_signing),
            "MAC Address": sum(1 for d in all_devices if d.mac_address),
        }
        for label, count in device_field_counts.items():
            lines.append(f"- {label}: {count}/{total_devices} devices")

        service_field_counts = {
            "Product": sum(1 for e in all_services if e.product),
            "Version": sum(1 for e in all_services if e.version),
            "HTTP Title": sum(1 for e in all_services if e.http_title),
            "TLS Subject": sum(1 for e in all_services if e.tls_subject),
            "TLS Issuer": sum(1 for e in all_services if e.tls_issuer),
            "HTTP Authentication Realm": sum(1 for e in all_services if e.http_auth_realm),
        }
        for label, count in service_field_counts.items():
            lines.append(f"- {label}: {count}/{total_services} services")

        return lines

    # ------------------------------------------------------------------
    # Shared helpers (retained from the prior report)
    # ------------------------------------------------------------------

    def _group_devices_by_type(self, project: Project) -> dict[DeviceType, list[Device]]:
        """Group inventory devices by their device type for Markdown rendering."""
        grouped_devices: dict[DeviceType, list[Device]] = defaultdict(list)

        for device in sorted(
            project.network_graph.all_devices(),
            key=lambda device: (
                device.hostname or "",
                device.ip_address or "",
            ),
        ):
            grouped_devices[device.device_type].append(device)

        return grouped_devices

    def _render_section_manufacturers(self, devices: list[Device]) -> list[str]:
        """Render a section summary for manufacturer distribution in a device type group."""
        lines: list[str] = []
        manufacturer_counts = Counter(
            self._display_value(device.vendor) for device in devices
        )
        unique_manufacturers = set(manufacturer_counts)

        if len(unique_manufacturers) == 1:
            lines.append("Manufacturer")
            lines.append("")
            lines.append(f"{next(iter(unique_manufacturers))}")
            lines.append("")
            return lines

        lines.append("Manufacturers")
        lines.append("")
        for manufacturer, count in sorted(manufacturer_counts.items()):
            lines.append(f"- {manufacturer}: {count}")
        lines.append("")
        return lines

    def _display_value(self, value: object) -> str:
        """Return a user-friendly string for values that may be missing."""
        if value is None:
            return "Unknown"
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, str) and not value.strip():
            return "Unknown"
        return str(value)

    def _display_title(self, value: object) -> str:
        """Return a display-friendly title for headings and labels."""
        if value is None:
            return "Unknown"
        if isinstance(value, DeviceType):
            return value.value.replace("_", " ").title()
        if isinstance(value, str) and not value.strip():
            return "Unknown"
        return str(value)

    def _plural_title(self, value: object) -> str:
        """Return the pluralized heading form for a given device type."""
        if isinstance(value, DeviceType):
            device_title = self._display_title(value)
            return {
                "Server": "Servers",
                "Workstation": "Workstations",
                "Printer": "Printers",
                "Switch": "Switches",
                "Router": "Routers",
                "Firewall": "Firewalls",
                "Access Point": "Access Points",
                "Hypervisor": "Hypervisors",
                "Unknown": "Unknown",
            }.get(device_title, device_title)
        return self._display_title(value)

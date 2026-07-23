from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from networkmapper.classification.classifier import DeviceClassifier
from networkmapper.core.models import Device, DeviceType


@dataclass(frozen=True)
class BenchmarkMismatch:
    """Represent one classification mismatch in a benchmark run."""

    ip_address: str
    expected_device_type: str
    predicted_device_type: str


@dataclass(frozen=True)
class BenchmarkReport:
    """Represent aggregate classification accuracy for one benchmark run."""

    total_devices: int
    correct_classifications: int
    incorrect_classifications: int
    accuracy_percentage: float
    mismatches: tuple[BenchmarkMismatch, ...]


class BenchmarkRunner:
    """Run classification benchmarks against curated inventory datasets."""

    def __init__(self, classifier: DeviceClassifier | None = None) -> None:
        """Initialize a runner with an optional classifier instance."""
        self._classifier = classifier or DeviceClassifier()

    def load_inventory(self, inventory_path: str | Path) -> list[Device]:
        """Load benchmark inventory devices from a JSON file."""
        payload = self._load_json_file(inventory_path)
        device_payloads = payload.get("devices", [])

        devices: list[Device] = []
        for device_payload in device_payloads:
            devices.append(
                Device(
                    ip_address=device_payload["ip_address"],
                    hostname=device_payload.get("hostname"),
                    mac_address=device_payload.get("mac_address"),
                    vendor=device_payload.get("vendor"),
                    operating_system=device_payload.get("operating_system"),
                    open_ports=device_payload.get("open_ports", []),
                    detected_services=device_payload.get("detected_services", []),
                    device_type=DeviceType.UNKNOWN,
                    discovery_sources=device_payload.get("discovery_sources", []),
                )
            )

        return devices

    def load_expected_results(
        self,
        expected_results_path: str | Path,
    ) -> dict[str, DeviceType]:
        """Load expected device types keyed by IP address from JSON."""
        payload = self._load_json_file(expected_results_path)

        if "expected_results" in payload:
            expected_payloads = payload["expected_results"]
            expected_by_ip: dict[str, DeviceType] = {}
            for expected_payload in expected_payloads:
                ip_address = expected_payload["ip_address"]
                expected_type = self._parse_device_type(
                    expected_payload.get("device_type")
                    or expected_payload.get("expected_device_type")
                )
                expected_by_ip[ip_address] = expected_type
            return expected_by_ip

        expected_by_ip = {}
        for ip_address, device_type in payload.items():
            expected_by_ip[ip_address] = self._parse_device_type(device_type)

        return expected_by_ip

    def run_benchmark(
        self,
        inventory_path: str | Path,
        expected_results_path: str | Path,
    ) -> BenchmarkReport:
        """Run classification against one inventory and compute accuracy metrics."""
        devices = self.load_inventory(inventory_path)
        expected_by_ip = self.load_expected_results(expected_results_path)

        total_devices = len(devices)
        correct_classifications = 0
        mismatches: list[BenchmarkMismatch] = []

        for device in devices:
            predicted_type = self._classifier.classify(device).device_type
            expected_type = expected_by_ip.get(device.ip_address)

            if expected_type is not None and predicted_type == expected_type:
                correct_classifications += 1
                continue

            mismatches.append(
                BenchmarkMismatch(
                    ip_address=device.ip_address,
                    expected_device_type=expected_type.name if expected_type else "MISSING",
                    predicted_device_type=predicted_type.name,
                )
            )

        incorrect_classifications = total_devices - correct_classifications
        accuracy_percentage = (
            (correct_classifications / total_devices) * 100 if total_devices else 0.0
        )

        return BenchmarkReport(
            total_devices=total_devices,
            correct_classifications=correct_classifications,
            incorrect_classifications=incorrect_classifications,
            accuracy_percentage=accuracy_percentage,
            mismatches=tuple(mismatches),
        )

    def run_benchmark_directory(self, benchmark_dir: str | Path) -> BenchmarkReport:
        """Run a benchmark using the standard dataset file names in a directory."""
        benchmark_path = Path(benchmark_dir)
        return self.run_benchmark(
            inventory_path=benchmark_path / "inventory.json",
            expected_results_path=benchmark_path / "expected_results.json",
        )

    def _load_json_file(self, path: str | Path) -> dict[str, Any]:
        with Path(path).open("r", encoding="utf-8") as file_handle:
            payload: dict[str, Any] = json.load(file_handle)
        return payload

    def _parse_device_type(self, raw_device_type: Any) -> DeviceType:
        if not isinstance(raw_device_type, str):
            raise ValueError(f"Unsupported device type value: {raw_device_type!r}")

        normalized = raw_device_type.strip()
        try:
            return DeviceType(normalized.lower())
        except ValueError:
            try:
                return DeviceType[normalized.upper()]
            except KeyError as error:
                raise ValueError(
                    f"Unsupported device type value: {raw_device_type!r}"
                ) from error

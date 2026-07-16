from __future__ import annotations

from abc import ABC, abstractmethod

from networkmapper.core.models import Device, DeviceType


class ClassificationRule(ABC):
    """Define one deterministic classification rule for a discovered device."""

    @abstractmethod
    def classify(self, device: Device) -> DeviceType | None:
        """Return a device type when this rule matches, otherwise return None.

        Args:
            device: The device to evaluate.

        Returns:
            The inferred device type when the rule applies, or None when it
            does not match.
        """
        raise NotImplementedError

from __future__ import annotations

from abc import ABC, abstractmethod

from networkmapper.core.models import Device, DeviceType
from networkmapper.classification.rule_result import RuleResult


class ClassificationRule(ABC):
    """Define one deterministic classification rule for a discovered device."""

    @abstractmethod
    def classify(self, device: Device) -> DeviceType | RuleResult | None:
        """Return a rule outcome when this rule matches, otherwise return None.

        Args:
            device: The device to evaluate.

        Returns:
            The inferred device type or rule result when the rule applies, or
            None when it does not match.
        """
        raise NotImplementedError

from enum import StrEnum


class ScanProfile(StrEnum):
    """Supported scan-depth profiles for discovery providers."""

    FAST = "fast"
    STANDARD = "standard"
    DEEP = "deep"

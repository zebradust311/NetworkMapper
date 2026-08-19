"""Canonical identity resolution (ADR-012; ARCH-017 Stage 3; FEAT-008A).

Inert and unwired: nothing in the existing discovery, classification,
reporting, or persistence pipeline calls `IdentityResolver` yet.
"""

from networkmapper.identity.models import (
    CanonicalIdentity,
    IdentityCorroborationState,
    PropertyCorroboration,
)
from networkmapper.identity.resolver import IdentityResolver

__all__ = [
    "CanonicalIdentity",
    "IdentityCorroborationState",
    "IdentityResolver",
    "PropertyCorroboration",
]

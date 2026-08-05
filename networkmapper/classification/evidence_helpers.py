from __future__ import annotations

from collections.abc import Collection, Sequence

from networkmapper.core.models import ServiceEvidence


def service_ports(services: Sequence[ServiceEvidence]) -> list[int]:
    """Return the ports from a device's correlated service evidence, in order."""
    return [entry.port for entry in services]


def service_names(services: Sequence[ServiceEvidence]) -> list[str]:
    """Return the known service names from a device's correlated service evidence, in order."""
    return [entry.service for entry in services if entry.service]


def first_matching_product(
    services: Sequence[ServiceEvidence],
    candidate_keywords: Collection[str],
) -> str | None:
    """Return the first service product string containing any candidate keyword, if any.

    Unlike `first_matching_service`, this performs a substring search rather
    than exact membership, because Nmap product strings are free-text
    descriptions (e.g. "VMware ESXi Server httpd"), not fixed values.
    """
    return first_containing([entry.product for entry in services], candidate_keywords)


def service_http_titles(services: Sequence[ServiceEvidence]) -> list[str]:
    """Return the known HTTP page titles from a device's correlated service evidence, in order."""
    return [entry.http_title for entry in services if entry.http_title]


def service_tls_subjects(services: Sequence[ServiceEvidence]) -> list[str]:
    """Return the known TLS certificate subjects from a device's correlated service evidence, in order."""
    return [entry.tls_subject for entry in services if entry.tls_subject]


def service_tls_issuers(services: Sequence[ServiceEvidence]) -> list[str]:
    """Return the known TLS certificate issuers from a device's correlated service evidence, in order."""
    return [entry.tls_issuer for entry in services if entry.tls_issuer]


def service_http_auth_realms(services: Sequence[ServiceEvidence]) -> list[str]:
    """Return the known HTTP authentication realms from a device's correlated service evidence, in order."""
    return [entry.http_auth_realm for entry in services if entry.http_auth_realm]


def first_containing(
    values: Sequence[str | None],
    candidate_keywords: Collection[str],
) -> str | None:
    """Return the first non-empty value containing any candidate keyword (case-insensitive substring)."""
    for value in values:
        if not value:
            continue

        value_lower = value.lower()
        if any(keyword in value_lower for keyword in candidate_keywords):
            return value

    return None


def first_matching_identifier(
    services: Sequence[ServiceEvidence],
    candidate_keywords: Collection[str],
) -> tuple[str, str] | None:
    """Search product, HTTP title, TLS certificate subject/issuer, and HTTP
    authentication realm, in that order, for the first value containing any
    candidate keyword.

    Returns a (label, value) pair naming which evidence type matched, so
    callers can produce an accurate reason string instead of assuming the
    match came from a specific field.
    """
    checks = (
        ("service product", [entry.product for entry in services]),
        ("HTTP title", service_http_titles(services)),
        ("TLS certificate subject", service_tls_subjects(services)),
        ("TLS certificate issuer", service_tls_issuers(services)),
        ("HTTP authentication realm", service_http_auth_realms(services)),
    )
    for label, values in checks:
        match = first_containing(values, candidate_keywords)
        if match is not None:
            return label, match

    return None


def normalize_vendor(vendor: str | None, *, strip: bool = True) -> str:
    """Normalize vendor text for deterministic matching."""
    normalized = vendor or ""
    if strip:
        normalized = normalized.strip()
    return normalized.lower()


def normalize_hostname(hostname: str | None, *, strip: bool = False) -> str:
    """Normalize hostname text for deterministic matching."""
    normalized = hostname or ""
    if strip:
        normalized = normalized.strip()
    return normalized.lower()


def first_matching_port(
    open_ports: Sequence[int],
    candidate_ports: Collection[int],
) -> int | None:
    """Return the first matching port in input order, if any."""
    for port in open_ports:
        if port in candidate_ports:
            return port
    return None


def first_matching_service(
    detected_services: Sequence[str],
    candidate_services: Collection[str],
    *,
    strip: bool = True,
    return_lower: bool = False,
) -> str | None:
    """Return the first service matching known candidates in input order."""
    for service in detected_services:
        value = service.strip() if strip else service
        lowered = value.lower()
        if lowered in candidate_services:
            if return_lower:
                return lowered
            return value
    return None


def format_hostname_evidence_reason(
    raw_hostname: str | None,
    matched_port: int | None,
    matched_service: str | None,
    evidence_label: str,
) -> str:
    """Format a consistent hostname-plus-signal evidence reason string."""
    if matched_port is not None and matched_service is not None:
        return (
            f"Hostname {raw_hostname!r} with open port {matched_port} and "
            f"service {matched_service!r} matched known {evidence_label} evidence."
        )

    if matched_port is not None:
        return (
            f"Hostname {raw_hostname!r} with open port {matched_port} matched known "
            f"{evidence_label} evidence."
        )

    return (
        f"Hostname {raw_hostname!r} with service {matched_service!r} matched known "
        f"{evidence_label} evidence."
    )
"""Local IPv4 subnet auto-detection (PLAN-013A Revision 3).

Used by `Application` only when the operator supplies no `--subnet` value
at all. Reports exactly the IPv4 route/interface Windows itself would
select for an outbound connection, then derives that interface's subnet —
it makes no attempt to distinguish a physical adapter from a virtual one
(VPN, etc.), and enumerates no other interfaces. An operator who needs a
different subnet than the one detected here already has the complete
override: supplying `--subnet` explicitly bypasses this module entirely.
"""

from __future__ import annotations

import ipaddress
import socket
import subprocess
from dataclasses import dataclass
from typing import Callable

_PROBE_HOST = "8.8.8.8"
_PROBE_PORT = 80
_POWERSHELL_TIMEOUT_SECONDS = 5.0

SocketFactory = Callable[[], socket.socket]
PowerShellRunner = Callable[[str], str]


@dataclass(frozen=True)
class DetectedLocalSubnet:
    """The result of local IPv4 subnet auto-detection.

    Both fields are retained and surfaced to the operator — never just
    `subnet_cidr` — so a preferred VPN/virtual route being selected is
    visible before a scan begins. This type makes no claim that
    `source_address` belongs to a physical, preferred, or "expected"
    adapter; it is whatever address Windows' own routing table resolved.
    """

    source_address: str
    subnet_cidr: str


def _default_socket_factory() -> socket.socket:
    """Return a fresh UDP socket for the routing-table probe."""
    return socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


def _detect_active_ipv4_address(socket_factory: SocketFactory) -> str | None:
    """Return the IPv4 source address Windows would use to route to a
    fixed, arbitrary public destination, or None if no such route exists.

    Connecting a `SOCK_DGRAM` socket never transmits a packet — it only
    asks the OS kernel which local interface and source address its
    routing table would use for that destination, then binds the socket
    to it. This defers all interface/route selection to the OS: no
    adapter enumeration, ranking, or "is this physical/virtual" heuristic
    is attempted here. Whatever the kernel would actually use for
    outbound traffic is reported, faithfully, whether that turns out to
    be a physical LAN adapter or a VPN's virtual one.
    """
    try:
        sock = socket_factory()
    except OSError:
        # Socket creation itself failed — detection fails, never guesses.
        return None

    try:
        sock.connect((_PROBE_HOST, _PROBE_PORT))
        return sock.getsockname()[0]
    except OSError:
        # No usable outbound/default route exists (e.g. an isolated,
        # air-gapped host) — detection fails, never guesses.
        return None
    finally:
        sock.close()


def _reject_loopback_or_link_local(address: str) -> str | None:
    """Return `address` unchanged, or None if it is loopback or APIPA.

    Kept as explicit, cheap defense-in-depth even though the routing-table
    probe above should never surface either address in practice.
    """
    try:
        parsed = ipaddress.ip_address(address)
    except ValueError:
        return None

    if parsed.is_loopback or parsed.is_link_local:
        return None

    return address


def _run_get_net_ip_address(address: str) -> str:
    """Invoke PowerShell's `Get-NetIPAddress` for one already-known
    address and return its raw stdout (the bare `PrefixLength` value).

    `address` is a value this process just read back from its own
    socket's `getsockname()`, not external/operator input, so no
    shell-injection concern applies to the interpolated command string.
    Raises on any subprocess-level failure; callers treat any exception
    as detection failure, never a hang or an unhandled traceback.
    """
    completed = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            f"(Get-NetIPAddress -AddressFamily IPv4 -IPAddress '{address}' "
            f"-ErrorAction Stop).PrefixLength",
        ],
        capture_output=True,
        text=True,
        timeout=_POWERSHELL_TIMEOUT_SECONDS,
        check=True,
    )
    return completed.stdout


def _detect_prefix_length(
    address: str, powershell_runner: PowerShellRunner
) -> int | None:
    """Resolve `address`'s IPv4 prefix length, or None on any failure —
    PowerShell unavailable, the address no longer present, the cmdlet
    missing, a timeout, or non-integer output."""
    try:
        output = powershell_runner(address)
    except (subprocess.SubprocessError, OSError):
        return None

    try:
        return int(output.strip())
    except ValueError:
        return None


def detect_local_subnet(
    *,
    socket_factory: SocketFactory = _default_socket_factory,
    powershell_runner: PowerShellRunner = _run_get_net_ip_address,
) -> DetectedLocalSubnet | None:
    """Auto-detect the single active local IPv4 subnet.

    Returns `None` on any failure at any step — never a guessed or
    hard-coded network. `socket_factory`/`powershell_runner` are
    injection points for tests only; production callers use the defaults.
    """
    address = _detect_active_ipv4_address(socket_factory)
    if address is None:
        return None

    address = _reject_loopback_or_link_local(address)
    if address is None:
        return None

    prefix_length = _detect_prefix_length(address, powershell_runner)
    if prefix_length is None:
        return None

    try:
        network = ipaddress.ip_network(f"{address}/{prefix_length}", strict=False)
    except ValueError:
        return None

    return DetectedLocalSubnet(source_address=address, subnet_cidr=str(network))

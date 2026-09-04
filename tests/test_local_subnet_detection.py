import socket
import subprocess
import unittest

from networkmapper.discovery.local_subnet import DetectedLocalSubnet, detect_local_subnet


class _StubSocket:
    """A fake `socket.socket` for injecting a canned `getsockname()` result
    or a `connect()` failure, without any real network I/O."""

    def __init__(self, address: str | None = None, connect_error: OSError | None = None):
        self._address = address
        self._connect_error = connect_error
        self.closed = False

    def connect(self, destination):
        if self._connect_error is not None:
            raise self._connect_error

    def getsockname(self):
        return (self._address, 0)

    def close(self):
        self.closed = True


def _socket_factory(stub_socket: _StubSocket):
    return lambda: stub_socket


def _powershell_runner(output: str | None = None, error: Exception | None = None):
    def _runner(address: str) -> str:
        if error is not None:
            raise error
        return output

    return _runner


class LocalSubnetDetectionTest(unittest.TestCase):
    def test_detected_address_and_prefix_combine_into_a_canonical_cidr(self):
        result = detect_local_subnet(
            socket_factory=_socket_factory(_StubSocket(address="192.168.1.55")),
            powershell_runner=_powershell_runner(output="24"),
        )

        self.assertEqual(
            result, DetectedLocalSubnet(source_address="192.168.1.55", subnet_cidr="192.168.1.0/24")
        )

    def test_result_preserves_the_raw_source_address_distinct_from_the_derived_subnet(self):
        result = detect_local_subnet(
            socket_factory=_socket_factory(_StubSocket(address="10.0.0.200")),
            powershell_runner=_powershell_runner(output="8"),
        )

        self.assertEqual(result.source_address, "10.0.0.200")
        self.assertEqual(result.subnet_cidr, "10.0.0.0/8")
        self.assertNotEqual(result.source_address, result.subnet_cidr)

    def test_loopback_address_is_rejected(self):
        runner_calls: list[str] = []

        def _tracking_runner(address: str) -> str:
            runner_calls.append(address)
            return "8"

        result = detect_local_subnet(
            socket_factory=_socket_factory(_StubSocket(address="127.0.0.1")),
            powershell_runner=_tracking_runner,
        )

        self.assertIsNone(result)
        self.assertEqual(runner_calls, [])

    def test_apipa_address_is_rejected(self):
        runner_calls: list[str] = []

        def _tracking_runner(address: str) -> str:
            runner_calls.append(address)
            return "16"

        result = detect_local_subnet(
            socket_factory=_socket_factory(_StubSocket(address="169.254.10.5")),
            powershell_runner=_tracking_runner,
        )

        self.assertIsNone(result)
        self.assertEqual(runner_calls, [])

    def test_socket_failure_returns_none(self):
        # Models an isolated host with no usable outbound/default route.
        result = detect_local_subnet(
            socket_factory=_socket_factory(
                _StubSocket(connect_error=OSError("no route to host"))
            ),
            powershell_runner=_powershell_runner(output="24"),
        )

        self.assertIsNone(result)

    def test_socket_factory_failure_returns_none_without_raising(self):
        # socket_factory() itself (not connect()/getsockname()) raises —
        # this must not propagate, and no exception (e.g. NameError from
        # closing a never-created socket) should occur either.
        def _raising_socket_factory():
            raise OSError("could not allocate socket")

        try:
            result = detect_local_subnet(
                socket_factory=_raising_socket_factory,
                powershell_runner=_powershell_runner(output="24"),
            )
        except Exception as error:  # noqa: BLE001 - the point of this test
            self.fail(f"detect_local_subnet() raised {error!r} instead of returning None")

        self.assertIsNone(result)

    def test_powershell_failure_returns_none(self):
        result = detect_local_subnet(
            socket_factory=_socket_factory(_StubSocket(address="192.168.1.55")),
            powershell_runner=_powershell_runner(
                error=subprocess.CalledProcessError(1, "powershell.exe")
            ),
        )

        self.assertIsNone(result)

    def test_powershell_timeout_returns_none(self):
        result = detect_local_subnet(
            socket_factory=_socket_factory(_StubSocket(address="192.168.1.55")),
            powershell_runner=_powershell_runner(
                error=subprocess.TimeoutExpired("powershell.exe", 5.0)
            ),
        )

        self.assertIsNone(result)

    def test_powershell_not_found_returns_none(self):
        result = detect_local_subnet(
            socket_factory=_socket_factory(_StubSocket(address="192.168.1.55")),
            powershell_runner=_powershell_runner(
                error=FileNotFoundError("powershell.exe not found")
            ),
        )

        self.assertIsNone(result)

    def test_non_integer_prefix_length_output_returns_none(self):
        result = detect_local_subnet(
            socket_factory=_socket_factory(_StubSocket(address="192.168.1.55")),
            powershell_runner=_powershell_runner(output=""),
        )

        self.assertIsNone(result)

    def test_no_hard_coded_network_is_ever_returned_on_any_failure_path(self):
        failure_cases = [
            (
                _socket_factory(_StubSocket(connect_error=OSError("no route"))),
                _powershell_runner(output="24"),
            ),
            (
                _socket_factory(_StubSocket(address="127.0.0.1")),
                _powershell_runner(output="24"),
            ),
            (
                _socket_factory(_StubSocket(address="169.254.1.1")),
                _powershell_runner(output="24"),
            ),
            (
                _socket_factory(_StubSocket(address="192.168.1.55")),
                _powershell_runner(error=subprocess.CalledProcessError(1, "powershell.exe")),
            ),
            (
                _socket_factory(_StubSocket(address="192.168.1.55")),
                _powershell_runner(output="not-a-number"),
            ),
        ]

        for socket_factory, powershell_runner in failure_cases:
            with self.subTest(powershell_runner=powershell_runner):
                result = detect_local_subnet(
                    socket_factory=socket_factory, powershell_runner=powershell_runner
                )
                self.assertIsNone(result)

    def test_a_vpn_or_virtual_adapter_address_is_returned_without_special_casing(self):
        # No attempt is made to distinguish a physical adapter from a
        # virtual/VPN one (PLAN-013A Section 1.4's corrected contract) —
        # whatever address the routing probe finds is reported as-is.
        result = detect_local_subnet(
            socket_factory=_socket_factory(_StubSocket(address="10.8.0.6")),
            powershell_runner=_powershell_runner(output="24"),
        )

        self.assertEqual(
            result, DetectedLocalSubnet(source_address="10.8.0.6", subnet_cidr="10.8.0.0/24")
        )

    def test_default_socket_factory_creates_a_udp_socket(self):
        # Confirms the production default wires up AF_INET/SOCK_DGRAM,
        # without performing any real connection.
        from networkmapper.discovery.local_subnet import _default_socket_factory

        sock = _default_socket_factory()
        try:
            self.assertEqual(sock.family, socket.AF_INET)
            self.assertEqual(sock.type, socket.SOCK_DGRAM)
        finally:
            sock.close()


if __name__ == "__main__":
    unittest.main()

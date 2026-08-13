import unittest

from networkmapper.discovery.snmp_credentials import SnmpCredentials, SnmpVersion


class SnmpCredentialsTest(unittest.TestCase):
    def test_repr_never_includes_the_community_string(self):
        credentials = SnmpCredentials(version=SnmpVersion.V2C, community="s3cr3t-community")

        self.assertNotIn("s3cr3t-community", repr(credentials))

    def test_repr_includes_the_version(self):
        credentials = SnmpCredentials(version=SnmpVersion.V2C, community="public")

        self.assertIn("v2c", repr(credentials))


if __name__ == "__main__":
    unittest.main()

"""Smoke test for package imports."""
import unittest


class TestImports(unittest.TestCase):
    """Test that the package can be imported without errors."""

    def test_import_protocol(self):
        """Test importing the main protocol class."""
        from hivemind_player_protocol import HiveMindPlayerProtocol
        self.assertIsNotNone(HiveMindPlayerProtocol)

    def test_import_version(self):
        """Test importing version constants."""
        from hivemind_player_protocol.version import (
            VERSION_MAJOR,
            VERSION_MINOR,
            VERSION_BUILD,
            VERSION_ALPHA
        )
        self.assertIsNotNone(VERSION_MAJOR)
        self.assertIsNotNone(VERSION_MINOR)
        self.assertIsNotNone(VERSION_BUILD)
        self.assertIsNotNone(VERSION_ALPHA)


if __name__ == '__main__':
    unittest.main()

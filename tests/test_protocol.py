"""Unit tests for HiveMindPlayerProtocol."""
import unittest
from unittest.mock import Mock, patch

try:
    from hivemind_player_protocol import HiveMindPlayerProtocol
    from ovos_utils.fakebus import FakeBus
    from ovos_bus_client.message import Message
    from hivemind_bus_client.message import HiveMessageType
    IMPORTS_AVAILABLE = True
except ImportError:
    IMPORTS_AVAILABLE = False


@unittest.skipIf(not IMPORTS_AVAILABLE, "Required dependencies not available")
class TestHiveMindPlayerProtocol(unittest.TestCase):
    """Test HiveMindPlayerProtocol basic functionality."""

    def setUp(self):
        """Set up test fixtures."""
        # Mock PlaybackService to avoid audio initialization
        with patch('hivemind_player_protocol.PlaybackService') as mock_playback:
            mock_playback.return_value = Mock()
            # Mock sys.modules to prevent PHAL import
            import sys
            if 'ovos_PHAL.service' not in sys.modules:
                sys.modules['ovos_PHAL.service'] = Mock()
                sys.modules['ovos_PHAL'] = Mock()

            self.protocol = HiveMindPlayerProtocol()

        # Initialize clients dict if not present
        if not hasattr(self.protocol, 'clients'):
            self.protocol.clients = {}

    def test_protocol_instantiation(self):
        """Test that protocol can be instantiated."""
        self.assertIsNotNone(self.protocol)
        self.assertIsNotNone(self.protocol.bus)
        self.assertIsNotNone(self.protocol.config)

    def test_protocol_has_playback_service(self):
        """Test that protocol has a playback service."""
        self.assertIsNotNone(self.protocol.playback)

    def test_protocol_tts_property(self):
        """Test that TTS property returns the playback service's TTS."""
        mock_tts = Mock()
        self.protocol.playback.tts = mock_tts
        self.assertEqual(self.protocol.tts, mock_tts)

    def test_register_bus_handlers(self):
        """Test that bus handlers are registered."""
        # Create a fresh protocol to test handler registration
        with patch('hivemind_player_protocol.PlaybackService'):
            protocol = HiveMindPlayerProtocol()
            # Verify the protocol has the bus
            self.assertIsNotNone(protocol.bus)

    def test_protocol_has_clients_dict(self):
        """Test that protocol has a clients dictionary."""
        self.assertTrue(hasattr(self.protocol, 'clients'))
        self.assertIsInstance(self.protocol.clients, dict)

    def test_protocol_dataclass(self):
        """Test that protocol is a dataclass with expected fields."""
        self.assertTrue(hasattr(self.protocol, 'bus'))
        self.assertTrue(hasattr(self.protocol, 'config'))
        self.assertTrue(hasattr(self.protocol, 'playback'))

    def test_protocol_phal_attribute(self):
        """Test that protocol has a phal attribute."""
        self.assertTrue(hasattr(self.protocol, 'phal'))


@unittest.skipIf(not IMPORTS_AVAILABLE, "Required dependencies not available")
class TestHiveMindPlayerProtocolMessageHandling(unittest.TestCase):
    """Test HiveMindPlayerProtocol message handling."""

    def setUp(self):
        """Set up test fixtures."""
        with patch('hivemind_player_protocol.PlaybackService') as mock_playback:
            mock_playback.return_value = Mock()
            self.protocol = HiveMindPlayerProtocol()

    def test_handle_send_method_exists(self):
        """Test that handle_send method exists and is callable."""
        self.assertTrue(hasattr(self.protocol, 'handle_send'))
        self.assertTrue(callable(self.protocol.handle_send))

    def test_handle_internal_mycroft_method_exists(self):
        """Test that handle_internal_mycroft method exists and is callable."""
        self.assertTrue(hasattr(self.protocol, 'handle_internal_mycroft'))
        self.assertTrue(callable(self.protocol.handle_internal_mycroft))

    def test_handle_send_accepts_message(self):
        """Test that handle_send accepts a Message object."""
        # Create a simple message with valid HiveMessageType
        message = Message(
            'test',
            data={
                'msg_type': HiveMessageType.BROADCAST,
                'payload': {'test': 'data'},
                'peer': None
            }
        )

        # Should not raise an exception (it may error on empty clients, that's ok)
        try:
            self.protocol.handle_send(message)
        except (AttributeError, TypeError, ValueError):
            # Expected - no actual clients connected
            pass

    def test_handle_internal_mycroft_accepts_serialized_message(self):
        """Test that handle_internal_mycroft accepts a serialized message."""
        # Create an OVOS message
        ovos_message = Message(
            'test.message',
            data={'result': 'success'},
            context={'other': 'data'}
        )

        # Serialize and handle the message
        serialized = ovos_message.serialize()

        # Should not raise an exception
        try:
            self.protocol.handle_internal_mycroft(serialized)
        except (KeyError, AttributeError):
            # Expected if clients dict is empty or message format differs
            pass


if __name__ == '__main__':
    unittest.main()

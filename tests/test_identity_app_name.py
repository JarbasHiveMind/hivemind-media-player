"""The identity is this application's own (HIVEMIND-CRYPTO-1 §2).

Before this change the entry point called ``NodeIdentity()`` and shared
``~/.config/hivemind/_identity.json`` with every other HiveMind application of
the user, so a satellite, a bridge and the CLI on one account presented one
identifier and one static key. The application now names itself, and hands that identity to the client:
without ``identity=`` the client builds ``NodeIdentity()`` itself and presents
the shared Noise and RSA keys under this application's access key.
"""
from unittest.mock import MagicMock, patch

import pytest

APP_NAME = "media-player"


def _identity():
    identity = MagicMock()
    identity.password = "correct-horse-battery-staple-92"
    identity.access_key = "sat-key"
    identity.site_id = "site"
    identity.default_master = "ws://hub"
    identity.default_port = 5678
    return identity


class _Stop(Exception):
    """Raised by the patched client's connect(): the run ends right after
    the client is built, which is all these tests look at."""


def _load_script():
    import importlib.util, os
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "hivemind-player-ctl.py")
    spec = importlib.util.spec_from_file_location("hivemind_player_ctl", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_player_asks_for_its_own_identity_and_hands_it_to_the_client():
    entry = _load_script()
    identity = _identity()
    with patch.object(entry, "NodeIdentity", return_value=identity) as ctor, \
         patch.object(entry, "HiveMessageBusClient") as client:
        node = entry.get_client("", "", "", 0)
    ctor.assert_called_once_with(app_name=APP_NAME)
    assert node is client.return_value
    assert client.call_args.kwargs.get("identity") is identity, (
        "the client was built without the application's identity")

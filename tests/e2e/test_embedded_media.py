"""End-to-end test for the embedded ovos-media daemon via hivescope.

Complements ``test_media_player.py`` (which disables ovos-media and asserts
the remote-control *routing*). Here ovos-media is left enabled, so the plugin
boots a real ``MediaService`` on its internal bus, with zero backend plugins
installed (it logs warnings for that — expected, no audio device or network
is ever touched).

Two things are proven separately, on purpose:

* ``ovos.common_play.ping`` / ``ovos.common_play.pong`` (see
  ``ovos_media/bus/api.py``'s ``_ServiceTopics``) is registered UNGATED —
  it answers regardless of session, so it only proves the daemon booted and
  is reachable through hivemind-core's ACL and this plugin's reverse-routing.
  It says nothing about ``validate_source``.
* ``ovos.common_play.pause`` IS a gated topic (``gated=True`` in the same
  table): ovos-media only acts on it when the message's session is the
  local/"default" one, or when ``validate_source=False``. Per
  HIVEMIND-BRIDGE-1 §4, hivemind-core namespaces a satellite's session to a
  per-connection id, never to "default", so a satellite's ``pause`` reaching
  the embedded player at all is the load-bearing proof that
  ``validate_source=False`` is doing something.
"""
import threading

import pytest
from ovos_bus_client.message import Message
from ovos_utils.ocp import PlayerState

from hivescope.topology import TopologyBuilder

from hivemind_player_protocol import HiveMindPlayerProtocol

PING = "ovos.common_play.ping"
PONG = "ovos.common_play.pong"
PAUSE = "ovos.common_play.pause"
PLAYER_STATE = "ovos.common_play.player.state"


@pytest.fixture
def embedded_media_topology():
    """A started single-satellite topology whose master runs the real
    HiveMindPlayerProtocol with ovos-media ENABLED (no ``disable_media``)."""
    builder = TopologyBuilder()
    player = HiveMindPlayerProtocol()
    master = builder.add_master("M0", agent_protocol=player)
    builder.add_satellite("S0", upstream=master,
                           allowed_types=[PING, PONG, PAUSE])
    builder.start_all()
    try:
        yield builder, player
    finally:
        player.media.shutdown()
        builder.stop_all()


def test_embedded_media_service_is_started(embedded_media_topology):
    """The plugin embeds a real, running MediaService on its own bus."""
    from ovos_media.service import MediaService

    _, player = embedded_media_topology
    assert isinstance(player.media, MediaService)
    # ``run()`` finishes fast (setup happens in ``__init__``); readiness is
    # tracked via ``status``, not thread liveness.
    assert player.media.status.check_ready()


def test_satellite_ping_reaches_embedded_media(embedded_media_topology):
    """A satellite reaches the embedded MediaService and gets a real pong
    back, round-tripped through hivemind-core's ACL and this plugin's
    reverse-routing. ``ping`` is ungated, so this proves boot/liveness and
    routing only — not session validation (see ``test_satellite_pause_is_processed_by_embedded_media``)."""
    builder, player = embedded_media_topology
    satellite = builder.get_satellite("S0")

    got = threading.Event()
    replies = []

    def _on_pong(msg):
        replies.append(msg)
        got.set()

    satellite.internal_bus.on(PONG, _on_pong)

    satellite.send(Message(PING, {}))

    assert got.wait(timeout=10), (
        f"satellite never received '{PONG}' from the embedded MediaService"
    )
    assert replies[0].msg_type == PONG


def test_satellite_pause_is_processed_by_embedded_media(embedded_media_topology):
    """A GATED topic (``ovos.common_play.pause``) sent by a satellite is
    actually processed by the embedded player, proving ``validate_source=False``
    is load-bearing: the satellite's session is namespaced, never "default"
    (HIVEMIND-BRIDGE-1 §4), so this would be silently dropped by ovos-media's
    session gate otherwise."""
    builder, player = embedded_media_topology
    satellite = builder.get_satellite("S0")

    got = threading.Event()
    states = []

    def _on_state(msg):
        states.append(msg.data.get("state"))
        got.set()

    player.bus.on(PLAYER_STATE, _on_state)

    satellite.send(Message(PAUSE, {}))

    assert got.wait(timeout=10), (
        f"embedded MediaService never processed the satellite's '{PAUSE}' "
        f"command ('{PLAYER_STATE}' was never emitted)"
    )
    assert states[0] == PlayerState.PAUSED

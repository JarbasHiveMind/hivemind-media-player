"""End-to-end tests for HiveMindPlayerProtocol via hivescope.

These tests wire the real ``HiveMindPlayerProtocol`` (the OCP/media agent
protocol plugin) as a hivescope master's ``agent_protocol`` and drive it
through a fully simulated, in-process HiveMind topology: a satellite connects,
completes the handshake, and exchanges OCP/media bus messages with the master.

What is exercised end-to-end:

* **Forward path** — a satellite sends an OCP command (``ovos.common_play.*``)
  as a HiveMind ``BUS`` message. hivemind-core's deny-by-default ACL admits it
  (the satellite is granted ``allowed_types``), and the master injects it onto
  the plugin's internal OVOS bus, where the plugin's ``PlaybackService``/OCP
  stack is listening.
* **Reverse path** — a media message emitted on the plugin's internal OVOS bus
  with ``destination == [satellite_peer]`` is forwarded back to that satellite
  by the plugin's ``handle_internal_mycroft`` routing, wrapped as a ``BUS``
  HiveMessage. This is the client-isolation seam.
* **ACL** — a satellite that was *not* granted an OCP message type has its
  command denied by hivemind-core and it never reaches the agent bus.

The plugin boots a real ``PlaybackService`` (OCP) on a ``FakeBus`` in
``__post_init__`` — no audio backend is required for these routing assertions.

hivescope is a required ``test`` dependency (see pyproject ``[test]`` extra);
it is never optional/importorskip'd here.
"""
import threading

import pytest
from ovos_bus_client.message import Message
from hivemind_bus_client.message import HiveMessage, HiveMessageType

from hivescope.topology import TopologyBuilder
from hivescope.assertions import assert_bus_message_routed

from hivemind_player_protocol import HiveMindPlayerProtocol


# OCP / media-player message types the satellite is allowed to send.
# Mirrors docs/permissions.md (the types granted via `hivemind-core allow-msg`).
OCP_PLAY = "ovos.common_play.play"
OCP_PAUSE = "ovos.common_play.pause"
OCP_STATUS = "ovos.common_play.player.status"

ALLOWED_OCP_TYPES = [OCP_PLAY, OCP_PAUSE, OCP_STATUS]


@pytest.fixture
def media_topology():
    """A started single-satellite topology whose master runs the real
    HiveMindPlayerProtocol as its agent protocol.

    The satellite is granted the OCP message types in ``ALLOWED_OCP_TYPES``
    (hivemind-core is deny-by-default whitelist-only, so without this grant the
    agent would never be invoked).
    """
    builder = TopologyBuilder()
    # The plugin instantiates PlaybackService/OCP on its FakeBus here.
    player = HiveMindPlayerProtocol()
    master = builder.add_master("M0", agent_protocol=player)
    builder.add_satellite("S0", upstream=master, allowed_types=list(ALLOWED_OCP_TYPES))
    builder.start_all()
    try:
        yield builder, player
    finally:
        builder.stop_all()


def _bus_messages_to_agent(master, ovos_type):
    """OCP messages of ``ovos_type`` that reached the master's agent bus.

    hivescope records every authorized inject via the ``bus_inject`` direction
    (see ``_instrument_master``), where the payload is the OVOS Message.
    """
    return [
        r for r in master.recorder.records
        if r.direction == "bus_inject" and r.msg_type == ovos_type
    ]


def test_satellite_ocp_command_reaches_media_player(media_topology):
    """A satellite OCP 'play' command routes through the master and lands on
    the media-player plugin's internal OVOS bus."""
    builder, player = media_topology
    master = builder.get_master("M0")
    satellite = builder.get_satellite("S0")

    # Capture the message as the plugin's own PlaybackService bus sees it.
    received = []
    player.bus.on(OCP_PLAY, lambda m: received.append(m))

    satellite.send(Message(
        OCP_PLAY,
        {"media": {"uri": "file:///tmp/song.mp3", "playback": 2}},
    ))

    # The HiveMind BUS message reached the master...
    assert_bus_message_routed(master, count=1)

    # ...and was injected onto the plugin's agent (OVOS) bus.
    injected = _bus_messages_to_agent(master, OCP_PLAY)
    assert injected, (
        f"OCP '{OCP_PLAY}' was not injected onto the media-player agent bus. "
        f"All injects: {[r.msg_type for r in master.recorder.records if r.direction == 'bus_inject']}"
    )

    # The plugin's own PlaybackService bus actually fired the OCP handler chain.
    assert received, f"PlaybackService bus never received '{OCP_PLAY}'"


def test_unauthorized_ocp_command_is_denied(media_topology):
    """An OCP type the satellite was NOT granted is denied by hivemind-core's
    deny-by-default ACL and never reaches the media-player plugin's bus handlers.

    Note: hivescope records a ``bus_inject`` on every *attempt* (before the ACL
    check), so the meaningful signal is that the plugin's own OVOS bus never
    fired the handler and the satellite received a ``hive.policy.denied``.
    """
    builder, player = media_topology
    master = builder.get_master("M0")
    satellite = builder.get_satellite("S0")

    not_granted = "ovos.common_play.next"  # deliberately absent from ALLOWED_OCP_TYPES
    assert not_granted not in ALLOWED_OCP_TYPES

    fired = []
    player.bus.on(not_granted, lambda m: fired.append(m))

    denied = threading.Event()
    satellite.internal_bus.on("hive.policy.denied", lambda m: denied.set())

    satellite.send(Message(not_granted, {}))

    # The ACL blocked it: the plugin's PlaybackService bus never saw the command.
    assert not fired, (
        f"Unauthorized OCP '{not_granted}' should have been denied but hit the media-player bus"
    )
    # And hivemind-core informed the satellite of the denial. The denial
    # notification is delivered asynchronously over the simulated topology, so
    # allow a generous timeout — loaded CI runners are much slower than a local
    # box (where this arrives in well under a second).
    assert denied.wait(timeout=30), (
        "satellite never received 'hive.policy.denied' for the unauthorized OCP command"
    )


def test_media_response_routes_back_to_satellite(media_topology):
    """A media bus message emitted on the plugin's OVOS bus with the satellite
    as its destination is forwarded back to that satellite as a BUS HiveMessage
    (the plugin's client-isolation reverse-routing seam)."""
    builder, player = media_topology
    master = builder.get_master("M0")
    satellite = builder.get_satellite("S0")

    peer = satellite.peer
    assert peer is not None, "satellite is not connected"

    # Satellite should receive the wrapped BUS HiveMessage on its internal bus.
    got = threading.Event()
    received = []

    def _on_status(msg):
        received.append(msg)
        got.set()

    satellite.internal_bus.on(OCP_STATUS, _on_status)

    # Simulate OCP emitting a player-status update targeted at this satellite,
    # exactly as ovos-audio would after a play command.
    status = Message(
        OCP_STATUS,
        {"status": 20, "track": "song.mp3"},
        {"destination": [peer]},
    )
    player.bus.emit(status)

    assert got.wait(timeout=30), (
        f"satellite never received '{OCP_STATUS}' routed back from the media player. "
        f"Inbound at satellite: {[r.msg_type for r in satellite.recorder.records if r.direction == 'in']}"
    )
    assert received[0].data.get("status") == 20

    # And at the HiveMind layer it arrived wrapped as a BUS message.
    inbound_bus = [
        r for r in satellite.recorder.records
        if r.direction == "in" and r.msg_type == HiveMessageType.BUS.value
    ]
    assert inbound_bus, "expected a BUS HiveMessage delivered to the satellite"


def test_media_response_isolated_from_other_satellites(media_topology):
    """Client isolation: a media message destined for one satellite is not
    delivered to a second, unrelated satellite."""
    builder, player = media_topology
    master = builder.get_master("M0")
    s0 = builder.get_satellite("S0")

    # Add a second satellite to the same master, also OCP-allowed.
    builder.add_satellite("S1", upstream=master, allowed_types=list(ALLOWED_OCP_TYPES))
    # add_satellite only queues the connection; wire it up now.
    s1 = builder.get_satellite("S1")
    s1.connect(master, allowed_types=list(ALLOWED_OCP_TYPES))

    target_peer = s0.peer
    other_peer = s1.peer
    assert target_peer and other_peer and target_peer != other_peer

    s0_hit = threading.Event()
    s1.internal_bus.on(OCP_STATUS, lambda m: pytest.fail("S1 must not receive S0's media message"))
    s0.internal_bus.on(OCP_STATUS, lambda m: s0_hit.set())

    player.bus.emit(Message(
        OCP_STATUS,
        {"status": 20},
        {"destination": [target_peer]},
    ))

    assert s0_hit.wait(timeout=30), "target satellite S0 should have received the media message"

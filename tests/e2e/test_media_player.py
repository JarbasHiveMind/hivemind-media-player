"""End-to-end tests for HiveMindPlayerProtocol via hivescope.

These tests wire the real ``HiveMindPlayerProtocol`` (the OCP/media agent
protocol plugin) as a hivescope master's ``agent_protocol`` and drive it
through a fully simulated, in-process HiveMind topology: a satellite connects,
completes the handshake, and exchanges OCP/media bus messages with the master
over a real ``HiveMessageBusClient``.

The whole stack is real **except the media playback backend**:

* **hivemind-core** runs in-process as the master (real ACL, real
  policy-admission chain, real client isolation).
* The **player plugin** boots a real ``ovos-audio`` ``PlaybackService`` on its
  internal OVOS bus, used only for its TTS engine, and routes messages
  to/from satellites for real.
* The **ovos-media backend is disabled** (``disable_media=True``), so *no
  real media backend plugin (mpv/vlc/…) is ever loaded* and nothing touches
  an audio device or the network. A lightweight recorder is registered on
  the plugin's bus in place of the media daemon, so the remote ``play`` /
  ``pause`` / ``stop`` control verbs are captured and asserted instead of
  producing sound. This keeps the tests about *remote-control routing* — the
  only thing the satellite path is responsible for. A real embedded
  ovos-media daemon is exercised separately in ``test_embedded_media.py``.

What is exercised end-to-end:

* **Forward / control path** — a satellite sends OCP control commands
  (``ovos.common_play.{play,pause,stop}``) as HiveMind ``BUS`` messages.
  hivemind-core's deny-by-default ACL admits them (the satellite is granted
  ``allowed_types``), and the master injects them onto the plugin's internal
  OVOS bus, where the mocked playback backend records them.
* **Reverse path** — a media message emitted on the plugin's internal OVOS bus
  with ``destination == [satellite_peer]`` is forwarded back to that satellite
  by the plugin's ``handle_internal_mycroft`` routing, wrapped as a ``BUS``
  HiveMessage. This is the client-isolation seam.
* **ACL** — a satellite that was *not* granted an OCP message type has its
  command denied by hivemind-core and it never reaches the agent bus.

hivescope + hivemind-core are required ``e2e``/``test`` dependencies (see the
pyproject ``[e2e]`` extra); they are never optional/importorskip'd here.
"""
import threading
import time

import pytest
from ovos_bus_client.message import Message
from hivemind_bus_client.message import HiveMessageType

from hivescope.topology import TopologyBuilder
from hivescope.assertions import assert_bus_message_routed

from hivemind_player_protocol import HiveMindPlayerProtocol


# OCP / media-player remote-control message types the satellite is allowed to
# send. Mirrors docs/permissions.md (the types granted via `hivemind-core
# allow-msg`).
OCP_PLAY = "ovos.common_play.play"
OCP_PAUSE = "ovos.common_play.pause"
OCP_STOP = "ovos.common_play.stop"
OCP_STATUS = "ovos.common_play.status"

# every control verb the satellite drives, plus the status channel used for the
# reverse (player -> satellite) path.
ALLOWED_OCP_TYPES = [OCP_PLAY, OCP_PAUSE, OCP_STOP, OCP_STATUS]


class MockOCPBackend:
    """Stand-in for the OCP / audio playback backend.

    Registered directly on the plugin's internal OVOS bus, it records the
    remote-control commands that reach the player instead of loading a real
    audio plugin or producing any sound. This is what makes the suite safe to
    run headless in CI: the real routing is exercised, the playback is faked.
    """

    def __init__(self, bus):
        self.events = []  # list[(msg_type, data)]
        self._lock = threading.Lock()
        for mtype in (OCP_PLAY, OCP_PAUSE, OCP_STOP):
            bus.on(mtype, self._record)

    def _record(self, message):
        with self._lock:
            self.events.append((message.msg_type, message.data))

    def types_seen(self):
        with self._lock:
            return [t for t, _ in self.events]

    def wait_for(self, msg_type, timeout=10):
        """Block until ``msg_type`` has been recorded (the command is delivered
        async over the simulated topology)."""
        start = time.monotonic()
        while time.monotonic() - start < timeout:
            if msg_type in self.types_seen():
                return True
            time.sleep(0.05)
        return msg_type in self.types_seen()


@pytest.fixture
def media_topology():
    """A started single-satellite topology whose master runs the real
    HiveMindPlayerProtocol as its agent protocol, with the OCP/audio backend
    mocked out.

    The satellite is granted the OCP message types in ``ALLOWED_OCP_TYPES``
    (hivemind-core is deny-by-default whitelist-only, so without this grant the
    agent would never be invoked).
    """
    builder = TopologyBuilder()
    # Boot the real plugin but with no embedded ovos-media, so no media
    # backend plugin is ever loaded.
    player = HiveMindPlayerProtocol(disable_media=True)
    # Swap in the recording backend on the plugin's own internal bus.
    backend = MockOCPBackend(player.bus)
    master = builder.add_master("M0", agent_protocol=player)
    builder.add_satellite("S0", upstream=master, allowed_types=list(ALLOWED_OCP_TYPES))
    builder.start_all()
    try:
        yield builder, player, backend
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


def test_satellite_play_command_reaches_media_player(media_topology):
    """A satellite OCP 'play' command routes through the master and lands on
    the media-player plugin's (mocked) playback backend."""
    builder, player, backend = media_topology
    master = builder.get_master("M0")
    satellite = builder.get_satellite("S0")

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

    # The mocked playback backend actually received the play command (no real
    # audio plugin was loaded, so this is a pure routing assertion).
    assert backend.wait_for(OCP_PLAY), (
        f"playback backend never received '{OCP_PLAY}'; saw {backend.types_seen()}"
    )


def test_play_pause_stop_round_trip(media_topology):
    """The full remote-control verb set (play -> pause -> stop) round-trips
    from the satellite, through hivemind-core's ACL, to the mocked playback
    backend in order."""
    builder, player, backend = media_topology
    satellite = builder.get_satellite("S0")

    satellite.send(Message(OCP_PLAY, {"media": {"uri": "file:///tmp/song.mp3"}}))
    assert backend.wait_for(OCP_PLAY), f"play not delivered; saw {backend.types_seen()}"

    satellite.send(Message(OCP_PAUSE, {}))
    assert backend.wait_for(OCP_PAUSE), f"pause not delivered; saw {backend.types_seen()}"

    satellite.send(Message(OCP_STOP, {}))
    assert backend.wait_for(OCP_STOP), f"stop not delivered; saw {backend.types_seen()}"

    # the three control verbs arrived, in command order.
    seen = [t for t in backend.types_seen() if t in (OCP_PLAY, OCP_PAUSE, OCP_STOP)]
    assert seen == [OCP_PLAY, OCP_PAUSE, OCP_STOP], (
        f"control verbs out of order or missing: {seen}"
    )


def test_unauthorized_ocp_command_is_denied(media_topology):
    """An OCP type the satellite was NOT granted is denied by hivemind-core's
    deny-by-default ACL and never reaches the media-player plugin's backend.

    Note: hivescope records a ``bus_inject`` on every *attempt* (before the ACL
    check), so the meaningful signal is that the plugin's own OVOS bus never
    fired the handler and the satellite received a ``hive.policy.denied``.
    """
    builder, player, backend = media_topology
    satellite = builder.get_satellite("S0")

    not_granted = "ovos.common_play.next"  # deliberately absent from ALLOWED_OCP_TYPES
    assert not_granted not in ALLOWED_OCP_TYPES

    fired = []
    player.bus.on(not_granted, lambda m: fired.append(m))

    denied = threading.Event()
    satellite.internal_bus.on("hive.policy.denied", lambda m: denied.set())

    satellite.send(Message(not_granted, {}))

    # The ACL blocked it: the plugin's bus never saw the command.
    assert not fired, (
        f"Unauthorized OCP '{not_granted}' should have been denied but hit the media-player bus"
    )
    # And hivemind-core informed the satellite of the denial (the
    # policy-admission chain emits hive.policy.denied; requires hivemind-core
    # >=4.6, pinned in the e2e extra). Delivered async over the simulated
    # topology, so allow a little headroom.
    assert denied.wait(timeout=10), (
        "satellite never received 'hive.policy.denied' for the unauthorized OCP command"
    )


def test_media_response_routes_back_to_satellite(media_topology):
    """A media bus message emitted on the plugin's OVOS bus with the satellite
    as its destination is forwarded back to that satellite as a BUS HiveMessage
    (the plugin's client-isolation reverse-routing seam)."""
    builder, player, backend = media_topology
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

    assert got.wait(timeout=10), (
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
    builder, player, backend = media_topology
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

    assert s0_hit.wait(timeout=10), "target satellite S0 should have received the media message"

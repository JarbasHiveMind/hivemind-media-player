import dataclasses
from typing import Dict, Any, Optional

from hivemind_bus_client.message import HiveMessage, HiveMessageType
from hivemind_core.protocol import AgentProtocol
from ovos_audio.service import PlaybackService
from ovos_bus_client.message import Message
from ovos_config import Configuration
from ovos_media.service import MediaService
from ovos_plugin_manager.tts import TTS
from ovos_utils.fakebus import FakeBus
from ovos_utils.log import LOG


@dataclasses.dataclass()
class HiveMindPlayerProtocol(AgentProtocol):
    bus: FakeBus = dataclasses.field(default_factory=FakeBus)
    # hivemind-core's AgentProtocolFactory passes the plugin's own sub-block
    # of server.json's ``agent_protocol`` section here (see
    # ``hivemind_core.service.get_agent_protocol``); the empty-dict default
    # only applies to standalone construction (tests, scripts), never to a
    # hivemind-core-managed instance.
    config: Dict[str, Any] = dataclasses.field(default_factory=dict)
    # Skip loading the embedded ovos-media daemon. Useful for TTS-only
    # deployments and for tests that mock the playback backend (so no real
    # media backend plugin is loaded). Defaults to None so the ``config``
    # block (server.json) can set it; an explicit constructor value always
    # wins.
    disable_media: Optional[bool] = None

    def __post_init__(self):
        # constructor args take precedence; otherwise read from the agent-plugin
        # config block (server.json -> hivemind-player-agent-plugin).
        if self.disable_media is None:
            self.disable_media = self.config.get("disable_media", False)

        # ovos-media is the OCP-native media daemon embedded below; the
        # legacy ovos-audio AudioService and its own OCP integration stay off
        # so PlaybackService is only ever exercised for its TTS engine.
        Configuration()["enable_old_audioservice"] = False
        self.playback = PlaybackService(
            bus=self.bus,
            validate_source=False,
            disable_ocp=True,
        )

        self.media = None
        if not self.disable_media:
            # hivemind-core NATs each client's session to a per-connection id
            # (HIVEMIND-BRIDGE-1 §4), never to "default" — this device is a
            # single dedicated player, so it acts on every authorized session
            # rather than only "default".
            self.media = MediaService(bus=self.bus, validate_source=False)
            self.media.daemon = True
            self.media.start()

        self.register_bus_handlers()
        try:
            from ovos_PHAL.service import PHAL
            self.phal = PHAL(bus=self.bus)
            self.phal.start()
        except ImportError:
            LOG.warning("PHAL is not available")
            self.phal = None

    @property
    def tts(self) -> TTS:
        return self.playback.tts

    def register_bus_handlers(self):
        LOG.debug("registering internal OVOS bus handlers")
        self.bus.on("hive.send.downstream", self.handle_send)
        self.bus.on("message", self.handle_internal_mycroft)  # catch all

    # mycroft handlers  - from master -> slave
    def natural_language_query(self, utterance: str, lang: str):
        """A media-player agent answers no natural-language questions; it
        declines (yields only the end-of-query sentinel) so the node escalates
        the query upstream to an agent that can answer."""
        yield None

    def handle_send(self, message: Message):
        """ovos wants to send a HiveMessage

        a device can be both a master and a slave, downstream messages are handled here

        HiveMindSlaveInternalProtocol will handle requests meant to go upstream
        """

        payload = message.data.get("payload")
        peer = message.data.get("peer")
        msg_type = message.data["msg_type"]

        hmessage = HiveMessage(msg_type, payload=payload, target_peers=[peer])

        if msg_type in [HiveMessageType.PROPAGATE, HiveMessageType.BROADCAST]:
            # this message is meant to be sent to all slave nodes
            for peer in self.clients:
                self.clients[peer].send(hmessage)
        elif msg_type == HiveMessageType.ESCALATE:
            # only slaves can escalate, ignore silently
            #   if this device is also a slave to something,
            #   HiveMindSlaveInternalProtocol will handle the request
            pass

        # NOT a protocol specific message, send directly to requested peer
        # ovos component is asking explicitly to send a message to a peer
        elif peer:
            if peer in self.clients:
                # send message to client
                client = self.clients[peer]
                client.send(hmessage)
            else:
                LOG.error("That client is not connected")
                self.bus.emit(
                    message.forward(
                        "hive.client.send.error",
                        {"error": "That client is not connected", "peer": peer},
                    )
                )

    def handle_internal_mycroft(self, message: str):
        """forward internal messages to clients if they are the target
        here is where the client isolation happens,
        clients only get responses to their own messages"""

        # "message" event is a special case in ovos-bus-client that is not deserialized
        message = Message.deserialize(message)
        target_peers = message.context.get("destination") or []
        if not isinstance(target_peers, list):
            target_peers = [target_peers]

        # A REQUEST IS NEVER DELIVERED TO A PEER, whatever its destination says.
        # hivemind-core stamps context["source"] with the peer id it minted for
        # the connection a message arrived on, so a message whose source names a
        # CONNECTED peer is that peer's own request travelling to the agent, or
        # something forwarded from it -- never an answer to send to somebody. A
        # reply carries the peer in destination and no peer in source, because
        # Message.reply() swaps the two.
        #
        # Without this test, anything that writes a peer id into destination
        # after injection -- a transformer, a skill, any other bus writer -- has
        # this relay deliver one peer's traffic to another peer's socket with
        # source rewritten to "hive". hivemind-core stops a CLIENT writing that
        # key; this stops the same value arriving from inside the bus, which the
        # node cannot police at injection.
        #
        # HIVEMIND-AGENT-1 §3.2 delivers a RESPONSE to the peers its destination
        # names. A request is not a response.
        #
        # source is NORMALISED THE SAME WAY AS destination above, because
        # ovos_bus_client carries an array-of-strings form for this key too. A
        # string-only test reads a list as "no source" and delivers, which is
        # the same hole in a different shape.
        source = message.context.get("source") or []
        if not isinstance(source, (list, tuple)):
            source = [source]
        sources = {s for s in source if isinstance(s, str)}
        connected = list(self.clients.items())
        if target_peers and sources & {p for p, _ in connected}:
            LOG.debug(f"{message.msg_type} - not delivered: source {sorted(sources)} names "
                      f"a connected peer, so this is a request and not a response")
        elif target_peers:
            for peer, client in connected:
                if peer in target_peers:
                    # forward internal messages to clients if they are the target
                    LOG.debug(f"{message.msg_type} - destination: {peer}")
                    message.context["source"] = "hive"
                    msg = HiveMessage(
                        HiveMessageType.BUS,
                        source_peer=peer,
                        target_peers=target_peers,
                        payload=message,
                    )
                    client.send(msg)


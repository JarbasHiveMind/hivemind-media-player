import dataclasses
from typing import Dict, Any

from hivemind_bus_client.message import HiveMessage, HiveMessageType
from hivemind_core.protocol import AgentProtocol
from ovos_audio.service import PlaybackService
from ovos_bus_client.message import Message
from ovos_config import Configuration
from ovos_plugin_manager.tts import TTS
from ovos_utils.fakebus import FakeBus
from ovos_utils.log import LOG


@dataclasses.dataclass()
class HiveMindPlayerProtocol(AgentProtocol):
    bus: FakeBus = dataclasses.field(default_factory=FakeBus)
    config: Dict[str, Any] = dataclasses.field(default_factory=lambda: Configuration().get("websocket", {}))

    def __post_init__(self):
        self.playback = PlaybackService(
            bus=self.bus,
            validate_source=False
        )
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

        if target_peers:
            for peer, client in self.clients.items():
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


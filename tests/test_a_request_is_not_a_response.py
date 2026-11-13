"""A request is never delivered to a peer, whatever its destination says.

This is the same guard as hivemind-ovos-agent-plugin#73 and for the same reason.
This relay carries the identical pattern: it reads `context["destination"]`,
matches those strings against connected peers, and delivers with `source`
rewritten to "hive".

hivemind-core stops a CLIENT writing that key (HiveMind-core#382). It cannot stop
a value written INSIDE the bus after injection -- a transformer, a skill, any
other emitter. If such a value names a connected peer, this relay delivered one
peer's traffic to another peer's socket, and the receiver could not tell because
`source` had been rewritten.

The discriminator is the one this family of relays already had available:
hivemind-core stamps `context["source"]` with the peer id it minted for the
connection a message arrived on, so a message whose `source` names a CONNECTED
peer is that peer's own request in flight. A reply carries the peer in
`destination` and no peer in `source`, because `Message.reply()` swaps the two.

HIVEMIND-AGENT-1 3.2 delivers a RESPONSE to the peers its destination names. A
request is not a response.
"""
from unittest.mock import MagicMock

from ovos_bus_client.message import Message

from hivemind_player_protocol import HiveMindPlayerProtocol

ATTACKER = "attacker::session-a"
VICTIM = "victim::session-b"


def _agent(*peers):
    hm = MagicMock()
    hm.clients = {p: MagicMock() for p in peers}
    agent = HiveMindPlayerProtocol(hm_protocol=hm)
    return agent, hm.clients


def _internal(msg_type, destination=None, source=None, data=None):
    context = {}
    if destination is not None:
        context["destination"] = destination
    if source is not None:
        context["source"] = source
    return Message(msg_type, data or {}, context).serialize()


class TestARequestIsNotDelivered:
    def test_a_peer_id_written_after_injection_does_not_reach_the_victim(self):
        agent, clients = _agent(ATTACKER, VICTIM)

        agent.handle_internal_mycroft(_internal(
            "recognizer_loop:utterance", destination=VICTIM, source=ATTACKER,
            data={"utterances": ["hi"]}))

        clients[VICTIM].send.assert_not_called()
        clients[ATTACKER].send.assert_not_called()

    def test_the_same_with_the_victim_hidden_in_a_list(self):
        agent, clients = _agent(ATTACKER, VICTIM)

        agent.handle_internal_mycroft(_internal(
            "speak", destination=[VICTIM, "audio"], source=ATTACKER,
            data={"utterance": "say this"}))

        clients[VICTIM].send.assert_not_called()

    def test_the_peer_id_in_a_LIST_source_is_refused_too(self):
        # `destination` is normalised to a list, so `source` must be too: a
        # list-valued source must not read as "no source". ovos_bus_client carries an array-of-strings
        # form for this key, so an in-bus producer writing one is supported
        # behaviour, not an exotic shape.
        agent, clients = _agent(ATTACKER, VICTIM)

        agent.handle_internal_mycroft(_internal(
            "recognizer_loop:utterance", destination=[VICTIM], source=[ATTACKER],
            data={"utterances": ["hi"]}))

        clients[VICTIM].send.assert_not_called()

    def test_the_peer_id_need_not_be_first_in_that_list(self):
        agent, clients = _agent(ATTACKER, VICTIM)

        agent.handle_internal_mycroft(_internal(
            "recognizer_loop:utterance", destination=[VICTIM],
            source=["skills", ATTACKER], data={"utterances": ["hi"]}))

        clients[VICTIM].send.assert_not_called()

    def test_a_TUPLE_source_is_refused_on_the_same_reading(self):
        agent, clients = _agent(ATTACKER, VICTIM)

        agent.handle_internal_mycroft(_internal(
            "recognizer_loop:utterance", destination=[VICTIM], source=(ATTACKER,),
            data={"utterances": ["hi"]}))

        clients[VICTIM].send.assert_not_called()

    def test_a_peer_cannot_address_itself_either(self):
        # Not a security case, a design one: a peer's own request must not be
        # echoed back to it as though the agent had answered.
        agent, clients = _agent(ATTACKER)

        agent.handle_internal_mycroft(_internal(
            "speak", destination=ATTACKER, source=ATTACKER,
            data={"utterance": "hi"}))

        clients[ATTACKER].send.assert_not_called()


class TestARealResponseStillArrives:
    """The negative controls. The guard must not close the ordinary path."""

    def test_a_reply_reaches_the_peer_it_names(self):
        agent, clients = _agent(VICTIM)

        # what Message.reply() produces: the peer in destination, a service name
        # in source, because reply() swapped them
        agent.handle_internal_mycroft(_internal(
            "speak", destination=VICTIM, source="skills",
            data={"utterance": "the answer"}))

        clients[VICTIM].send.assert_called_once()

    def test_a_reply_with_no_source_at_all_still_arrives(self):
        agent, clients = _agent(VICTIM)

        agent.handle_internal_mycroft(_internal(
            "speak", destination=VICTIM, data={"utterance": "the answer"}))

        clients[VICTIM].send.assert_called_once()

    def test_a_source_naming_a_peer_that_is_not_connected_does_not_block(self):
        # The guard tests CONNECTED peers, not the shape of the string, so it
        # cannot quietly become a string-shape filter later.
        agent, clients = _agent(VICTIM)

        agent.handle_internal_mycroft(_internal(
            "speak", destination=VICTIM, source="gone::session-z",
            data={"utterance": "the answer"}))

        clients[VICTIM].send.assert_called_once()

    def test_a_LIST_source_that_names_no_connected_peer_still_delivers(self):
        # The list normalisation must not turn into "any list is refused".
        agent, clients = _agent(VICTIM)

        agent.handle_internal_mycroft(_internal(
            "speak", destination=VICTIM, source=["skills", "audio"],
            data={"utterance": "the answer"}))

        clients[VICTIM].send.assert_called_once()

    def test_two_peers_each_get_their_own_reply(self):
        agent, clients = _agent("alice::a", "bob::b")

        agent.handle_internal_mycroft(_internal(
            "speak", destination="alice::a", source="skills",
            data={"utterance": "for alice"}))
        agent.handle_internal_mycroft(_internal(
            "speak", destination="bob::b", source="skills",
            data={"utterance": "for bob"}))

        clients["alice::a"].send.assert_called_once()
        clients["bob::b"].send.assert_called_once()

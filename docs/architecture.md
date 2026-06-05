# Architecture

## Where this plugin fits

```
remote controller                  player device
(HA, ctl script, …)
        |
        | HiveMind encrypted WebSocket
        |
   hivemind-core  <---------  HiveMindPlayerProtocol (this package)
        |                               |
        |                          ovos-audio
        |                       (OCP, TTS, VLC/MPV)
        |                        ovos-PHAL (optional)
```

`HiveMindPlayerProtocol` is loaded by `hivemind-core` as the
`hivemind.agent.protocol` plugin. It owns:

1. **Local playback** — initialises `ovos_audio.service.PlaybackService` and
   optionally `ovos_PHAL.service.PHAL` on the device's internal `FakeBus`.
2. **Downstream dispatch** — when `hivemind-core` forwards an inbound
   `hive.send.downstream` bus event, the protocol routes the payload to the
   correct peer (PROPAGATE/BROADCAST fans out; targeted messages go to their peer).
3. **Response routing with client isolation** — internal bus messages whose
   `context["destination"]` matches a connected HiveMind peer are wrapped as
   `HiveMessageType.BUS` messages and forwarded to that peer only.

## What this plugin does NOT do

- **Natural-language answering** — `natural_language_query` yields only the
  end-of-query `None` sentinel. If a satellite sends a QUERY message, `hivemind-core`
  receives an empty answer and may escalate upstream.
- **Upstream forwarding** — handled by `hivemind-core`'s slave/upstream protocol.
- **Authentication, ACL, policy** — `hivemind-core`'s responsibility.

## Internal bus

The protocol uses a `FakeBus` (an in-process event emitter) rather than a real
WebSocket bus. `ovos-audio` and PHAL are wired to this FakeBus at startup. All OCP
messages forwarded by `hivemind-core` arrive on the FakeBus and are consumed by the
local audio stack.

## Plugin lifecycle

1. `hivemind-core` reads `agent_protocol.module = "hivemind-player-agent-plugin"`.
2. `AgentProtocolFactory.create(...)` instantiates `HiveMindPlayerProtocol`.
3. `__post_init__` creates `PlaybackService`, optionally starts PHAL, registers the
   two FakeBus handlers.
4. The protocol is purely event-driven from that point; it reacts to FakeBus events
   and dispatches HiveMessages to peers.

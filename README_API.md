# HiveMind Media Player API Documentation

## Overview

The `hivemind-player-protocol` package implements the HiveMind agent-protocol plugin for remote media playback control. It exposes the OVOS audio stack (PlaybackService with OCP support) over a secure HiveMind encrypted bus, allowing any device to become a networked media player controlled by remote clients.

## Architecture

The plugin runs two main components on the player device:

- **hivemind-core**: The encrypted HiveMind hub managing client connections, authentication, and per-message permissions.
- **hivemind-player-protocol**: The agent plugin that hivemind-core loads and executes.

## Plugin Contract

### Entry Point

```
Entry-point group: hivemind.agent.protocol
Entry point: hivemind-player-agent-plugin = hivemind_player_protocol:HiveMindPlayerProtocol
```

The plugin is discovered and loaded by `hivemind-plugin-manager` as an agent-protocol implementation.

## Public API

### HiveMindPlayerProtocol

The primary class implementing the agent protocol.

```python
from hivemind_player_protocol import HiveMindPlayerProtocol
from ovos_utils.fakebus import FakeBus
from ovos_config import Configuration

# Create an instance
protocol = HiveMindPlayerProtocol(
    bus=FakeBus(),  # In-process message bus (default)
    config=Configuration().get("websocket", {})  # HiveMind config (default)
)
```

#### Attributes

- **`bus`** (`FakeBus`): An in-process OVOS message bus for internal communication between the audio stack and HiveMind clients.
- **`config`** (`Dict[str, Any]`): Configuration dictionary from the `"websocket"` section of `mycroft.conf`.
- **`playback`** (`PlaybackService`): The OVOS audio playback service managing OCP and TTS.
- **`phal`** (`PHAL` or `None`): The OVOS Platform HAL service for hardware control (volume, LED, etc.), started if `ovos-phal` is installed.
- **`clients`** (`Dict[str, HiveClientConnection]`): Active HiveMind client connections (inherited from `AgentProtocol`).

#### Properties

```python
@property
def tts(self) -> TTS:
    """Return the TTS engine from the playback service."""
    return self.playback.tts
```

#### Methods

##### register_bus_handlers()

```python
def register_bus_handlers(self):
    """Register internal OVOS bus event handlers."""
```

Registers two bus listeners:

1. **`hive.send.downstream`**: Listens for OVOS components emitting HiveMessages for relay to clients.
2. **`message`**: Catch-all for all internal OVOS bus messages, providing per-client isolation.

##### handle_send(message: Message)

```python
def handle_send(self, message: Message):
    """Route downstream HiveMessages from OVOS to connected clients.
    
    Args:
        message: OVOS Message with data fields:
            - msg_type (HiveMessageType): PROPAGATE, BROADCAST, ESCALATE, or direct
            - payload: Message content
            - peer: Target peer ID (for direct send)
    
    Behavior:
        - PROPAGATE/BROADCAST: Relayed to all connected clients
        - ESCALATE: Ignored (only slaves escalate)
        - Direct (peer specified): Sent to the named peer if connected
    """
```

##### handle_internal_mycroft(message: str)

```python
def handle_internal_mycroft(self, message: str):
    """Forward internal OVOS messages to clients matching their destination.
    
    Args:
        message: Serialized OVOS Message on the internal bus
    
    Behavior:
        Deserializes the message and checks its `context["destination"]`.
        Only clients whose peer ID appears in the destination list receive the response,
        providing isolation so each client receives only responses to its own requests.
    """
```

## Supported Message Types

The plugin relays both HiveMind protocol messages and OVOS bus messages. Common control messages include:

### OVOS Audio (ovos-audio)

- `speak` — Text-to-speech
- `mycroft.audio.is_alive` — Check service readiness
- `mycroft.audio.is_ready` — Check service ready state
- `mycroft.audio.speak.status` — Speech status
- `mycroft.stop` — Stop all playback/TTS

### Open Voice OS Common Play (OCP)

- `ovos.common_play.play` — Start playback
- `ovos.common_play.pause` — Pause playback
- `ovos.common_play.resume` — Resume playback
- `ovos.common_play.stop` — Stop playback
- `ovos.common_play.next` — Next track
- `ovos.common_play.previous` — Previous track
- `ovos.common_play.set_track_position` — Seek to position
- `ovos.common_play.get_track_position` — Query current position
- `ovos.common_play.get_track_length` — Query track duration
- `ovos.common_play.track_info` — Get current track metadata
- `ovos.common_play.player.status` — Get playback status
- `ovos.common_play.playlist.queue` — Query playlist
- `ovos.common_play.playlist.clear` — Clear playlist
- `ovos.common_play.shuffle.set` — Enable shuffle
- `ovos.common_play.shuffle.unset` — Disable shuffle
- `ovos.common_play.repeat.set` — Enable repeat-all
- `ovos.common_play.repeat.unset` — Disable repeat
- `ovos.common_play.repeat.one` — Enable repeat-one

### PHAL (Platform Hardware Abstraction Layer)

- `mycroft.phal.is_alive` — Check PHAL readiness
- `mycroft.phal.is_ready` — Check PHAL ready state

### Volume Control (via ovos-phal-plugin-alsa)

- `mycroft.volume.get` — Query volume
- `mycroft.volume.set` — Set volume level
- `mycroft.volume.increase` — Increase volume
- `mycroft.volume.decrease` — Decrease volume
- `mycroft.volume.mute` — Mute audio
- `mycroft.volume.unmute` — Unmute audio

## Configuration

The plugin reads configuration from the `"websocket"` section of `mycroft.conf` (typically at `~/.config/mycroft/mycroft.conf`):

```json5
{
  "websocket": {
    // Optional HiveMind-specific settings
  }
}
```

The audio stack itself is configured in the same `mycroft.conf` file under the `"Audio"` and `"tts"` sections. Refer to the main README for examples.

## Dependencies

### Core

- `ovos-audio` — Playback service and audio backend management
- `ovos_plugin_common_play[>=1.1.4,<2.0.0]` — Common play (OCP) plugin
- `ovos-tts-plugin-server` — TTS plugin
- `hivemind-core` — HiveMind hub and protocol definitions
- `hivemind_bus_client[>=0.2.0,<1.0.0]` — HiveMind bus client for message handling
- `hivemind-plugin-manager[>=0.3.0,<1.0.0]` — Plugin discovery and management

### Extras (optional)

- `ovos_plugin_common_play[extractors]` — Audio metadata extractors for OCP
- `ovos_plugin_vlc` — VLC audio backend
- `ovos-phal` — Platform hardware abstraction (volume, LED, etc.)

## Example Usage

### Basic Plugin Instantiation

```python
from hivemind_player_protocol import HiveMindPlayerProtocol

# Plugin is instantiated by hivemind-core during startup
# when configured in server.json
protocol = HiveMindPlayerProtocol()

# The playback service is automatically available
print(f"TTS engine: {protocol.tts.engine}")
print(f"PHAL available: {protocol.phal is not None}")
```

### Sending a Play Command (from a client)

A remote HiveMind client would send an OCP message like:

```python
from ovos_bus_client.message import Message

play_message = Message(
    "ovos.common_play.play",
    {"uri": "http://example.com/song.mp3"},
    {"destination": "player_peer_id"}
)
```

The player device (running this plugin) receives it via HiveMind, the plugin routes it to its internal `bus`, the `PlaybackService` handles it, and responses are sent back to the requesting client.

### Controlling via CLI

The bundled `hivemind-player-ctl.py` script provides a command-line interface:

```bash
# Pause playback
python hivemind-player-ctl.py --key <access_key> --password <password> pause

# Play a URL
python hivemind-player-ctl.py --key <access_key> --password <password> play "http://example.com/audio.mp3"

# Enable shuffle
python hivemind-player-ctl.py --key <access_key> --password <password> shuffle.set

# Interactive shell
python hivemind-player-ctl.py --key <access_key> --password <password> interactive
```

## Installation

Install the plugin via pip:

```bash
pip install hivemind-player-protocol
```

Or with audio backend extras:

```bash
pip install 'hivemind-player-protocol[extras]'
```

## Permissions

Because HiveMind operates on a "deny by default" principle, each client must be explicitly granted permission to send specific message types. Use `hivemind-core allow-msg` after creating a client to grant permissions. Refer to the main README for the complete required permission list.

## Relations

- Part of the HiveMind distributed voice-assistant mesh
- Plugs into HiveMind via the encrypted bus client and the `hivemind.agent.protocol` entry point
- Hosts the OVOS audio stack (ovos-audio, OCP, TTS, PHAL)
- Integrates with Home Assistant and Music Assistant via `hivemind-homeassistant`

## Status

Beta (`0.0.0a1`). Functional plugin with a usable CLI and Docker deployment.

# HiveMind Media Player

Turn any device into a remotely controlled OVOS media player via HiveMind.

`hivemind-media-player` ships `HiveMindPlayerProtocol`, a HiveMind agent protocol
plugin (`hivemind.agent.protocol`) that runs the OVOS audio stack (`ovos-audio` and
optional `ovos-PHAL`) locally and exposes it to any HiveMind client. Remote
controllers send standard OCP (Open Voice OS Common Play) messages over the HiveMind
encrypted WebSocket. The player device handles playback locally.

This is for devices that are **not** running a full OVOS instance. Think of a
Raspberry Pi dedicated to being a networked speaker.

New to HiveMind? Read [docs/getting-started.md](docs/getting-started.md) —
a from-scratch walkthrough covering what this actually does, install,
the two config files, registering a client with `add-client` and the
`allow-msg` whitelist, and verifying a play command round-trips.

## Architecture

```
remote controller           HiveMind (encrypted WebSocket)    this device
(Home Assistant,       <--------------------------------->    hivemind-core
 hivemind-player-ctl,                                         + HiveMindPlayerProtocol
 any OCP client)                                              + ovos-audio (TTS, OCP, VLC/MPV...)
```

The player agent answers **no** natural-language questions (`natural_language_query`
yields only the end-of-query sentinel). Its sole role is to receive OCP/audio bus
messages forwarded by `hivemind-core` and play them through the local audio stack.

## Install

```bash
pip install hivemind-player-protocol
```

Optional extras (VLC, MPV backends):

```bash
pip install "hivemind-player-protocol[extras]"
```

Or from source:

```bash
git clone https://github.com/JarbasHiveMind/hivemind-media-player
cd hivemind-media-player
pip install -e .
```

### Dependencies

The whole stack rides the **`ovos-bus-client` 2.x line** (HiveMind core 4.6.x
requires it). That line, and the OVOS components updated to ride it
(`ovos-audio`, OCP, `ovos-plugin-manager`, `ovos-workshop`), are currently
published as **prereleases**.

`pyproject.toml` pins each dependency to its *prerelease floor* (for example
`ovos-bus-client>=2.0.0a3`). A plain `pip install` then resolves the right
versions. **No `--pre` flag is needed.** Do not add `--pre`. The floor pins
opt into the prereleases, package by package, and keep resolution deterministic.

`hivemind-core` itself (AGPL) is **not** a runtime dependency. The plugin only
imports its `AgentProtocol` base. The host process supplies `hivemind-core`.
The test suite pulls it in through the `[e2e]` extra.

## Quickstart

### 1. Configure hivemind-core

Edit `~/.config/hivemind-core/server.json` on the player device:

```json
{
  "agent_protocol": {
    "module": "hivemind-player-agent-plugin",
    "hivemind-player-agent-plugin": {}
  }
}
```

### 2. Configure ovos-audio

Edit `~/.config/mycroft/mycroft.conf` on the same device:

```json
{
  "play_wav_cmdline": "paplay %1",
  "play_mp3_cmdline": "mpg123 %1",
  "play_ogg_cmdline": "ogg123 -q %1",
  "tts": {
    "module": "ovos-tts-plugin-server"
  },
  "Audio": {
    "backends": {
      "OCP": {
        "type": "ovos_common_play",
        "preferred_audio_services": ["mpv", "vlc"],
        "active": true
      },
      "vlc": { "type": "vlc", "active": true },
      "mpv": { "type": "mpv",  "active": true }
    }
  }
}
```

### 3. Create a client credential

On the player device (where `hivemind-core` will run):

```bash
hivemind-core add-client
# note the Access Key and Password printed
```

### 4. Grant OCP permissions

```bash
# replace 3 with your Node ID from add-client
hivemind-core allow-msg "ovos.common_play.play" 3
hivemind-core allow-msg "ovos.common_play.pause" 3
hivemind-core allow-msg "ovos.common_play.resume" 3
hivemind-core allow-msg "ovos.common_play.stop" 3
hivemind-core allow-msg "ovos.common_play.next" 3
hivemind-core allow-msg "ovos.common_play.previous" 3
hivemind-core allow-msg "speak" 3
```

See [Permissions](#permissions) for the full list.

### 5. Set the identity on the controller

On the device that will send commands:

```bash
hivemind-client set-identity \
  --key <access_key> --password <password> \
  --host <player_device_ip> --port 5678 --siteid player
```

### 6. Start hivemind-core on the player device

```bash
hivemind-core listen
```

### 7. Control playback

```bash
python hivemind-player-ctl.py play "http://example.com/audio/track.mp3"
python hivemind-player-ctl.py pause
python hivemind-player-ctl.py resume
python hivemind-player-ctl.py next
```

## Home Assistant / Music Assistant Integration

With [hivemind-homeassistant](https://github.com/JarbasHiveMind/hivemind-homeassistant),
HiveMind player devices appear as media players in Home Assistant. Music Assistant can
then browse and play music to them.

Related projects:
- [hivemind-homeassistant](https://github.com/JarbasHiveMind/hivemind-homeassistant)
- [ovos-skill-music-assistant](https://github.com/HiveMindInsiders/ovos-skill-music-assistant)
- [ovos-media-plugin-mass](https://github.com/HiveMindInsiders/ovos-media-plugin-mass)

## hivemind-player-ctl

`hivemind-player-ctl.py` is a CLI to control a running player. It requires only
`hivemind_bus_client` and `click`.

```
Usage: python hivemind-player-ctl.py [OPTIONS] COMMAND
Options:
  --key TEXT       Access key (or read from identity file)
  --password TEXT  Password (or read from identity file)
Commands:
  play URI          Start playback of a URI
  pause             Pause
  resume            Resume
  stop              Stop
  next              Next track
  prev              Previous track
  shuffle.set       Enable shuffle
  shuffle.unset     Disable shuffle
  repeat.set        Enable repeat-all
  repeat.one        Enable repeat-one
  repeat.unset      Disable repeat
  interactive       Interactive shell
```

## Permissions

### Core audio

| Message | Purpose |
|---|---|
| `speak` | TTS output |
| `mycroft.audio.is_alive` | Health check |
| `mycroft.audio.is_ready` | Readiness check |
| `mycroft.stop` | Stop all audio |

### OCP (Open Voice OS Common Play)

| Message | Purpose |
|---|---|
| `ovos.common_play.play` | Start playback |
| `ovos.common_play.pause` | Pause |
| `ovos.common_play.resume` | Resume |
| `ovos.common_play.stop` | Stop |

| Message | Purpose |
|---|---|
| `ovos.common_play.next` | Next track |
| `ovos.common_play.previous` | Previous track |
| `ovos.common_play.player.status` | Query player status |
| `ovos.common_play.track_info` | Query track info |

| Message | Purpose |
|---|---|
| `ovos.common_play.playlist.queue` | Queue a track |
| `ovos.common_play.playlist.clear` | Clear the queue |
| `ovos.common_play.set_track_position` | Seek |

| Message | Purpose |
|---|---|
| `ovos.common_play.shuffle.set` | Enable shuffle |
| `ovos.common_play.shuffle.unset` | Disable shuffle |

| Message | Purpose |
|---|---|
| `ovos.common_play.repeat.set` | Enable repeat |
| `ovos.common_play.repeat.unset` | Disable repeat |
| `ovos.common_play.repeat.one` | Repeat one |

### PHAL (optional)

| Message | Purpose |
|---|---|
| `mycroft.phal.is_alive` | PHAL health |
| `mycroft.phal.is_ready` | PHAL readiness |

| Message | Purpose |
|---|---|
| `mycroft.volume.get` | Query volume |
| `mycroft.volume.set` | Set volume |

| Message | Purpose |
|---|---|
| `mycroft.volume.increase` | Volume up |
| `mycroft.volume.decrease` | Volume down |
| `mycroft.volume.mute` | Mute |
| `mycroft.volume.unmute` | Unmute |

## Running the tests

The suite is **end-to-end**. It stands up a real `hivemind-core` master
in-process and drives the real player plugin over a real `HiveMessageBusClient`
(through [`hivescope`](https://github.com/JarbasHiveMind/hivescope)). It asserts
that remote `play`, `pause`, and `stop` control commands round-trip from a
satellite, through the deny-by-default ACL, to the player.

**The audio playback backend is mocked.** OCP and the legacy audio service are
disabled, so no real audio plugin loads and nothing touches an audio device or
the network.

```bash
pip install -e ".[test]"   # pulls hivescope + in-process hivemind-core ([e2e])
pytest tests/
```

The heavyweight e2e hosts live in the `[e2e]` extra. `[test]` includes them plus
the test runner. `hivescope` and `hivemind-core` are required test dependencies.
The suite never `importorskip`s them.

## Documentation

- [`docs/architecture.md`](docs/architecture.md): how the player protocol fits into
  HiveMind.
- [`docs/configuration.md`](docs/configuration.md): configuration reference.
- [`docs/permissions.md`](docs/permissions.md): full permissions reference.

## License

Apache 2.0.

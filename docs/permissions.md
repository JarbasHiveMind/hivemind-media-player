# Permissions

HiveMind operates on a deny-by-default model: every message type a client may send
must be explicitly allowed with `hivemind-core allow-msg`.

## Granting permissions

```bash
# Replace 3 with the Node ID from `hivemind-core add-client`
hivemind-core allow-msg "speak" 3
hivemind-core allow-msg "ovos.common_play.play" 3
# ... repeat for each message type below
```

## Required message types

### ovos-audio core

| Message | Purpose |
|---|---|
| `speak` | TTS synthesis and playback |
| `mycroft.audio.is_alive` | Health check |
| `mycroft.audio.is_ready` | Ready check |

| Message | Purpose |
|---|---|
| `mycroft.audio.speak.status` | TTS status |
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
| `ovos.common_play.track_info` | Query current track info |

| Message | Purpose |
|---|---|
| `ovos.common_play.get_track_length` | Query track duration |
| `ovos.common_play.get_track_position` | Query playback position |
| `ovos.common_play.set_track_position` | Seek to position |

| Message | Purpose |
|---|---|
| `ovos.common_play.playlist.queue` | Add to queue |
| `ovos.common_play.playlist.clear` | Clear queue |

| Message | Purpose |
|---|---|
| `ovos.common_play.shuffle.set` | Enable shuffle |
| `ovos.common_play.shuffle.unset` | Disable shuffle |

| Message | Purpose |
|---|---|
| `ovos.common_play.repeat.set` | Enable repeat-all |
| `ovos.common_play.repeat.unset` | Disable repeat |
| `ovos.common_play.repeat.one` | Repeat current track |

### PHAL (optional)

Required only if `ovos-PHAL` is installed and used.

| Message | Purpose |
|---|---|
| `mycroft.phal.is_alive` | PHAL health check |
| `mycroft.phal.is_ready` | PHAL ready check |

### ovos-phal-plugin-alsa (optional volume control)

| Message | Purpose |
|---|---|
| `mycroft.volume.get` | Query current volume |
| `mycroft.volume.set` | Set volume level |

| Message | Purpose |
|---|---|
| `mycroft.volume.increase` | Volume up |
| `mycroft.volume.decrease` | Volume down |
| `mycroft.volume.mute` | Mute |
| `mycroft.volume.unmute` | Unmute |

### Audio Service (legacy, OCP-less deployments)

Only needed when not using the OCP backend.

| Message | Purpose |
|---|---|
| `mycroft.audio.service.play` | Play |
| `mycroft.audio.service.resume` | Resume |
| `mycroft.audio.service.pause` | Pause |
| `mycroft.audio.service.stop` | Stop |

| Message | Purpose |
|---|---|
| `mycroft.audio.service.prev` | Previous |
| `mycroft.audio.service.next` | Next |
| `mycroft.audio.service.set_track_position` | Seek |

---
[← Configuration](configuration.md) · [Home](../README.md)

# HiveMind Player Protocol

run `hivemind-core` with `hivemind-player-agent` to turn any device into an OCP Media Player. 

The `ovos-audio` stack will be served behind a hivemind connection, you can then send the standard OCP bus messages to trigger playback in the device running `hivemind-player-agent`

> NOTE: this is not meant for usage in a device that is already running OpenVoiceOS, only for standalone devices

---

## Configuration

### hivemind-core

to configure `hivemind-core` edit ` ~/.config/hivemind-core/server.json` and set your agent plugin to `"hivemind-player-agent-plugin"`

```json5
{
    "agent_protocol": {
        "module": "hivemind-player-agent-plugin",
        "hivemind-player-agent-plugin": {}
    }
}
```

### ovos-audio

to configure `ovos-audio` edit `~/.config/mycroft/mycroft.conf` 
  - configure players under `"Audio"` 
  - configure text-to-speech under `"tts"`

```json5
{
  "tts": {
    "module": "ovos-tts-plugin-server"
  },
  
  "Audio": {
    "backends": {
      "OCP": {
        "type": "ovos_common_play",
        "preferred_audio_services": ["mpv", "vlc", "simple"],
        "disable_mpris": true,
        "dbus_type": "session",
        "manage_external_players": false,
        "active": true
      },
      "vlc": {
        "type": "vlc",
        "active": true,
        "initial_volume": 100,
        "low_volume": 50
      },
      "mass-HomeLabRenderer:dlna": {
        "type": "ovos_mass",
        "identifier": "uuid:4b778a71-0499-485a-a5a4-88140603fba9",
        "url": "http://100.88.41.41:8095",
        "player_type": "dlna",
        "active": true
      }
    }
  }
}
```

---

## Home Assistant / Music Assistant

You can add HiveMind players to HomeAssistant, they can then be integrated with Music Assistant (via HA) to turn any device into a media player.

![image](https://github.com/user-attachments/assets/9bb3bdba-bce0-47f5-b837-6f934eff67ef)

![image](https://github.com/user-attachments/assets/1b0adcb0-bb92-4125-82ee-36367ce2bf60)

**Related Projects:**

- [hivemind-homeassistant](https://github.com/JarbasHiveMind/hivemind-homeassistant) allows HiveMind to show up as a player in Home Assistant
- [ovos-skill-music-assistant](https://github.com/HiveMindInsiders/ovos-skill-music-assistant) allows OVOS to search media in MA sources
- [ovos-media-plugin-mass](https://github.com/HiveMindInsiders/ovos-media-plugin-mass) allows OVOS to control MA players

---

## Permissions

You need to allow the following messages in hivemind-core

### ovos-audio

- `speak`
- `mycroft.audio.is_alive`
- `mycroft.audio.is_ready`
- `mycroft.audio.speak.status`
- `mycroft.stop`

#### OCP (OpenVoiceOS Common Play)

- `ovos.common_play.player.status`
- `ovos.common_play.track_info`
- `ovos.common_play.get_track_length`
- `ovos.common_play.get_track_position`
- `ovos.common_play.playlist.queue`
- `ovos.common_play.resume`
- `ovos.common_play.pause`
- `ovos.common_play.stop`
- `ovos.common_play.previous`
- `ovos.common_play.next`
- `ovos.common_play.set_track_position`
- `ovos.common_play.playlist.clear`
- `ovos.common_play.shuffle.set`
- `ovos.common_play.shuffle.unset`
- `ovos.common_play.repeat.set`
- `ovos.common_play.repeat.unset`
- `ovos.common_play.repeat.one`

#### Audio Service

*(only if enabled manually — for systems without the OCP Audio Plugin)*

- `mycroft.audio.service.play`
- `mycroft.audio.service.resume`
- `mycroft.audio.service.pause`
- `mycroft.audio.service.stop`
- `mycroft.audio.service.prev`
- `mycroft.audio.service.next`
- `mycroft.audio.service.set_track_position`

### PHAL

*(optional for platform/hardware plugins)*

- `mycroft.phal.is_alive`
- `mycroft.phal.is_ready`

#### ovos-phal-plugin-alsa

*(optional for volume control)*

- `mycroft.volume.get`
- `mycroft.volume.increase`
- `mycroft.volume.decrease`
- `mycroft.volume.mute`
- `mycroft.volume.unmute`



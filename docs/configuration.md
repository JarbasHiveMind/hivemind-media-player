# Configuration

## hivemind-core (`server.json`)

`~/.config/hivemind-core/server.json`:

```json
{
  "agent_protocol": {
    "module": "hivemind-player-agent-plugin",
    "hivemind-player-agent-plugin": {}
  }
}
```

Audio configuration lives in `mycroft.conf`; the agent-plugin block is for the
protocol itself. The plugin accepts these optional keys:

| Key | Default | Purpose |
|---|---|---|
| `disable_ocp` | `false` | Skip loading the OCP backend (for OCP-less deployments, or to mock playback). |
| `enable_old_audioservice` | *(OVOS config)* | Override whether the legacy pre-OCP `ovos-audio` AudioService is loaded. |

```json
{
  "agent_protocol": {
    "module": "hivemind-player-agent-plugin",
    "hivemind-player-agent-plugin": {
      "disable_ocp": false
    }
  }
}
```

## ovos-audio (`mycroft.conf`)

`~/.config/mycroft/mycroft.conf`:

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
      "mpv": {
        "type": "mpv",
        "active": true,
        "initial_volume": 100,
        "low_volume": 50
      }
    }
  }
}
```

Any TTS and OCP audio backend plugin for OpenVoiceOS works here. Refer to the
[OVOS documentation](https://openvoiceos.github.io/ovos-technical-manual/) for the
full list.

## Docker

A `docker-compose.yml` and `Dockerfile` are included for containerised deployment.
Copy `.env.example` to `.env`, fill in the values, then:

```bash
docker compose up -d
```

The container exposes port `5678` for HiveMind connections.

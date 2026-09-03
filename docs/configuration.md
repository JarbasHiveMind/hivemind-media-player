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

Audio/media configuration lives in `mycroft.conf`; the agent-plugin block is
for the protocol itself. The plugin forces `enable_old_audioservice=False`
process-wide (overriding any value already in `mycroft.conf`) — the embedded
stack serves media exclusively through `ovos-media`, so the legacy
`ovos-audio` AudioService is never loaded. The plugin accepts these optional
keys:

| Key | Default | Purpose |
|---|---|---|
| `disable_media` | `false` | Skip loading the embedded `ovos-media` daemon (for TTS-only deployments, or to mock playback). |

```json
{
  "agent_protocol": {
    "module": "hivemind-player-agent-plugin",
    "hivemind-player-agent-plugin": {
      "disable_media": false
    }
  }
}
```

## ovos-audio (`mycroft.conf`) — TTS only

`~/.config/mycroft/mycroft.conf`:

```json
{
  "tts": {
    "module": "ovos-tts-plugin-server"
  }
}
```

Any TTS plugin for OpenVoiceOS works here. `Audio.backends` is not read (the
embedded `ovos-audio` never loads AudioService backends); playback
configuration belongs under `media`, below.

## ovos-media (`mycroft.conf`) — playback

```json
{
  "media": {
    "preferred_audio_services": ["vlc"],
    "audio_players": {
      "vlc": {
        "module": "ovos-media-audio-plugin-vlc",
        "aliases": ["VLC"],
        "active": true
      }
    }
  }
}
```

Any `opm.media.audio` / `opm.media.video` / `opm.media.web` backend plugin
works here, declared under `media.audio_players` / `media.video_players` /
`media.web_players` respectively, keyed by a local plugin name. Refer to
[ovos-media's configuration reference](https://github.com/OpenVoiceOS/ovos-media/blob/dev/docs/configuration.md)
for the full option set.

## Docker

A `docker-compose.yml` and `Dockerfile` are included for containerized deployment.
Copy `.env.example` to `.env`, fill in the values, then:

```bash
docker compose up -d
```

The container exposes port `5678` for HiveMind connections.

---
[← Architecture](architecture.md) · [Home](../README.md) · [Permissions →](permissions.md)

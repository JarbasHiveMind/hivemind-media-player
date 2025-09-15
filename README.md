# HiveMind Media Player

This project allows you to turn any device into a media player that can be controlled remotely. It achieves this by using **HiveMind** to connect and control the **Open Voice OS (OVOS)** audio stack remotely.

Essentially, you'll run two main components:

  * `hivemind-core`: The central hub that manages connections and messages. Think of it as the brain of your remote control system.
  * `hivemind-player-agent`: This is a small plugin that turns the `hivemind-core` device into a media player.

By running both of these, you can send standard **Open Voice OS Common Play (OCP)** messages to the player device to control audio playback. For example, you can send a message to play a song, pause it, or skip to the next track.

> **Note:** This setup is designed for devices that are *not* already running Open Voice OS. It's perfect for things like a Raspberry Pi dedicated to being a speaker.

-----

## Home Assistant / Music Assistant Integration

One of the most powerful uses of this protocol is to integrate your HiveMind players with **Home Assistant** 🏡 and **Music Assistant**. This allows you to turn any device you set up into a media player that can be controlled directly from your smart home dashboard.

![image](https://github.com/user-attachments/assets/9bb3bdba-bce0-47f5-b837-6f934eff67ef)

![image](https://github.com/user-attachments/assets/1b0adcb0-bb92-4125-82ee-36367ce2bf60)

By using **hivemind-homeassistant**, your HiveMind player will show up in Home Assistant. From there, you can use **Music Assistant** to browse and play music from various sources in your new HiveMind-powered player.

**Related Projects:**

  * [hivemind-homeassistant](https://github.com/JarbasHiveMind/hivemind-homeassistant): A component that allows HiveMind devices to be discovered and controlled within Home Assistant.
  * [ovos-skill-music-assistant](https://github.com/HiveMindInsiders/ovos-skill-music-assistant): An OVOS skill that enables you to search for media in your Music Assistant libraries.
  * [ovos-media-plugin-mass](https://github.com/HiveMindInsiders/ovos-media-plugin-mass): An OVOS plugin that allows you to control Music Assistant players directly.

-----

## Configuration

To get started, you'll need to configure both `hivemind-core` and the `ovos-audio` stack.

### `hivemind-core`

The first step is to tell **HiveMind** which agent to use. You'll edit the `server.json` configuration file, typically located at `~/.config/hivemind-core/server.json`.

```json5
{
    "agent_protocol": {
        "module": "hivemind-player-agent-plugin",
        "hivemind-player-agent-plugin": {}
    }
}
```

In this file, you'll set the `agent_protocol` module to `"hivemind-player-agent-plugin"`. This tells HiveMind to load the correct plugin for controlling the player device.

-----

### `ovos-audio`

Next, you need to configure the audio player itself. The **ovos-audio** stack is part of the Open Voice OS ecosystem and handles all audio playback and text-to-speech (TTS) functions. You'll configure it by editing `mycroft.conf`, usually found at `~/.config/mycroft/mycroft.conf`.

Within this file, you'll find two key sections:

  * `"Audio"`: This is where you configure the specific audio players you want to use.
  * `"tts"`: This section is for configuring the **text-to-speech** module, which allows the device to speak.

The HiveMind player exposes a standalone `ovos-audio` under `hivemind-core`. This means all existing TTS and player plugins for OpenVoiceOS should work! Please refer to the OpenVoiceOS project for more information.

Here is an example configuration:

```json5
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

In this example, **OCP** is configured as the main audio backend, with a preference for using players like **MPV** or **VLC**. Specific `vlc` and `mpv` players are also configured for reference. This shows the flexibility of the `ovos-audio` stack to handle various playback plugins.


---

## Security and Access Keys

To ensure only authorized devices can control your media player, **HiveMind** uses a robust security and permissions system. You will need to create and configure an access key for your controlling device. This acts as a set of credentials, allowing it to connect to and send commands to `hivemind-core`.

### Step 1: Create a New Client

First, use the `hivemind-core add-client` command to generate a unique set of credentials. You'll need the `Access Key` and `Password` from this output to connect your controlling device later.

```bash
$ hivemind-core add-client 
Database backend: JsonDB
Credentials added to database!

Node ID: 3
Friendly Name: HiveMind-Node-2
Access Key: 57e488946808014168d9237c11e68959
Password: a60319726ca815102f7c5ff88527ec37
Encryption Key: 588816c6ba5477c3
WARNING: Encryption Key is deprecated, only use if your client does not support password
```

Keep these credentials secure\! You'll use them to authenticate your controlling device.

### Step 2: Grant Permissions

Once the client is created, you must explicitly grant it permission to send specific types of messages. The HiveMind permissions system operates on a "deny by default" principle, meaning you have to allow every message type you want to use.

Use the `hivemind-core allow-msg` command to grant these permissions. The command requires two arguments: the message type (e.g., `"speak"`) and the `Node ID` of the client you just created.

For example, to allow your client (`Node ID: 3`) to trigger the text-to-speech engine (`"speak"`), you would run:

```bash
$ hivemind-core allow-msg "speak" 3
Allowed 'speak' for HiveMind-Node-2
```

You must repeat this command for every message listed in the **Permissions** section below. This ensures your controlling device has all the necessary privileges to manage the media player.

---


## Permissions


### `ovos-audio`

These messages are required for core audio functionality, including text-to-speech and general playback status.

  * `speak`
  * `mycroft.audio.is_alive`
  * `mycroft.audio.is_ready`
  * `mycroft.audio.speak.status`
  * `mycroft.stop`

#### OCP (Open Voice OS Common Play)

These are the primary messages used to control media playback, covering actions like playing, pausing, and managing playlists.

  * `ovos.common_play.player.status`
  * `ovos.common_play.track_info`
  * `ovos.common_play.get_track_length`
  * `ovos.common_play.get_track_position`
  * `ovos.common_play.playlist.queue`
  * `ovos.common_play.play`
  * `ovos.common_play.resume`
  * `ovos.common_play.pause`
  * `ovos.common_play.stop`
  * `ovos.common_play.previous`
  * `ovos.common_play.next`
  * `ovos.common_play.set_track_position`
  * `ovos.common_play.playlist.clear`
  * `ovos.common_play.shuffle.set`
  * `ovos.common_play.shuffle.unset`
  * `ovos.common_play.repeat.set`
  * `ovos.common_play.repeat.unset`
  * `ovos.common_play.repeat.one`

#### Audio Service

*(only if enabled manually — for systems without the OCP Audio Plugin)*

If you're not using OCP, these messages provide a direct way to control the underlying audio service.

  * `mycroft.audio.service.play`
  * `mycroft.audio.service.resume`
  * `mycroft.audio.service.pause`
  * `mycroft.audio.service.stop`
  * `mycroft.audio.service.prev`
  * `mycroft.audio.service.next`
  * `mycroft.audio.service.set_track_position`

### PHAL

*(optional for platform/hardware plugins)*

  * `mycroft.phal.is_alive`
  * `mycroft.phal.is_ready`

#### ovos-phal-plugin-alsa

*(optional for volume control)*

If you want to control the system's volume, you'll need to allow these specific volume control messages.

  * `mycroft.volume.get`
  * `mycroft.volume.set`
  * `mycroft.volume.increase`
  * `mycroft.volume.decrease`
  * `mycroft.volume.mute`
  * `mycroft.volume.unmute`
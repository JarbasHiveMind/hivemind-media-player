import os

import click
from hivemind_bus_client.client import HiveMessageBusClient
from hivemind_bus_client.identity import NodeIdentity
from ovos_bus_client import Message
from ovos_utils.fakebus import FakeBus
from ovos_utils.log import LOG, init_service_logger
from ovos_utils.ocp import MediaType, MediaEntry, TrackState, PlaybackType
from ovos_utils.xdg_utils import xdg_state_home


def get_client(key: str, password: str, host: str, port: int, siteid: str):
    # Set up logging
    init_service_logger("hivemind-player-cli")
    LOG.base_path = os.path.join(xdg_state_home(), "hivemind")
    LOG.set_level("ERROR")

    identity = NodeIdentity()
    password = password or identity.password
    key = key or identity.access_key
    host = host or identity.default_master
    siteid = siteid or identity.site_id or "unknown"
    port = port or identity.default_port or 5678

    if not host.startswith("ws://") and not host.startswith("wss://"):
        host = "ws://" + host

    if not key or not password or not host:
        raise RuntimeError("NodeIdentity not set, please pass key/password/host or "
                           "call 'hivemind-client set-identity'")

    node = HiveMessageBusClient(key, host=host, port=port, password=password)
    node.connect(FakeBus(), site_id=siteid)
    return node


@click.group()
@click.option("--key", help="HiveMind access key (default read from identity file)", type=str, default="")
@click.option("--password", help="HiveMind password (default read from identity file)", type=str, default="")
@click.option("--host", help="HiveMind host (default read from identity file)", type=str, default="")
@click.option("--port", help="HiveMind port number (default: 5678)", type=int, required=False)
@click.option("--siteid", help="location identifier for message.context (default read from identity file)", type=str,
              default="")
@click.pass_context
def cli(ctx, key: str, password: str, host: str, port: int, siteid: str):
    ctx.obj = get_client(key, password, host, port, siteid)


def _get_play_message(uri: str,
                      legacy_audioservice=False,
                      media_type: MediaType = MediaType.MUSIC) -> Message:
    if legacy_audioservice:
        return Message('mycroft.audio.service.play',
                       {'tracks': [uri]})
    else:
        entry = MediaEntry(
            uri=uri,
            title="",
            artist="",
            length=0,
            match_confidence=100,
            skill_id="OCP.hivemind",
            skill_icon="https://raw.githubusercontent.com/home-assistant/brands/refs/heads/master/core_integrations/music_assistant/icon.png",
            image="",
            status=TrackState.QUEUED_AUDIO,
            media_type=media_type,
            playback=PlaybackType.AUDIO,
        )
        return Message("ovos.common_play.play",
                       {"media": entry.as_dict},
                       {"destination": "OCP"})


@cli.command()
@click.pass_obj
def interactive(node: HiveMessageBusClient):
    print("== connected to HiveMind")

    def handle_speak(message: Message):
        utt = message.data["utterance"]
        print(">", utt)

    node.on_mycroft("speak", handle_speak)

    print("Commands: play <uri>, pause, resume, next, prev, shuffle, repeat [one|all|none], quit")
    while True:
        try:
            cmd = input("command: ").strip()
            if not cmd:
                continue

            parts = cmd.split(maxsplit=1)
            action = parts[0].lower()
            arg = parts[1] if len(parts) > 1 else None

            if action == "quit":
                break
            elif action == "play" and arg:
                node.emit_mycroft(_get_play_message(arg))
            elif action == "pause":
                node.emit_mycroft(Message("ovos.common_play.pause", {}, {"destination": "OCP"}))
            elif action == "resume":
                node.emit_mycroft(Message("ovos.common_play.resume", {}, {"destination": "OCP"}))
            elif action == "next":
                node.emit_mycroft(Message("ovos.common_play.next", {}, {"destination": "OCP"}))
            elif action == "prev":
                node.emit_mycroft(Message("ovos.common_play.prev", {}, {"destination": "OCP"}))
            elif action == "shuffle":
                node.emit_mycroft(Message("ovos.common_play.shuffle", {}, {"destination": "OCP"}))
            elif action == "repeat" and arg:
                node.emit_mycroft(Message("ovos.common_play.repeat", {"mode": arg}, {"destination": "OCP"}))
            else:
                print("Unknown command or missing argument")
        except KeyboardInterrupt:
            break
        except Exception:
            LOG.exception("error")
            break

    node.close()


@cli.command()
@click.argument("uri")
@click.pass_obj
def play(node: HiveMessageBusClient, uri: str):
    node.emit_mycroft(Message("ovos.common_play.play", {"uri": uri}, {"destination": "OCP"}))


@cli.command()
@click.pass_obj
def pause(node: HiveMessageBusClient):
    node.emit_mycroft(Message("ovos.common_play.pause", {}, {"destination": "OCP"}))


@cli.command()
@click.pass_obj
def resume(node: HiveMessageBusClient):
    node.emit_mycroft(Message("ovos.common_play.resume", {}, {"destination": "OCP"}))


@cli.command(name="next")
@click.pass_obj
def next_cmd(node: HiveMessageBusClient):
    node.emit_mycroft(Message("ovos.common_play.next", {}, {"destination": "OCP"}))


@cli.command(name="prev")
@click.pass_obj
def prev_cmd(node: HiveMessageBusClient):
    node.emit_mycroft(Message("ovos.common_play.prev", {}, {"destination": "OCP"}))


@cli.command()
@click.pass_obj
def shuffle(node: HiveMessageBusClient):
    node.emit_mycroft(Message("ovos.common_play.shuffle", {}, {"destination": "OCP"}))


@cli.command()
@click.argument("mode", type=click.Choice(["one", "all", "none"]))
@click.pass_obj
def repeat(node: HiveMessageBusClient, mode: str):
    node.emit_mycroft(Message("ovos.common_play.repeat", {"mode": mode}, {"destination": "OCP"}))


if __name__ == "__main__":
    cli()

"""
Usage: client.py [OPTIONS] COMMAND [ARGS]...

  A command-line tool for controlling a HiveMind media player.

Options:
  --key TEXT       HiveMind access key (default read from identity file)
  --password TEXT  HiveMind password (default read from identity file)
  --host TEXT      HiveMind host (default read from identity file)
  --port INTEGER   HiveMind port number (default: 5678)
  --help           Show this message and exit.

Commands:
  interactive    Launches an interactive shell to control the player.
  next           Skips to the next track in the playlist.
  pause          Pauses the current playback.
  play           Starts playback of the given URI.
  prev           Returns to the previous track in the playlist.
  repeat.one     Enables repeat single-track mode.
  repeat.set     Enables repeat all mode.
  repeat.unset   Disables repeat mode.
  resume         Resumes the current playback.
  shuffle.set    Enables shuffle mode.
  shuffle.unset  Disables shuffle mode.
"""
import os

import click
from hivemind_bus_client.client import HiveMessageBusClient
from hivemind_bus_client.identity import NodeIdentity
from ovos_bus_client import Message
from ovos_utils.fakebus import FakeBus
from ovos_utils.log import LOG, init_service_logger
from ovos_utils.ocp import MediaType, MediaEntry, TrackState, PlaybackType
from ovos_utils.xdg_utils import xdg_state_home


def get_client(key: str, password: str, host: str, port: int) -> HiveMessageBusClient:
    """
    Initializes and connects the HiveMind MessageBus Client.
    It reads credentials from the identity file by default, but can be
    overridden by command-line arguments.
    """
    # Set up logging for the client
    init_service_logger("hivemind-player-cli")
    LOG.base_path = os.path.join(xdg_state_home(), "hivemind")
    LOG.set_level("ERROR")

    identity = NodeIdentity()
    password = password or identity.password
    key = key or identity.access_key
    host = host or identity.default_master
    siteid = identity.site_id or "unknown"
    port = port or identity.default_port or 5678

    if not host.startswith("ws://") and not host.startswith("wss://"):
        host = "ws://" + host

    if not key or not password or not host:
        raise RuntimeError("NodeIdentity not set. Please ensure you have generated "
                           "an identity with 'hivemind-client set-identity' or "
                           "passed all required arguments.")

    node = HiveMessageBusClient(key, host=host, port=port, password=password)
    # The FakeBus is a placeholder for the local bus, as we only need to
    # connect to the remote HiveMind bus.
    node.connect(FakeBus(), site_id=siteid)
    return node


def _get_play_message(uri: str,
                      media_type: MediaType = MediaType.MUSIC,
                      playback=PlaybackType.AUDIO,
                      status=TrackState.QUEUED_AUDIO) -> Message:
    """
    Creates a standardized OCP play message with a rich MediaEntry payload.
    This provides more metadata for the player.
    """
    # TODO - more kwargs
    entry = MediaEntry(
        uri=uri,
        title=f"Playback of {os.path.basename(uri)}",
        artist="",
        length=0,
        match_confidence=100,
        skill_id="OCP.hivemind",
        skill_icon="https://github.com/JarbasHiveMind/HiveMind-assets/raw/master/logo/hivemind-512.png",
        image="",
        status=status,
        media_type=media_type,
        playback=playback,
    )
    return Message("ovos.common_play.play", {"media": entry.as_dict})


@click.group()
@click.option("--key", help="HiveMind access key (default read from identity file)", type=str, default="")
@click.option("--password", help="HiveMind password (default read from identity file)", type=str, default="")
@click.option("--host", help="HiveMind host (default read from identity file)", type=str, default="")
@click.option("--port", help="HiveMind port number (default: 5678)", type=int, required=False)
@click.pass_context
def cli(ctx, key: str, password: str, host: str, port: int):
    """A command-line tool for controlling a HiveMind media player."""
    try:
        ctx.obj = get_client(key, password, host, port)
    except Exception as e:
        click.echo(f"Error connecting to HiveMind: {e}", err=True)
        ctx.exit(1)


@cli.command()
@click.pass_obj
def interactive(node: HiveMessageBusClient):
    """Launches an interactive shell to control the player."""
    print("== Connected to HiveMind. Type 'quit' to exit.")
    print("Commands: play <uri>, pause, resume, next, prev, shuffle.<set|unset>, repeat.<set|unset|one>, quit")

    while True:
        try:
            cmd_line = input("command: ").strip()
            if not cmd_line:
                continue

            parts = cmd_line.split(maxsplit=1)
            action = parts[0].lower()
            arg = parts[1] if len(parts) > 1 else None

            if action == "quit":
                break
            elif action == "play" and arg:
                node.emit_mycroft(_get_play_message(arg))
            elif action == "pause":
                node.emit_mycroft(Message("ovos.common_play.pause"))
            elif action == "resume":
                node.emit_mycroft(Message("ovos.common_play.resume"))
            elif action == "next":
                node.emit_mycroft(Message("ovos.common_play.next"))
            elif action == "prev":
                node.emit_mycroft(Message("ovos.common_play.prev"))
            elif action == "shuffle.set":
                node.emit_mycroft(Message("ovos.common_play.shuffle.set"))
            elif action == "shuffle.unset":
                node.emit_mycroft(Message("ovos.common_play.shuffle.unset"))
            elif action == "repeat.set":
                node.emit_mycroft(Message("ovos.common_play.repeat.set"))
            elif action == "repeat.unset":
                node.emit_mycroft(Message("ovos.common_play.repeat.unset"))
            elif action == "repeat.one":
                node.emit_mycroft(Message("ovos.common_play.repeat.one"))
            else:
                print("Unknown command or missing argument")
        except KeyboardInterrupt:
            print("\nExiting.")
            break
        except Exception:
            LOG.exception("An error occurred in interactive mode")
            break

    node.close()
    click.echo("Connection closed.")


@cli.command()
@click.argument("uri")
@click.pass_obj
def play(node: HiveMessageBusClient, uri: str):
    """Starts playback of the given URI."""
    click.echo(f"Sending 'play' command for {uri}...")
    node.emit_mycroft(_get_play_message(uri))
    click.echo("Command sent.")


@cli.command()
@click.pass_obj
def pause(node: HiveMessageBusClient):
    """Pauses the current playback."""
    click.echo("Sending 'pause' command...")
    node.emit_mycroft(Message("ovos.common_play.pause"))
    click.echo("Command sent.")


@cli.command()
@click.pass_obj
def resume(node: HiveMessageBusClient):
    """Resumes the current playback."""
    click.echo("Sending 'resume' command...")
    node.emit_mycroft(Message("ovos.common_play.resume"))
    click.echo("Command sent.")


@cli.command(name="next")
@click.pass_obj
def next_cmd(node: HiveMessageBusClient):
    """Skips to the next track in the playlist."""
    click.echo("Sending 'next' command...")
    node.emit_mycroft(Message("ovos.common_play.next"))
    click.echo("Command sent.")


@cli.command(name="prev")
@click.pass_obj
def prev_cmd(node: HiveMessageBusClient):
    """Returns to the previous track in the playlist."""
    click.echo("Sending 'prev' command...")
    node.emit_mycroft(Message("ovos.common_play.prev"))
    click.echo("Command sent.")


@cli.command(name="shuffle.set")
@click.pass_obj
def shuffle_set(node: HiveMessageBusClient):
    """Enables shuffle mode."""
    click.echo("Sending 'shuffle.set' command...")
    node.emit_mycroft(Message("ovos.common_play.shuffle.set"))
    click.echo("Command sent.")


@cli.command(name="shuffle.unset")
@click.pass_obj
def shuffle_unset(node: HiveMessageBusClient):
    """Disables shuffle mode."""
    click.echo("Sending 'shuffle.unset' command...")
    node.emit_mycroft(Message("ovos.common_play.shuffle.unset"))
    click.echo("Command sent.")


@cli.command(name="repeat.set")
@click.pass_obj
def repeat_set(node: HiveMessageBusClient):
    """Enables repeat all mode."""
    click.echo("Sending 'repeat.set' command...")
    node.emit_mycroft(Message("ovos.common_play.repeat.set"))
    click.echo("Command sent.")


@cli.command(name="repeat.unset")
@click.pass_obj
def repeat_unset(node: HiveMessageBusClient):
    """Disables repeat mode."""
    click.echo("Sending 'repeat.unset' command...")
    node.emit_mycroft(Message("ovos.common_play.repeat.unset"))
    click.echo("Command sent.")


@cli.command(name="repeat.one")
@click.pass_obj
def repeat_one(node: HiveMessageBusClient):
    """Enables repeat single-track mode."""
    click.echo("Sending 'repeat.one' command...")
    node.emit_mycroft(Message("ovos.common_play.repeat.one"))
    click.echo("Command sent.")


if __name__ == "__main__":
    cli()

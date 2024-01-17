import os
from dataclasses import dataclass
from typing import Optional

import discord
from pyarr import RadarrAPI, SonarrAPI

from radarr import MovieSelectView, get_movie
from sonarr import SeriesSelectView, get_series

intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = discord.app_commands.CommandTree(client)
guild_id = None

@dataclass
class Command:
    name: str
    rootfolderpath: str
    qualityprofile: str

def sync_commands(command_type: str, command: list, config: dict[str, str]):
    if command_type == "SONARR":
        sonarr = SonarrAPI(config["url"], config["api_key"])
    elif command_type == "RADARR":
        radarr = RadarrAPI(config["url"], config["api_key"])

    async def command_func(interaction, title: str, quality_profile: Optional[str] = command.qualityprofile, root_folder_path: Optional[str] = command.rootfolderpath):
        if command_type == "SONARR":
            entries = get_series(title, sonarr)
            view = SeriesSelectView(series_found=entries, quality_profile=quality_profile, root_folder_path=root_folder_path)
        elif command_type == "RADARR":
            entries = get_movie(title, radarr)
            view = MovieSelectView(movies_found=entries, quality_profile=quality_profile, root_folder_path=root_folder_path)

        if entries:
            await interaction.response.send_message(f"Select an item", view=view)
        else:
            await interaction.response.send_message(f"No item found with the name \"{title}\". Please make sure you spelled it correctly.")

    print(f"Added command: {command.name}")
    tree.command(name=command.name)(command_func)


@client.event
async def on_ready():
    await tree.sync()
    print("Seekarr is online!")

def add_commands(command_type: str):
    command_envs = [env for env in os.environ if env.startswith(f"{command_type}_")]
    if command_envs:
        command_url = os.environ[f"{command_type}_URL"]
        command_api_key = os.environ[f"{command_type}_API_KEY"]

        # get any command prefixed with {command_type}_COMMAND_
        commands = [command for command in command_envs if command.startswith(f"{command_type}_COMMAND_")]
        if len(commands) > 0:
            for command in commands:
                fields = os.environ[command].split(",")
                command = Command(name=fields[0], rootfolderpath=fields[1], qualityprofile=fields[2])
                sync_commands(command_type, command, {"url": command_url, "api_key": command_api_key})
        else:
            raise Exception(f"No {command_type} commands found. Please set at least one {command_type} command.\nExample: {command_type}_COMMAND_TV request-media,/media,Any")

if __name__ == "__main__":
    try:
        discord_token = os.environ["DISCORD_TOKEN"]
    except KeyError:
        raise Exception("DISCORD_TOKEN environment variable not set. Please set it to your discord bot token.")

    if os.environ.get("GUILD_ID"):
        guild_id = int(os.environ["GUILD_ID"])

    add_commands("SONARR")
    add_commands("RADARR")

    client.run(discord_token)

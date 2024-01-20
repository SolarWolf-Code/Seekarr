import os
from dataclasses import dataclass
import asyncio

import discord
from pyarr import RadarrAPI, SonarrAPI

from radarr import MovieSelectView, get_movie
from sonarr import SeriesSelectView, get_series
from utils import notification_agents

@dataclass
class Command:
    name: str
    rootfolderpath: str
    qualityprofile: str


intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = discord.app_commands.CommandTree(client)
guild_id = None

radarr = None
sonarr = None

def check_movie_downloaded(movie_info: dict) -> bool:
    movie = radarr.get_movie(id_=movie_info["tmdbId"], tmdb=True)[0]
    if movie["hasFile"]:
        return True

    return False


async def check_downloads():
    while True:
        print(f"Checking downloads | {len(notification_agents)}")
        await asyncio.sleep(5)
        for agent in notification_agents:
            if agent.instance_type == "Radarr":
                print(f"Checking {agent.info['title']}")
                if check_movie_downloaded(agent.info):
                    # send message to each channel. include all users in message for that given channel
                    for channel_id, members in agent.notified_members.items():
                        channel = client.get_channel(channel_id)
                        members_to_mention = " ".join([member.mention for member in members])
                        await channel.send(content=f"{members_to_mention} {agent.info['title']} has finished downloading!", embed=agent.embed)

                    notification_agents.remove(agent)

            elif agent.instance_type == "Sonarr":
                # TODO: check if series is downloaded
                pass

def sync_commands(command_type: str, command: list, config: dict[str, str]):
    global sonarr
    global radarr

    if command_type == "SONARR":
        if not sonarr:
            sonarr = SonarrAPI(config["url"], config["api_key"])
    elif command_type == "RADARR":
        if not radarr:
            radarr = RadarrAPI(config["url"], config["api_key"])

    async def command_func(interaction, title: str):
        if command_type == "SONARR":
            entries = get_series(title, sonarr)
            view = SeriesSelectView(series_found=entries, quality_profile=command.qualityprofile, root_folder_path=command.rootfolderpath)
        elif command_type == "RADARR":
            entries = get_movie(title, radarr)
            view = MovieSelectView(movies_found=entries, quality_profile=command.qualityprofile, root_folder_path=command.rootfolderpath)

        if entries:
            await interaction.response.send_message(f"Select an item", view=view)
        else:
            await interaction.response.send_message(f"No item found with the name \"{title}\". Please make sure you spelled it correctly.")

    print(f"Added command: {command.name}")
    if guild_id:
        tree.command(name=command.name, guild=discord.Object(id=guild_id))(command_func)
    else:
        tree.command(name=command.name)(command_func)


@client.event
async def on_ready():
    if guild_id:
        await tree.sync(guild=discord.Object(id=guild_id))
    else:
        await tree.sync()

    # create new task to check downloads
    asyncio.create_task(check_downloads())

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

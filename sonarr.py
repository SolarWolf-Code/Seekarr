import discord
from typing import Optional
from get_env import get_sonarr_commands, get_son_base_envs
from pyarr import SonarrAPI

discord_token = ""
sonarr_url = ""
sonarr_port = 0
sonarr_api_key = ""
sonarr = None

intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = discord.app_commands.CommandTree(client)


def get_series(title: str):
    series = sonarr.lookup_series(term=title)
    return series[:25]

def series_already_monitored(tvdbid: int):
    series = sonarr.get_series(id_=tvdbid, tvdb=True)
    if series:
        return True
    
    return False

class RequestSeasonsButton(discord.ui.Button):
    def __init__(self, series, already_monitored, seasons, quality_profile, root_folder_path):
        self.series = series
        self.seasons = seasons
        self.already_monitored = already_monitored
        self.quality_profile = quality_profile
        self.root_folder_path = root_folder_path
        super().__init__(label='Request', style=discord.ButtonStyle.primary)


    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()

        quality_profiles = sonarr.get_quality_profile()
        quality_profile_id = next(profile["id"] for profile in quality_profiles if profile["name"] == self.quality_profile)

        self.series["qualityProfileId"] = quality_profile_id
        self.series["rootFolderPath"] = self.root_folder_path

        if not self.already_monitored:
            for season in self.series["seasons"]:
                season["monitored"] = False

        for season in self.seasons:
            season_info = next(season_info for season_info in self.series["seasons"] if season_info["seasonNumber"] == int(season))
            season_info["monitored"] = True

        if self.already_monitored:
            sonarr.upd_series(self.series)
        else:
            # TODO: get language profile and pass it to add_series
            sonarr.add_series(self.series, quality_profile_id, 1, self.root_folder_path)


class SeasonSelect(discord.ui.Select):
    def __init__(self, series, already_monitored, quality_profile, root_folder_path):
        self.series = series
        self.quality_profile = quality_profile
        self.root_folder_path = root_folder_path
        self.already_monitored = already_monitored

        self.seasons = series["seasons"]
        seasons = []
        season_count = 1
        if len(self.seasons) > 1:
            season_count = len(self.seasons) - 1
            seasons.append(discord.SelectOption(label="All Seasons", value="all"))
        for season in self.seasons:
            if season["monitored"] and already_monitored:
                seasons.append(discord.SelectOption(label=f"Season {season['seasonNumber']}", value=str(season['seasonNumber']), emoji='✅'))
            else:
                seasons.append(discord.SelectOption(label=f"Season {season['seasonNumber']}", value=str(season['seasonNumber']), emoji='❌'))

        super().__init__(placeholder="Select a season", min_values=1, max_values=season_count, options=seasons)

    async def callback(self, interaction: discord.Interaction):
        selected_seasons = sorted(self.values)
        self.placeholder = ", ".join(selected_seasons)

        button = RequestSeasonsButton(self.series, self.already_monitored, selected_seasons, self.quality_profile, self.root_folder_path)
        for item in list(self.view.children):
            if isinstance(item, discord.ui.Button):
                self.view.remove_item(item)
        
        self.view.add_item(button)

        await interaction.response.edit_message(view=self.view)

class SelectMenu(discord.ui.Select):
    def __init__(self, series, quality_profile, root_folder_path):
        self.series = series
        self.quality_profile = quality_profile
        self.root_folder_path = root_folder_path
        options = []
        for index, entry in enumerate(series):
            options.append(discord.SelectOption(label=entry["title"], value=str(index), description=entry["year"]))

        super().__init__(placeholder="Select a series", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        selected_series = int(self.values[0])
        selected_series_info = self.series[selected_series]
        self.placeholder = selected_series_info["title"]

        embed = discord.Embed(
            title=f"{selected_series_info['title']} ({selected_series_info['year']})",
            url=f"https://www.theseriesdb.org/series/{selected_series_info['tvdbId']}",
            description=selected_series_info['overview'],
            color=0x3498db
        )
        embed.set_thumbnail(url="https://thetvdb.com/images/logo.png")

        if selected_series_info.get("remotePoster"):
            embed.set_image(url=selected_series_info["remotePoster"])

        for item in list(self.view.children):
            if isinstance(item, discord.ui.Button):
                self.view.remove_item(item)
            if isinstance(item, discord.ui.Select) and item != self:
                self.view.remove_item(item)

        selected_series_info["seasons"] = [season for season in selected_series_info["seasons"] if season["seasonNumber"] != 0]

        self.view.add_item(SeasonSelect(selected_series_info, series_already_monitored(selected_series_info["tvdbId"]), self.quality_profile, self.root_folder_path))

        await interaction.response.edit_message(content=f"{selected_series_info['title']} is not downloaded or requested. Would you like to request it?", embed=embed, view=self.view)
            

class SelectView(discord.ui.View):
    def __init__(self, *, timeout = 180, seriess_found, quality_profile, root_folder_path):
        super().__init__(timeout=timeout)
        self.add_item(SelectMenu(seriess_found, quality_profile, root_folder_path))

@client.event
async def on_ready():
    global sonarr
    sonarr_commands = get_sonarr_commands()
    if not sonarr_commands:
        print("No sonarr commands found. Exiting...")
        exit(1)

    sonarr = SonarrAPI(sonarr_url, sonarr_api_key)

    for command in sonarr_commands:
        async def command_func(interaction, title: str, quality_profile: Optional[str] = command.qualityprofile, root_folder_path: Optional[str] = command.rootfolderpath):
            seriess = get_series(title)
            if seriess:
                await interaction.response.send_message("Select a series", view=SelectView(seriess_found=seriess, quality_profile=quality_profile, root_folder_path=root_folder_path))
            else:
                await interaction.response.send_message(f"No series found with the name \"{title}\". Please make sure you spelled it correctly.")

        print(f"Adding command: {command.name}")
        tree.command(name=command.name)(command_func)

    await tree.sync()
    print("Seekarr is online!")


if __name__ == "__main__":
    discord_token, sonarr_url, sonarr_api_key = get_son_base_envs()
    client.run(discord_token)

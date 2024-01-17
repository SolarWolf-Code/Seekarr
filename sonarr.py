import discord
from pyarr import SonarrAPI

sonarr = None

def get_series(title: str, sonarr_instance: SonarrAPI):
    global sonarr
    sonarr = sonarr_instance
    series = sonarr.lookup_series(term=title)
    return series[:25]

def series_already_monitored(tvdbid: int):
    series = sonarr.get_series(id_=tvdbid, tvdb=True)
    if series:
        return True
    
    return False

class RequestSeasonsButton(discord.ui.Button):
    def __init__(self, series, already_monitored, seasons, pretty_seasons,quality_profile, root_folder_path):
        self.series = series
        self.seasons = seasons
        self.pretty_seasons = pretty_seasons
        self.already_monitored = already_monitored
        self.quality_profile = quality_profile
        self.root_folder_path = root_folder_path
        super().__init__(label='Request', style=discord.ButtonStyle.primary)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()

        quality_profiles = sonarr.get_quality_profile()
        quality_profile_id = next(profile["id"] for profile in quality_profiles if profile["name"] == self.quality_profile)


        if not self.already_monitored:
            for season in self.series["seasons"]:
                season["monitored"] = False

        if "all" not in self.seasons:
            for season in self.seasons:
                season_info = next(season_info for season_info in self.series["seasons"] if season_info["seasonNumber"] == int(season))
                season_info["monitored"] = True
        else:
            for season in self.series["seasons"]:
                if season["seasonNumber"] != 0:
                    season["monitored"] = True

        if self.already_monitored:
            sonarr.upd_series(self.series)
        else:
            sonarr.add_series(self.series, quality_profile_id, 1, self.root_folder_path, ignore_episodes_with_files=True, search_for_missing_episodes=True)
        
        self.label = "Requested"
        self.disabled = True

        await interaction.message.edit(content=f"Successfully requested {self.pretty_seasons} from {self.series['title']}!", view=self.view)

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
            season_count = len(self.seasons)
            seasons.append(discord.SelectOption(label="All Seasons", value="all"))

        for season in self.seasons:
            if season["monitored"] and already_monitored:
                seasons.append(discord.SelectOption(label=f"Season {season['seasonNumber']}", value=str(season['seasonNumber']), emoji='✅'))
            else:
                seasons.append(discord.SelectOption(label=f"Season {season['seasonNumber']}", value=str(season['seasonNumber']), emoji='❌'))

        super().__init__(placeholder="Select a season", min_values=1, max_values=season_count, options=seasons)

    async def callback(self, interaction: discord.Interaction):
        selected_seasons = sorted(self.values)
        self.placeholder = "All Seasons" if "all" in selected_seasons else ", ".join(f"Season {season}" for season in selected_seasons)

        if "All Seasons" not in self.placeholder:
            pretty_seasons = [season.replace("Season ", "") for season in self.placeholder.split(", ")]
            if len(pretty_seasons) > 2:
                pretty_seasons[-1] = "and " + pretty_seasons[-1]
                pretty_seasons = "season(s) " + ", ".join(pretty_seasons)
            else:
                pretty_seasons = "season(s) " + " and ".join(pretty_seasons)
        else:
            pretty_seasons = "all seasons"

        button = RequestSeasonsButton(self.series, self.already_monitored, selected_seasons, pretty_seasons, self.quality_profile, self.root_folder_path)
        for item in list(self.view.children):
            if isinstance(item, discord.ui.Button):
                self.view.remove_item(item)
        
        self.view.add_item(button)

        # TODO: handle seasons that are already monitored
        await interaction.response.edit_message(content=f"Would you like to request {pretty_seasons} from {self.series['title']}?", view=self.view)

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

        description = ""
        if selected_series_info.get("overview"):
            if len(selected_series_info["overview"]) > 255:
                description = selected_series_info["overview"][:255] + "(...)"
            else:
                description = selected_series_info["overview"]

        embed = discord.Embed(
            title=f"{selected_series_info['title']} ({selected_series_info['year']})",
            url=f"https://www.theseriesdb.org/series/{selected_series_info['tvdbId']}",
            description=description,
            color=0x3498db
        )
        embed.set_thumbnail(url="https://thetvdb.com/images/logo.png")
        embed.set_footer(text=f"Powered by Seekarr")

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
            

class SeriesSelectView(discord.ui.View):
    def __init__(self, *, timeout = 180, series_found, quality_profile, root_folder_path):
        super().__init__(timeout=timeout)
        self.add_item(SelectMenu(series_found, quality_profile, root_folder_path))
import requests
import discord
from typing import Optional
from get_env import get_radarr_commands, get_base_envs

discord_token = ""
radarr_url = ""
radarr_port = 0
radarr_api_key = ""

intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = discord.app_commands.CommandTree(client)

def get_movie(title: str):
    headers = {'X-Api-Key': radarr_api_key}
    req = requests.get(f"{radarr_url}:{radarr_port}/api/v3/movie/lookup?term={title}", headers=headers)

    movies = []
    for entry in req.json():
        movies.append(entry)

    return movies

class RequestButton(discord.ui.Button):
    def __init__(self, movie, quality_profile, root_folder_path):
        self.movie = movie
        self.quality_profile = quality_profile
        self.root_folder_path = root_folder_path
        super().__init__(label='Request', style=discord.ButtonStyle.primary)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()

        req = requests.get(f"{radarr_url}:{radarr_port}/api/v3/qualityProfile", headers={'X-Api-Key': radarr_api_key})
        quality_profiles = req.json()
        quality_profile_id = next(profile["id"] for profile in quality_profiles if profile["name"] == self.quality_profile)

        headers = {'X-Api-Key': radarr_api_key, 'Content-Type': 'application/json'}
        data = {
            "title": self.movie["title"], 
            "qualityProfileId": quality_profile_id,
            "monitored": True,
            "minimumAvailability": "announced",
            "isAvailable": True,
            "tmdbId": self.movie["tmdbId"],
            "id": 0,
            "addOptions": {
                "monitor": "movieOnly",
                "searchForMovie": True,
            },
            "rootFolderPath": self.root_folder_path 
        }
        req = requests.post(f"{radarr_url}:{radarr_port}/api/v3/movie", headers=headers, json=data)
        if req.status_code == 201:
            self.label = "Requested"
            self.disabled = True
            await interaction.message.edit(content=f"Successfully requested {self.movie['title']} ({self.movie['year']})!", view=self.view)
        else:
            self.label = "Failed"
            self.style = discord.ButtonStyle.danger
            self.disabled = True

            await interaction.message.edit(content=f"Failed to request {self.movie['title']} ({self.movie['year']}). Please try again later.", view=self.view)


class SelectMenu(discord.ui.Select):
    def __init__(self, movies, quality_profile, root_folder_path):
        self.movies = movies
        self.quality_profile = quality_profile
        self.root_folder_path = root_folder_path
        options = []
        for movie in movies:
            options.append(discord.SelectOption(label=f"{movie['title']} ({movie['year']})"))

        super().__init__(placeholder="Select a movie", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        selected_movie = self.values[0]
        self.placeholder = selected_movie

        selected_movie_info = next(movie for movie in self.movies if f"{movie['title']} ({movie['year']})" == selected_movie)

        embed = discord.Embed(
            title=f"{selected_movie_info['title']} ({selected_movie_info['year']})",
            url=f"https://www.themoviedb.org/movie/{selected_movie_info['tmdbId']}",
            description=selected_movie_info['overview'],
            color=0x3498db
        )
        embed.set_thumbnail(url="https://i.imgur.com/44ueTES.png")
        embed.set_image(url=selected_movie_info['images'][0]["remoteUrl"])

        for item in list(self.view.children):
            if isinstance(item, discord.ui.Button):
                self.view.remove_item(item)

        if selected_movie_info["hasFile"]:
            # this means it is already downloaded.
            button = discord.ui.Button(label='Available', style=discord.ButtonStyle.primary, disabled=True)
            self.view.add_item(button)
            await interaction.response.edit_message(content=f"{selected_movie} has already been downloaded. Enjoy!", embed=embed, view=self.view)
        elif selected_movie_info["monitored"]:
            # this means it is already requested.
            button = discord.ui.Button(label='Requested', style=discord.ButtonStyle.primary, disabled=True)
            self.view.add_item(button)
            await interaction.response.edit_message(content=f"{selected_movie} was already requested. Please wait for it to be available", embed=embed, view=self.view)
        else:
            # this means it is not requested or downloaded.
            button = RequestButton(selected_movie_info, self.quality_profile, self.root_folder_path)
            self.view.add_item(button)
            await interaction.response.edit_message(content=f"{selected_movie} is not downloaded or requested. Would you like to request it?", embed=embed, view=self.view)
            

class SelectView(discord.ui.View):
    def __init__(self, *, timeout = 180, movies_found, quality_profile, root_folder_path):
        super().__init__(timeout=timeout)
        self.add_item(SelectMenu(movies_found, quality_profile, root_folder_path))


@client.event
async def on_ready():
    radarr_commands = get_radarr_commands()
    if not radarr_commands:
        print("No radarr commands found. Exiting...")
        exit(1)

    for command in radarr_commands:
        async def command_func(interaction, title: str, quality_profile: Optional[str] = command.qualityprofile, root_folder_path: Optional[str] = command.rootfolderpath):
            movies = get_movie(title)
            if movies:
                await interaction.response.send_message("Select a movie", view=SelectView(movies_found=movies, quality_profile=quality_profile, root_folder_path=root_folder_path))
            else:
                await interaction.response.send_message(f"No movies found with the name \"{title}\". Please make sure you spelled it correctly.")

        tree.command(name=command.name)(command_func)

    await tree.sync()
    print("Seekarr is online!")


if __name__ == "__main__":
    discord_token, radarr_url, radarr_port, radarr_api_key = get_base_envs()
    client.run(discord_token)

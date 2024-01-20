import discord
from pyarr import RadarrAPI

from notifications import NotificationAgent, notification_agents

radarr = None

def get_movie(title: str, radarr_instance: RadarrAPI):
    global radarr
    radarr = radarr_instance
    movies = radarr.lookup_movie(term=title)
    return movies[:25]

def check_movie_downloaded(movie_info: dict) -> bool:
    movie = radarr.get_movie(id_=movie_info["tmdbId"], tmdb=True)[0]
    if movie["hasFile"]:
        return True

    return False

class RequestButton(discord.ui.Button):
    def __init__(self, movie, quality_profile, root_folder_path, embed):
        self.movie = movie
        self.quality_profile = quality_profile
        self.root_folder_path = root_folder_path
        self.embed = embed
        super().__init__(label='Request', style=discord.ButtonStyle.primary)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()

        # get quality profiles
        quality_profiles = radarr.get_quality_profile()
        quality_profile_id = int(next(profile["id"] for profile in quality_profiles if profile["name"] == self.quality_profile))

        radarr.add_movie(self.movie, quality_profile_id=quality_profile_id, root_dir=self.root_folder_path, search_for_movie=True)

        self.label = "Requested"
        self.disabled = True

        agent = NotificationAgent(instance_type="Radarr")
        agent.info = self.movie
        agent.add_member(interaction.user, interaction.channel_id)
        agent.embed = self.embed
        notification_agents.append(agent)

        await interaction.message.edit(content=f"Successfully requested **{self.movie['title']}**!", view=self.view)


class SelectMenu(discord.ui.Select):
    def __init__(self, movies, quality_profile, root_folder_path):
        self.movies = movies
        self.quality_profile = quality_profile
        self.root_folder_path = root_folder_path
        options = []
        for index, entry in enumerate(movies):
            options.append(discord.SelectOption(label=entry["title"], value=str(index), description=entry["year"]))

        super().__init__(placeholder="Select a movie", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        selected_movie = int(self.values[0])
        selected_movie_info = self.movies[selected_movie]
        self.placeholder = selected_movie_info["title"]

        description = ""
        if selected_movie_info.get("overview"):
            if len(selected_movie_info["overview"]) > 255:
                description = selected_movie_info["overview"][:255] + "(...)"
            else:
                description = selected_movie_info["overview"]

        embed = discord.Embed(
            title=f"{selected_movie_info['title']}",
            url=f"https://www.themoviedb.org/movie/{selected_movie_info['tmdbId']}",
            description=description,
            color=0x3498db
        )
        # <t:1705463340:f>
        embed.set_thumbnail(url="https://i.imgur.com/44ueTES.png")
        embed.set_footer(text=f"Powered by Seekarr")

        if selected_movie_info.get("remotePoster"):
            embed.set_image(url=selected_movie_info["remotePoster"])
        
        # remove old buttons
        for item in list(self.view.children):
            if isinstance(item, discord.ui.Button):
                self.view.remove_item(item)

        if check_movie_downloaded(selected_movie_info):
            # this means it is already downloaded.
            button = discord.ui.Button(label='Available', style=discord.ButtonStyle.primary)
            button.disabled = True
            self.view.add_item(button)
            await interaction.response.edit_message(content=f"**{selected_movie_info['title']}** has already been downloaded. Enjoy!", embed=embed, view=self.view)
        elif selected_movie_info["monitored"]:
            # check if the user is already in the notification agent list
            agent = next((agent for agent in notification_agents if agent.info["tmdbId"] == selected_movie_info["tmdbId"]), None)
            if agent:
                if interaction.user not in agent.notified_members[interaction.channel_id]:
                    agent.add_member(interaction.user, interaction.channel_id)

                await interaction.response.edit_message(content=f"**{selected_movie_info['title']}** is already requested. You will be notified when it is available.", embed=embed, view=self.view)

            else:
                # this means it was already requests but the bot likely lost connection and the notification agent was removed.
                agent = NotificationAgent(instance_type="Radarr")
                agent.info = selected_movie_info
                agent.add_member(interaction.user, interaction.channel_id)
                agent.embed = embed
                notification_agents.append(agent)

                button = discord.ui.Button(label='Requested', style=discord.ButtonStyle.primary)
                button.disabled = True
                self.view.add_item(button)
                await interaction.response.edit_message(content=f"**{selected_movie_info['title']}** was already requested. Please wait for it to be available", embed=embed, view=self.view)
        else:
            # this means it is not requested or downloaded.
            button = RequestButton(selected_movie_info, self.quality_profile, self.root_folder_path, embed)
            self.view.add_item(button)
            await interaction.response.edit_message(content=f"**{selected_movie_info['title']}** is not downloaded or requested. Would you like to request it?", embed=embed, view=self.view)
            
class MovieSelectView(discord.ui.View):
    def __init__(self, *, timeout = 180, movies_found, quality_profile, root_folder_path):
        super().__init__(timeout=timeout)
        self.add_item(SelectMenu(movies_found, quality_profile, root_folder_path))
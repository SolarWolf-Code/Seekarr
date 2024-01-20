import discord
from dataclasses import dataclass, field

@dataclass
class NotificationAgent:
    instance_type: str # Sonarr or Radarr
    notified_members: dict[str, list[discord.Member]] = field(default_factory=dict)
    embed: discord.Embed = None
    info: dict = None

    def add_member(self, member: discord.Member, channel_id: int):
        if channel_id not in self.notified_members:
            self.notified_members[channel_id] = []

        self.notified_members[channel_id].append(member)
        

notification_agents: list[NotificationAgent] = []
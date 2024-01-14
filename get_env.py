import os
from dataclasses import dataclass

@dataclass
class Command:
    name: str
    rootfolderpath: str
    qualityprofile: str

def get_radarr_commands():
    radarr_commands = []
    for var in os.environ:
        if var.startswith("RADARR_COMMAND_"):
            fields = os.environ[var].split(",")
            radarr_commands.append(Command(name=fields[0], rootfolderpath=fields[1], qualityprofile=fields[2]))

    return radarr_commands

def get_base_envs():
    base_envs = ["DISCORD_TOKEN","RADARR_URL","RADARR_PORT", "RADARR_API_KEY"]
    envs = []
    for env in base_envs:
        try:
            envs.append(os.environ[env])
        except KeyError:
            print(f"Missing environment variable: {env}")
            exit(1)
    
    return envs

if __name__ == "__main__":
    get_base_envs()
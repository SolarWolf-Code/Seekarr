# Seekarr

Seekarr is a simple discord bot that allows you to request media to your Radarr and Sonarr instances. It is written in Python using the discord.py library.

## Installation
``` shell
docker pull solarwolf/seekarr:latest
```

## Configuration
The bot is configured using environment variables. `DISCORD_TOKEN` is the only required variable.  

If you wish to use Radarr, you'll need to provide the following variables:
- `RADARR_URL` - The URL of your Radarr instance (e.g. `http://localhost:7878`)
- `RADARR_API_KEY` - The API key for your Radarr instance

If you wish to use Sonarr, you'll need to provide the following variables:
- `SONARR_URL` - The URL of your Sonarr instance (e.g. `http://localhost:8989`)
- `SONARR_API_KEY` - The API key for your Sonarr instance

To add any number of commands to the bot, you'll need to prefix the instance type + `_COMMAND_` (e.g. `RADARR_COMMAND_1`). The value of each command is a comma separated list which consists of the following:
- Command name - the actual command that will be used in discord (e.g. `request-movie`)
- Root Folder Path - the root folder path for the command (e.g. `/media/movies`)
- Quality Profile Name - the quality profile name for the command (e.g. `4K`)

Lastly, if you'd like to only run this in a single server, you can provide the following variable:
- `GUILD_ID` - The ID of the guild you'd like to run the bot in

### Example
``` shell
export DISCORD_TOKEN=1234567890

export RADARR_URL=http://localhost:7878
export RADARR_API_KEY=1234567890
export RADARR_COMMAND_1=request-movie,/media/movies,4k

export SONARR_URL=http://localhost:8989
export SONARR_API_KEY=1234567890
export SONARR_COMMAND_1=request-tv,/media/tv,4K
```

## TODO
- Add `In Theaters` field to embed
- Add check for if all seasons are already monitored
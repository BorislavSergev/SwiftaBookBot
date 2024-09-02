import discord
from discord.ext import commands
import json
import traceback
import asyncio

# Load configuration data
with open("config.json", "r", encoding="utf-8") as file:
    configData = json.load(file)

intents = discord.Intents.default()
intents.members = True
intents.voice_states = True  # Ensure voice state updates are enabled

bot = commands.Bot(command_prefix=commands.when_mentioned, sync_commands_debug=True, intents=intents)

def load_extensions():
    initial_extensions = [
        "cogs.testcommandone",
        "cogs.welcome",
        "cogs.ticket_system",
        "cogs.task_management"

    ]

    for extension in initial_extensions:
        if extension in bot.extensions:
            print(f"Extension '{extension}' is already loaded.")
            continue
        try:
            bot.load_extension(extension)
            print(f"[LOADED] {extension}")
        except Exception as e:
            print(f"Failed to load extension {extension}: {e}")
            traceback.print_exc()

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    # Load extensions after the bot is ready
    load_extensions()

# Run the bot with the token
async def main():
    async with bot:
        load_extensions()
        await bot.start(configData["token"])

# Run the bot using asyncio.run
if __name__ == "__main__":
    asyncio.run(main())

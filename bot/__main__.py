import nextcord
from nextcord.ext import commands  # type: ignore

from . import cogs
from .config import TOKEN

intents = nextcord.Intents.default()

bot = commands.Bot(command_prefix=commands.when_mentioned, intents=intents)
bot.remove_command("help")

cogs_list = [
    cogs.player,
]

for cog in cogs_list:
    cog.setup(bot)


@bot.event
async def on_ready():
    """При включении бота"""
    bot.add_all_cog_commands()

    activity = nextcord.Game(name="hyperpop?", type=3)
    await bot.change_presence(status=nextcord.Status.idle, activity=activity)
    print(
        f"Bot started at {bot.user.name}#{bot.user.discriminator}\n| {TOKEN=}",
    )


bot.run(TOKEN)

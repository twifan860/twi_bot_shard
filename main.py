import sys
import traceback
from itertools import cycle

import asyncpg
import discord
from discord.ext import commands, tasks

import secrets

bot = commands.Bot(
    command_prefix='!',
    description="The wandering inn bot",
    case_insensitive=True, )

cogs = ['cogs.gallery', 'cogs.links_tags', 'cogs.patreon_poll', 'cogs.twi', 'cogs.owner', 'cogs.other']


@bot.event
async def on_ready():
    print(f'Logged in as: {bot.user.name}\nVersion: {discord.__version__}\n')
    for extension in cogs:
        try:
            bot.load_extension(extension)
        except Exception as e:
            print(f'Failed to load extension {extension}.', file=sys.stderr)
            traceback.print_exc()


async def create_db_pool():
    bot.pg_con = await asyncpg.create_pool(database="testDB", user=secrets.DB_user, password=secrets.DB_pass)


status = cycle(["Killing the mages of Wistram",
                "Cleaning up a mess",
                "Keeping secrets",
                "Hiding corpses",
                "Mending Pirateaba's broken hands",
                "Longing for Zelkyr",
                "Banishing Chimera to #debates",
                "Hoarding knowledge",
                "Dusting off priceless artifacts",
                "Praying for Mating Rituals 2"])


@tasks.loop(seconds=10)
async def status_loop():
    await bot.change_presence(activity=discord.Game(next(status)))


# @bot.event
# async def on_command_error(ctx, error):
#     if hasattr(ctx.command, "on_error"):
#         return
#     elif isinstance(error, commands.MissingRequiredArgument):
#         await ctx.send("Please pass an argument")
#     elif isinstance(error, commands.NotOwner):
#         await ctx.send(f"Sorry {ctx.author.display_name} only ~~Zelkyr~~ Sara may do that.")
#     elif isinstance(error, commands.MissingRole):
#         await ctx.send("I'm sorry, you don't seem to have the required role for that")
#     elif isinstance(error, commands.CommandOnCooldown):
#         await ctx.send(f"That command is on cooldown, please wait a bit.")


# TODO: Allow to switch page (show more results) on !find

bot.loop.run_until_complete(create_db_pool())
bot.run(secrets.bot_token)

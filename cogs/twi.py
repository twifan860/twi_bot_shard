import json

import aiohttp
import discord
from discord.ext import commands
from googleapiclient.discovery import build

import secrets
from cogs.patreon_poll import fetch


def google_search(search_term, api_key, cse_id, **kwargs):
    service = build("customsearch", "v1", developerKey=api_key)
    res = service.cse().list(q=search_term, cx=cse_id, num=5, **kwargs).execute()
    return res


async def is_bot_channel(ctx):
    return ctx.channel.id == 361694671631548417


class TwiCog(commands.Cog, name="The Wandering Inn"):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(
        name="Password",
        description="Provides information for patreons on how to get the chapter password",
        aliases=['pw'],
        hidden=False,
    )
    async def password(self, ctx):
        await ctx.send("3 ways.\n"
                       "1. Link discord to patreon and go to <#346842161704075265> and check pins.\n"
                       "2. go to <https://www.patreon.com/pirateaba> and check the latest posts. It has the password.")
        embed = discord.Embed(title="password")
        embed.set_image(url="https://cdn.discordapp.com/attachments/362248294849576960/638350570972774440/unknown.png")
        await ctx.send(embed=embed)
        await ctx.send("3. You will get an email with the password every time pirate posts it.")

    @commands.command(
        name="ConnectDiscord",
        description="Provides information for patreons on how to connect their patreon account to discord.",
        aliases=['cd'],
        hidden=False,
    )
    async def connect_discord(self, ctx):
        await ctx.send(
            "Check this link: <https://support.patreon.com/hc/en-us/articles/212052266-How-do-I-receive-my-Discord-role>")

    @commands.command(
        name="Wiki",
        description="Searches the The Wandering Inn wiki for a matching article.",
        aliases=['w'],
        usage='[Query]',
        hidden=False,
    )
    async def wiki(self, ctx, *, query):
        url = f"https://thewanderinginn.fandom.com/api/v1/Search/List?query={query}&limit=1&minArticleQuality=0"
        async with aiohttp.ClientSession() as session:
            html = await fetch(session, url)
            json_data = json.loads(html)
        try:
            await ctx.send(
                f"Results from search **{query}**\n{json_data['items'][0]['title']} - {json_data['items'][0]['url']}")
        except IndexError:
            url = f"https://thewanderinginn.fandom.com/api/v1/SearchSuggestions/List?query={query}"
            async with aiohttp.ClientSession() as session:
                html = await fetch(session, url)
                json_data = json.loads(html)
            try:
                await ctx.send(
                    f"Sorry, i could not find a article matching that search. You could try: {json_data['items'][0]['title']}")
            except IndexError:
                await ctx.send(f"Sorry, i could not find a article matching that search.")

    @commands.command(
        name="Find",
        description="Does a google search on 'Wanderinginn.com' and returns the results",
        aliases=['F'],
        usage='[Query]',
        hidden=False,
    )
    @commands.check(is_bot_channel)
    async def find(self, ctx, *, query):
        results = google_search(query, secrets.google_api_key, secrets.google_cse_id)
        if results['searchInformation']['totalResults'] == "0":
            await ctx.send("I could not find anything that matches your search.")
        else:
            embed = discord.Embed(title="Search", description=f"**{query}**")
            for result in results['items']:
                embed.add_field(name=result['title'],
                                value=f"{result['snippet']}\n{result['link']}")
            await ctx.send(embed=embed)

    @find.error
    async def isError(self, ctx, error):
        if isinstance(error, commands.CheckFailure):
            await ctx.send("Please use this command in <#361694671631548417> only. It takes up quite a bit of space.")


def setup(bot):
    bot.add_cog(TwiCog(bot))

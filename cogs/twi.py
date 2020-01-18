import json

import aiohttp
import discord
from discord.ext import commands
from googleapiclient.discovery import build

import secrets
from cogs.patreon_poll import fetch


def google_search(search_term, api_key, cse_id, **kwargs):
    service = build("customsearch", "v1", developerKey=api_key)
    res = service.cse().list(q=search_term, cx=cse_id, num=9, **kwargs).execute()
    return res


async def is_bot_channel(ctx):
    return ctx.channel.id == 361694671631548417


class TwiCog(commands.Cog, name="The Wandering Inn"):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(
        name="Password",
        brief="Information for patreons on how to get the chapter password",
        aliases=['pw'],
        hidden=False,
    )
    async def password(self, ctx):
        allowed_channel_ids = [620021401516113940, 346842161704075265, 521403093892726785, 362248294849576960,
                               359864559361851392]
        if ctx.message.channel.id in allowed_channel_ids:
            password = await self.bot.pg_con.fetchrow("SELECT password "
                                                      "FROM patreon_twi "
                                                      "WHERE password IS NOT NULL "
                                                      "ORDER BY serial_id DESC "
                                                      "LIMIT 1")
            await ctx.send(password['password'])
        else:
            await ctx.send("3 ways.\n"
                           "1. Link discord to patreon and go to <#346842161704075265> and check pins or use !pw inside it.\n"
                           "If you don't know how to connect discord to patreon use the command !cd\n"
                           "2. go to <https://www.patreon.com/pirateaba> and check the latest posts. It has the password.")
            embed = discord.Embed(title="password")
            embed.set_image(
                url="https://cdn.discordapp.com/attachments/362248294849576960/638350570972774440/unknown.png")
            await ctx.send(embed=embed)
            await ctx.send("3. You will get an email with the password every time pirate posts it.")

    @commands.command(
        name="ConnectDiscord",
        brief="Information for patreons on how to connect their patreon account to discord.",
        aliases=['cd'],
        hidden=False,
    )
    async def connect_discord(self, ctx):
        await ctx.send(
            "Check this link: <https://support.patreon.com/hc/en-us/articles/212052266-How-do-I-receive-my-Discord-role>")

    @commands.command(
        name="Wiki",
        brief="Searches the The Wandering Inn wiki for a matching article.",
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
        brief="Does a google search on 'Wanderinginn.com' and returns the results",
        aliases=['F', 'search'],
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

    @commands.command(
        name="Invistext",
        brief="Gives a list of all the invisible text in TWI.",
        aliases=['ht', 'hiddentext', 'hidden_text', 'invisbletext', 'invisible_text', 'it', 'invisitext']
    )
    async def invis_text(self, ctx, *, chapter=None):
        if chapter is None:
            invis_text_chapters = await self.bot.pg_con.fetch(
                "SELECT title, COUNT(*) FROM invisible_text_twi GROUP BY title, date ORDER BY date"
            )
            embed = discord.Embed(title="Chapters with invisible text")
            for posts in invis_text_chapters:
                embed.add_field(name=f"Chapter: {posts['title']}", value=f"{posts['count']}", inline=False)
            await ctx.send(embed=embed)
        else:
            texts = await self.bot.pg_con.fetch(
                "SELECT title, content FROM invisible_text_twi WHERE lower(title) similar to lower($1)",
                chapter)
            if texts:
                embed = discord.Embed(title=f"Search for: **{chapter}** invisible text")
                for text in texts:
                    embed.add_field(name=f"{text['title']}", value=text['content'], inline=False)
                await ctx.send(embed=embed)
            else:
                await ctx.send("Sorry i could not find any invisible text on that chapter.\n"
                               "Please give me the chapters exact title.")

    @commands.command(
        name="ColoredText",
        brief="List of all the different colored texts in twi",
        aliases=['ct', 'textcolor', 'tc']
    )
    async def colored_text(self, ctx):
        embed = discord.Embed(title="Twi's different colored text")
        embed.add_field(name="Red skills and classes",
                        value="#FF0000 "
                              "<:FF0000:666429504834633789><:FF0000:666429504834633789><:FF0000:666429504834633789>"
                              "\n<https://wanderinginn.com/2017/09/27/3-17-t/>")
        embed.add_field(name="Ser Raim skill",
                        value="#EB0E0E "
                              "<:EB0E0E:666429505019183144><:EB0E0E:666429505019183144><:EB0E0E:666429505019183144>"
                              "\n<https://wanderinginn.com/2019/09/10/6-43-e/>")
        embed.add_field(name="Ivolethe summoning fire",
                        value="#E01D1D "
                              "<:E01D1D:666429504863993908><:E01D1D:666429504863993908><:E01D1D:666429504863993908>"
                              "\n<https://wanderinginn.com/2017/12/30/interlude-4/>")
        embed.add_field(name="Unique Skills",
                        value="#99CC00 "
                              "<:99CC00:666429504998211594><:99CC00:666429504998211594><:99CC00:666429504998211594>"
                              "\n<https://wanderinginn.com/2017/05/03/2-19/>")
        embed.add_field(name="Erin's landmark skill",
                        value="#FF9900 "
                              "<:FF9900:666435308480364554><:FF9900:666435308480364554><:FF9900:666435308480364554>"
                              "\n<https://wanderinginn.com/2018/12/08/5-44/>")
        embed.add_field(name="Emperor's command",
                        value="#FFD700 "
                              "<:FFD700:666429505031897107><:FFD700:666429505031897107><:FFD700:666429505031897107>"
                              "\n<https://wanderinginn.com/2018/03/27/4-23-e/>")
        embed.add_field(name="Class restoration",
                        value="#99CCFF "
                              "<:99CCFF:667886770679054357><:99CCFF:667886770679054357><:99CCFF:667886770679054357>"
                              "\n<https://wanderinginn.com/2017/10/03/3-20-t/>")
        embed.add_field(name="Winter fae talking",
                        value="#8AE8FF "
                              "<:8AE8FF:666429505015119922><:8AE8FF:666429505015119922><:8AE8FF:666429505015119922>"
                              "\n<https://wanderinginn.com/2017/03/28/2-06/>")
        embed.add_field(name="Spring fae talking",
                        value="#96BE50 "
                              "<:96BE50:666429505014857728><:96BE50:666429505014857728><:96BE50:666429505014857728>"
                              "\n<https://wanderinginn.com/2018/08/14/5-11-e/>")
        embed.add_field(name="Winter fae talking",
                        value="#8AE8FF "
                              "<:8AE8FF:666429505015119922><:8AE8FF:666429505015119922><:8AE8FF:666429505015119922>"
                              "\n<https://wanderinginn.com/2017/03/28/2-06/>")
        await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.id in {579061805335183370, 579060950867640332}:
            old_pin = await self.bot.pg_con.fetchrow("SELECT * FROM webhook_pins_twi WHERE webhook_id = $1",
                                                     message.webhook_id)
            if old_pin:
                await self.bot.pg_con.execute(
                    "UPDATE webhook_pins_twi set message_id = $1, posted_date = $2 WHERE webhook_id = $3",
                    message.id, message.created_at, message.webhook_id)
                for pin in await message.channel.pins():
                    if pin.id == old_pin['message_id']:
                        await pin.unpin()
                        break
            else:
                await self.bot.pg_con.execute(
                    "INSERT INTO webhook_pins_twi(message_id, webhook_id, posted_date) VALUES ($1,$2,$3)",
                    message.id, message.webhook_id, message.created_at)
            await message.pin()


def setup(bot):
    bot.add_cog(TwiCog(bot))

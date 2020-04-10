import discord
from discord.ext import commands


class OtherCogs(commands.Cog, name="Other"):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(
        name="Ping",
        brief="Gives the latency of the bot",
        aliases=['latency', 'delay'],
        hidden=False,
    )
    async def ping(self, ctx):
        await ctx.send(f"{round(self.bot.latency * 1000)} ms")

    @commands.command(
        name="Avatar",
        brief="Posts the full version of a avatar",
        aliases=['Av'],
        usage='[@User]',
        hidden=False,
    )
    async def av(self, ctx, *, member: discord.Member = None):
        if member is None:
            member = ctx.author
        embed = discord.Embed(title="Avatar", color=discord.Color(0x3cd63d))
        embed.set_image(url=member.avatar_url)
        await ctx.send(embed=embed)

    @commands.command(
        name="Info",
        brief="Gives the account information of a user.",
        aliases=['Stats', 'Information'],
        usage='[@user]',
        hidden=False,
    )
    async def info(self, ctx, *, member: discord.Member = None):
        if member is None:
            member = ctx.author

        embed = discord.Embed(title=member.display_name, color=discord.Color(0x3cd63d))
        embed.set_thumbnail(url=member.avatar_url)
        embed.add_field(name="Account created at", value=member.created_at.strftime("%d-%m-%Y @ %H:%M:%S"))
        embed.add_field(name="Joined server", value=member.joined_at.strftime("%d-%m-%Y @ %H:%M:%S"))
        embed.add_field(name="Id", value=member.id)
        embed.add_field(name="Color", value=member.color)
        roles = ""
        for role in reversed(member.roles):
            if role.is_default():
                pass
            else:
                roles += f"{role.mention}\n"
        if roles != "":
            embed.add_field(name="Roles", value=roles, inline=False)
        await ctx.send(embed=embed)

    @commands.command(
        name="Say",
        brief="Makes Cognita repeat whatever was said",
        aliases=['repeat'],
        usage='[message]'
    )
    @commands.is_owner()
    async def say(self, ctx, *, say):
        await ctx.message.delete()
        await ctx.send(say)

    @commands.command(
        name="SayChannel",
        brief="Makes Cognita repeat whatever was said in a specific channel",
        aliases=['sayc', 'repeatc', 'sc', 'repeatchannel'],
        usage='[Channel_id][message]'
    )
    @commands.is_owner()
    async def say_channel(self, ctx, channel_id, *, say):
        channel = self.bot.get_channel(int(channel_id))
        await channel.send(say)

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        # Acid jars, Acid Flies, Frying Pans, Enchanted Soup, Barefoot Clients.
        # Green, Purple, Orange, Blue, Red
        list_of_ids = [346842555448557568, 346842589984718848, 346842629633343490, 416001891970056192,
                       416002473032024086]
        gained = set(after.roles) - set(before.roles)
        if gained:
            gained = gained.pop()
            if gained.id in list_of_ids:
                channel = self.bot.get_channel(346842161704075265)
                # Acid jar
                if gained.id == 346842555448557568:
                    embed = discord.Embed(title=f"Hey be careful over there!",
                                          description=f"Those {gained.mention} will melt your hands off {after.mention}!")
                # Acid Flies
                elif gained.id == 346842589984718848:
                    embed = discord.Embed(title=f"Make some room at the tables!",
                                          description=f"{after.mention} just ordered a bowl of {gained.mention}!")
                # Frying Pans
                elif gained.id == 346842629633343490:
                    embed = discord.Embed(title=f"Someone ordered a frying pan!",
                                          description=f"Hope {after.mention} can dodge!")
                # Enchanted Soup
                elif gained.id == 416001891970056192:
                    embed = discord.Embed(title=f"Hey get down from there Mrsha!",
                                          description=f"Looks like {after.mention} will have to order a new serving of {gained.mention} because Mrsha just ate theirs!")
                # Barefoot Clients
                elif gained.id == 416002473032024086:
                    embed = discord.Embed(title=f"Make way!",
                                          description=f"{gained.mention} {after.mention} coming through!")
                else:
                    embed = discord.Embed(title=f"Make some room in the inn!",
                                          description=f"{after.mention} just joined the ranks of {gained.mention}!")
                embed.set_thumbnail(url=after.avatar_url)
                await channel.send(embed=embed, content=f"{after.mention}")

    @commands.command(
        name="addQuote",
        aliases = ['aq']
    )
    async def addquote(self, ctx, *, quote):
        await self.bot.pg_con.execute("INSERT INTO quotes(quote, author, author_id, time, tokens) VALUES ($1,$2,$3,now(),to_tsvector($4))",
                                      quote, ctx.author.display_name, ctx.author.id, quote)
        await ctx.send(f"Added quote `{quote}`")

    @commands.command(
        name="findQuote",
        aliases = ['fq']
    )
    async def findquote(self, ctx, *, search):
        results = await self.bot.pg_con.fetch("SELECT quote, ROW_NUMBER () OVER (ORDER BY time) FROM quotes WHERE tokens @@ to_tsquery($1);", search)
        if len(results) > 1:
            index_res = "["
            iterres = iter(results)
            next(iterres)
            for result in iterres:
                index_res = f"{index_res}{str(result['row_number'])}, "
            index_res = index_res[:-2]
            index_res = f"{index_res}]"
            await ctx.send(f"{results[0]['quote']}\nThere is also results at {index_res}")
        elif len(results) == 1:
            await ctx.send(f"{results[0]['quote']}")
        elif len(results) < 1:
            await ctx.send("I found no results")
        else:
            await ctx.send("How the fuck?")


    @commands.command(
        name="deleteQuote",
        aliases=['dq']
    )
    async def deletequote(self, ctx, *, delete: int):
        u_quote = await self.bot.pg_con.fetchrow("SELECT quote, row_number FROM (SELECT quote, ROW_NUMBER () OVER () FROM quotes) x WHERE ROW_NUMBER = $1", delete)
        if u_quote:
            await self.bot.pg_con.execute("DELETE FROM quotes WHERE serial_id in (SELECT serial_id FROM QUOTES ORDER BY TIME LIMIT 1 OFFSET $1)", delete-1)
            await ctx.send(f"Deleted quote `{u_quote['quote']}` from position {u_quote['row_number']}")
        else:
            await ctx.send("Im sorry. I could not find a quote on that index")

    @commands.command(
        name="Quote",
        aliases=['q']
    )
    async def quote(self, ctx, index: int = None):
        if index is None:
            u_quote = await self.bot.pg_con.fetchrow("SELECT quote, row_number FROM (SELECT quote, ROW_NUMBER () OVER () FROM quotes) x  ORDER BY random() LIMIT 1")
        else:
            u_quote = await self.bot.pg_con.fetchrow("SELECT quote, row_number FROM (SELECT quote, ROW_NUMBER () OVER () FROM quotes) x WHERE ROW_NUMBER = $1", index)
        if u_quote:
            await ctx.send(f"Quote {u_quote['row_number']}: `{u_quote['quote']}`")
        else:
            await ctx.send("Im sorry, i could not find a quote with that index value.")
    @commands.command(
        name="whoQuote",
        aliases=['infoquote','iq','wq']
    )
    async def whoquote(self, ctx, index: int):
        u_quote = await self.bot.pg_con.fetchrow("SELECT author, author_id, time, row_number FROM (SELECT author, author_id, time, ROW_NUMBER () OVER () FROM quotes) x WHERE ROW_NUMBER = $1", index)
        await ctx.send(f"Quote {u_quote['row_number']} was added by: {u_quote['author']} ({u_quote['author_id']}) at {u_quote['time']}")
    @commands.command(
        name="backup",
    )
    @commands.is_owner()
    async def backup(self, ctx, amount: int):
        async for message in ctx.channel.history(limit=amount):
            await self.bot.pg_con.execute(
                "INSERT INTO foliana_interlude(author, author_id, content, clean_content, date, message_id)VALUES ($1,$2,$3,$4,$5,$6)",
                message.author.name, message.author.id, message.content, message.clean_content, message.created_at,
                message.id)


def setup(bot):
    bot.add_cog(OtherCogs(bot))

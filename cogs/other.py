import discord
from discord.ext import commands


class OtherCogs(commands.Cog, name="Other"):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(
        name="Ping",
        description="Gives the latency of the bot",
        aliases=['latency', 'delay'],
        hidden=False,
    )
    async def ping(self, ctx):
        await ctx.send(f"{round(self.bot.latency * 1000)} ms")

    @commands.command(
        name="Avatar",
        description="Posts the full version of a users avatar, or self if non provided.",
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
        description="Gives the account information of a user, or self if non provided.",
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
        if roles is not "":
            embed.add_field(name="Roles", value=roles, inline=False)
        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(OtherCogs(bot))

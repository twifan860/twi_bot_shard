import discord
from discord.ext import commands


def admin_or_me_check(ctx):
    role = discord.utils.get(ctx.guild.roles, id=346842813687922689)
    if ctx.message.author.id == 268608466690506753:
        return True
    elif role in ctx.message.author.roles:
        return True
    else:
        return False


class ModCogs(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(
        name="reset",
        brief="resets the cooldown of a command",
        help="resets the cooldown of a command",
        aliases=['removecooldown', 'cooldown'],
        usage='[Command]',
        hidden=False, )
    @commands.check(admin_or_me_check)
    async def reset(self, ctx, command):
        self.bot.get_command(command).reset_cooldown(ctx)

    @commands.command(
        name="state",
        brief="Makes Cognita post a mod message",
        help="",
        aliases=['modState'],
        usage="[message]"
    )
    @commands.check(admin_or_me_check)
    async def state(self, ctx, *, message):
        embed=discord.Embed(title="**MOD MESSAGE**", color=0xff0000)
        embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/359864559361851392/715698476813385788/Exclamation-Mark-Symbol-PNG.png")
        embed.add_field(name="\u200b", value=message, inline=False)
        embed.set_footer(text=f"{ctx.author.name}", icon_url=ctx.author.avatar_url)
        await ctx.send(embed=embed)

def setup(bot):
    bot.add_cog(ModCogs(bot))

import discord
from discord.ext import commands


async def add_to_gallery(ctx, msg_id, title, channel):
    msg = await ctx.fetch_message(msg_id)
    attach = msg.attachments
    embed = discord.Embed(title=title, description=f"Created by: {msg.author.mention}")
    embed.set_image(url=attach[0].url)
    await channel.send(embed=embed)


def admin_or_me_check(ctx):
    if ctx.message.author.id == 268608466690506753:
        return True
    elif ctx.message.author.roles == 346842813687922689:
        return True
    else:
        return False


class GalleryCog(commands.Cog, name="Gallery and Mementos Commands"):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(
        name="gallery",
        description="Adds a image to #gallery\nEx: !gallery 123123123 a nice image",
        aliases=['g'],
        usage='[Msg id][title]',
        hidden=False,
    )
    @commands.check(admin_or_me_check)
    async def g(self, ctx, msg_id, *, title):
        channel_id = await self.bot.pg_con.fetchrow("SELECT channel_id FROM gallery_mementos WHERE channel_name = $1",
                                                    "gallery")
        channel = self.bot.get_channel(channel_id["channel_id"])
        await add_to_gallery(ctx, msg_id, title, channel)

    @commands.command(
        name="mementos",
        description="Adds an image to #mementos",
        aliases=['m'],
        usage='[message id] [title]\nEx: !mementos 123123123 a nice meme',
        hidden=False,
    )
    @commands.check(admin_or_me_check)
    async def m(self, ctx, msg_id, *, title):
        channel_id = await self.bot.pg_con.fetchrow("SELECT channel_id FROM gallery_mementos WHERE channel_name = $1",
                                                    "mementos")
        channel = self.bot.get_channel(channel_id["channel_id"])
        await add_to_gallery(ctx, msg_id, title, channel)

    @commands.command(
        name="setgallery",
        hidden=True
    )
    @commands.check(admin_or_me_check)
    async def set_gallery(self, ctx, gallery_id: int):
        channel = await self.bot.pg_con.fetch("SELECT * FROM gallery_mementos WHERE channel_name = $1", "gallery")
        if not channel:
            await self.bot.pg_con.execute("INSERT INTO gallery_mementos (channel_id, channel_name) VALUES ($1, $2)",
                                          gallery_id,
                                          "gallery")
        await self.bot.pg_con.execute("UPDATE gallery_mementos SET channel_id=$1 WHERE channel_name=$2", gallery_id,
                                      "gallery")

    @commands.command(
        name="setmementos",
        hidden=True
    )
    @commands.check(admin_or_me_check)
    async def set_mementos(self, ctx, mementos_id: int):
        channel = await self.bot.pg_con.fetch("SELECT * FROM gallery_mementos WHERE channel_name = $1", "mementos")
        if not channel:
            await self.bot.pg_con.execute("INSERT INTO gallery_mementos (channel_id, channel_name) VALUES ($1, $2)",
                                          mementos_id,
                                          "mementos")
        await self.bot.pg_con.execute("UPDATE gallery_mementos SET channel_id=$1 WHERE channel_name=$2", mementos_id,
                                      "mementos")


def setup(bot):
    bot.add_cog(GalleryCog(bot))

import discord
from discord.ext import commands


async def add_to_gallery(ctx, msg_id, title, channel):
    msg = await ctx.fetch_message(msg_id)
    attach = msg.attachments
    embed = discord.Embed(title=title, description=f"Created by: {msg.author.mention}")
    embed.set_image(url=attach[0].url)
    await channel.send(embed=embed)


def admin_or_me_check(ctx):
    role = discord.utils.get(ctx.guild.roles, id=346842813687922689)
    if ctx.message.author.id == 268608466690506753:
        return True
    elif role in ctx.message.author.roles:
        return True
    else:
        return False


class GalleryCog(commands.Cog, name="Gallery & Mementos"):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(
        name="Gallery",
        brief="Adds a image to #gallery",
        help="'!gallery 123123123 a nice image A nice image' will add a image with the id '123123123' called 'A nice image' to #gallery\n"
             "Get the id of the image by right clicking it and selecting 'Copy id' **Note you need to use the command in the same channel as the image**",
        aliases=['g'],
        usage='[Msg Id][Title]',
        hidden=False,
    )
    @commands.check(admin_or_me_check)
    async def g(self, ctx, msg_id, *, title):
        channel_id = await self.bot.pg_con.fetchrow("SELECT channel_id FROM gallery_mementos WHERE channel_name = $1",
                                                    "gallery")
        channel = self.bot.get_channel(channel_id["channel_id"])
        await add_to_gallery(ctx, msg_id, title, channel)
        await ctx.message.delete()

    @commands.command(
        name="Mementos",
        brief="Adds an image to #mementos",
        help="'!Mementos 123123123 a nice image A nice image' will add a image with the id '123123123' called 'A nice image' to #mementos\n"
             "Get the id of the image by right clicking it and selecting 'Copy id' **Note you need to use the command in the same channel as the image**",
        aliases=['m'],
        usage='[message Id] [title]\nEx: !mementos 123123123 A nice meme',
        hidden=False,
    )
    @commands.check(admin_or_me_check)
    async def m(self, ctx, msg_id, *, title):
        channel_id = await self.bot.pg_con.fetchrow("SELECT channel_id FROM gallery_mementos WHERE channel_name = $1",
                                                    "mementos")
        channel = self.bot.get_channel(channel_id["channel_id"])
        await add_to_gallery(ctx, msg_id, title, channel)
        await ctx.message.delete()

    @commands.command(
        name="setGallery",
        brief="Set what channel !gallery posts to",
        aliases=['sg'],
        usage='[Channel id]',
        hidden=False,
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
        name="SetMementos",
        brief="Set what channel !mementos posts to",
        aliases=['sm'],
        usage='[Channel id]',
        hidden=False,
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

    @commands.command(
        name="editEmbed",
        brief="Edits the title a of embed by its message id",
        aliases=['ee'],
        usage='[message id] [New title]'
    )
    @commands.check(admin_or_me_check)
    async def editembed(self, ctx, embed_id: int, *, title):
        msg = await ctx.fetch_message(embed_id)
        test = msg.embeds
        test[0].title = title
        await msg.edit(embed=test[0])


def setup(bot):
    bot.add_cog(GalleryCog(bot))

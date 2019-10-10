import discord


async def add_to_gallery(ctx, msg_id, title, channel):
    msg = await ctx.fetch_message(msg_id)
    attach = msg.attachments
    embed = discord.Embed(title=title, description=f"Created by: {msg.author.mention}")
    embed.set_image(url=attach[0].url)
    await channel.send(embed=embed)

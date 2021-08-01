import asyncio
import logging

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
        embed = discord.Embed(title="**MOD MESSAGE**", color=0xff0000)
        embed.set_thumbnail(
            url="https://cdn.discordapp.com/attachments/359864559361851392/715698476813385788/Exclamation-Mark-Symbol-PNG.png")
        embed.add_field(name="\u200b", value=message, inline=False)
        embed.set_footer(text=ctx.author.name, icon_url=ctx.author.avatar.url)
        await ctx.send(embed=embed)

    @commands.command(
        name="deletealluser",
        alias=['dau']
    )
    @commands.check(admin_or_me_check)
    async def delete_all_user(self, ctx, user: discord.User):
        result = await self.bot.pg_con.fetchrow(
            "SELECT COUNT(*) message_count FROM messages WHERE user_id = $1 AND deleted = False AND server_id = $2",
            user.id, ctx.guild.id)
        confirm = await ctx.send(
            f"Are you sure you want do delete {result['message_count']} messages from user {user.mention}",
            allowed_mentions=None)
        await confirm.add_reaction('✅')
        await confirm.add_reaction('❌')
        logging.info(
            f"requestion confirmation to delete: {result['message_count']} messages from user id {user.id} "
            f"and user name {user.name}")

        def check(reaction, author):
            return str(reaction.emoji) in ['✅', '❌'] and author == ctx.author

        try:
            reaction, author = await self.bot.wait_for(
                'reaction_add', timeout=60,
                check=check)

        except asyncio.TimeoutError:
            await ctx.send("No reaction within 60 seconds")

        else:
            if str(reaction.emoji) == '✅':
                await ctx.send("Confirmed")
                all_messages = await self.bot.pg_con.fetch(
                    "SELECT message_id from messages where user_id = $1 AND deleted = False AND server_id = $2",
                    user.id, ctx.guild.id)
                total_del = 0
                for message in all_messages:
                    try:
                        msg = await ctx.fetch_message(message['message_id'])
                        await msg.delete()
                        total_del += 1
                    except discord.Forbidden as e:
                        logging.error(f"Forbidden {e} - {message['message_id']}")
                    except discord.NotFound as e:
                        logging.error(f"NotFound {e} - {message['message_id']}")
                    except discord.HTTPException as e:
                        logging.error(f"HTTPException {e} - {message['message_id']}")
                    await asyncio.sleep(1)
                await ctx.send(f"I succeeded in deleting {total_del} messages out of {result['message_count']}")

            if str(reaction.emoji) == '❌':
                await ctx.send("Denied")


def setup(bot):
    bot.add_cog(ModCogs(bot))

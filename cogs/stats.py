import asyncio
import logging
from datetime import datetime, timedelta

import asyncpg
import discord
from discord.ext import commands
from discord.ext import tasks
from discord.ext.commands import Cog


def admin_or_me_check(ctx):
    role = discord.utils.get(ctx.guild.roles, id=346842813687922689)
    if ctx.message.author.id == 268608466690506753:
        return True
    elif role in ctx.message.author.roles:
        return True
    else:
        return False


async def save_reaction(self, reaction):
    if type(reaction.emoji) == discord.partial_emoji.PartialEmoji or type(reaction.emoji) == discord.emoji.Emoji:
        emoji = None
        name = reaction.emoji.name
        animated = reaction.emoji.animated
        emoji_id = reaction.emoji.id
        url = reaction.emoji.url
    else:
        emoji = reaction.emoji
        name = None
        animated = False
        emoji_id = None
        url = None
    try:
        for user in await reaction.users().flatten():
            await self.bot.pg_con.execute("INSERT INTO reactions "
                                          "VALUES($1,$2,$3,$4,$5,$6,$7,$8)",
                                          emoji,
                                          reaction.message.id, user.id,
                                          name, animated, emoji_id, str(url), datetime.now())
    except Exception as e:
        logging.error(f"Failed to insert reaction into db. {e}")


async def save_message(self, message):
    roles = ""
    try:
        for role in reversed(message.author.roles):
            if role.is_default():
                pass
            else:
                roles += f"{role.name},{role.id}]\n"
    except AttributeError:
        pass

    mentions = ""
    for mention in message.mentions:
        mentions += f"{mention.name},{mention.id}\n"

    role_mentions = ""
    for role_mention in message.role_mentions:
        role_mentions += f"{role_mention.name},{role_mention.id}\n"

    if message.attachments:
        for attachment in message.attachments:
            await self.bot.pg_con.execute("INSERT INTO attachments "
                                          "VALUES($1,$2,$3,$4,$5,$6,$7,$8)",
                                          attachment.id, attachment.filename, attachment.url,
                                          attachment.size, attachment.height, attachment.width,
                                          attachment.is_spoiler(), message.id)

    if message.reactions:
        for reaction in message.reactions:
            await save_reaction(self, reaction)

    try:
        nick = message.author.nick
    except AttributeError:
        nick = ""

    try:
        await self.bot.pg_con.execute(
            "INSERT INTO messages "
            "VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16)",
            message.id, message.created_at, message.content, message.author.name, message.guild.name,
            message.guild.id, message.channel.id, message.channel.name,
            message.author.id, nick, mentions, role_mentions,
            message.jump_url, message.author.bot, roles, False)
    except asyncpg.exceptions.UniqueViolationError:
        print(f"already in database {message.id}")
        pass


class StatsCogs(commands.Cog, name="stats"):

    def __init__(self, bot):
        self.bot = bot

    # @Cog.listener("on_message")
    # async def on_message_mass_ping(self, message):
    #     if len(message.mentions) >= 2:
    #         mute_role = message.guild.get_role(712405244054863932)
    #         try:
    #             await message.author.add_roles(mute_role)
    #         except discord.Forbidden:
    #             await message.channel.send(f"I don't have the required permissions to mute {message.author.mention}")
    #         else:
    #             await message.channel.send(
    #                 f"{message.author.mention} has been muted for pinging more than 20 people in one message")

    @commands.command(
        name="save",
        hidden=True
    )
    @commands.check(admin_or_me_check)
    async def save(self, ctx):
        channels = ctx.guild.text_channels
        for channel in channels:
            if channel.permissions_for(channel.guild.me).read_message_history:
                last_message = await self.bot.pg_con.fetchrow(
                    'SELECT created_at FROM messages WHERE "channel_ID" = $1 ORDER BY created_at DESC LIMIT 1',
                    channel.id)
                if last_message is not None:
                    first = last_message['created_at']
                else:
                    first = datetime.strptime('2015-01-01', '%Y-%m-%d')
                async for message in channel.history(limit=None, after=first, oldest_first=True):
                    await save_message(self, message)
                    await asyncio.sleep(0.05)
                print(f"{channel.name} Done")
            else:
                print(f"I was not allowed access to {channel.name}")
        print("Done!")
        if self.save_listener not in self.bot.extra_events['on_message']:
            self.bot.add_listener(self.save_listener, name='on_message')
        if self.message_deleted not in self.bot.extra_events['on_raw_message_delete']:
            self.bot.add_listener(self.message_deleted, name='on_raw_message_delete')
        if self.message_edited not in self.bot.extra_events['on_raw_message_edit']:
            self.bot.add_listener(self.message_edited, name='on_raw_message_edit')
        if self.reaction_add not in self.bot.extra_events['on_raw_reaction_add']:
            self.bot.add_listener(self.reaction_add, name='on_raw_reaction_add')
        if self.reaction_remove not in self.bot.extra_events['on_raw_reaction_remove']:
            self.bot.add_listener(self.reaction_remove, name='on_raw_reaction_remove')

    @Cog.listener("on_message")
    async def save_listener(self, message):
        await save_message(self, message)

    @Cog.listener("on_raw_message_delete")
    async def message_deleted(self, message):
        await self.bot.pg_con.execute("UPDATE public.messages SET deleted = true WHERE message_id = $1",
                                      message.message_id)

    @Cog.listener("on_raw_message_edit")
    async def message_edited(self, message):
        if message.data['edited_timestamp'] is None:
            return
        mentions = ""
        for mention in message.data['mentions']:
            mentions += f"{mention['username']},{mention['id']}\n"
        await self.bot.pg_con.execute("INSERT INTO message_edit "
                                      "SELECT $1, $2, content, user_mentions, role_mentions "
                                      "FROM messages "
                                      "WHERE message_id = $1",
                                      message.message_id,
                                      datetime.fromisoformat(message.data['edited_timestamp']).replace(tzinfo=None))
        await self.bot.pg_con.execute("UPDATE messages SET content = $1, user_mentions = $2, role_mentions = $3 "
                                      "WHERE message_id = $4",
                                      message.data['content'], mentions,
                                      "\n".join(message.data['mention_roles']), message.message_id)

    @Cog.listener("on_raw_reaction_add")
    async def reaction_add(self, reaction):
        if type(reaction.emoji) == discord.partial_emoji.PartialEmoji or type(reaction.emoji) == discord.emoji.Emoji:
            old_react = await self.bot.pg_con.fetchrow("SELECT * "
                                                       "FROM reactions "
                                                       "WHERE (message_id = $1 AND user_id = $2 AND emoji_id = $3)",
                                                       reaction.message_id, reaction.user_id, reaction.emoji.id)
        else:
            old_react = await self.bot.pg_con.fetchrow("SELECT * "
                                                       "FROM reactions "
                                                       "WHERE (message_id = $1 AND user_id = $2 AND unicode_emoji = $3)",
                                                       reaction.message_id, reaction.user_id, reaction.emoji)
        if type(reaction.emoji) == discord.partial_emoji.PartialEmoji or type(reaction.emoji) == discord.emoji.Emoji:
            if old_react is not None:
                await self.bot.pg_con.execute("UPDATE reactions "
                                              "SET removed = FALSE "
                                              "WHERE message_id = $1 AND user_id = $2 AND emoji_id = $3",
                                              reaction.message_id, reaction.user_id, reaction.emoji.id)
                return
        else:
            if old_react is not None:
                await self.bot.pg_con.execute("UPDATE reactions "
                                              "SET removed = FALSE "
                                              "WHERE message_id = $1 AND user_id = $2 AND unicode_emoji = $3",
                                              reaction.message_id, reaction.user_id, reaction.emoji)
                return
        if type(reaction.emoji) == discord.partial_emoji.PartialEmoji or type(reaction.emoji) == discord.emoji.Emoji:
            emoji = None
            name = reaction.emoji.name
            animated = reaction.emoji.animated
            emoji_id = reaction.emoji.id
        else:
            emoji = reaction.emoji
            name = None
            animated = False
            emoji_id = None
        await self.bot.pg_con.execute("INSERT INTO reactions "
                                      "VALUES($1,$2,$3,$4,$5,$6,$7,$8)",
                                      emoji, reaction.message_id, reaction.user_id,
                                      name, animated, emoji_id,
                                      f"https://cdn.discordapp.com/emojis/{emoji_id}.{'gif' if animated else 'png'}",
                                      datetime.now())

    @Cog.listener("on_raw_reaction_remove")
    async def reaction_remove(self, reaction):
        if type(reaction.emoji) == discord.partial_emoji.PartialEmoji or type(reaction.emoji) == discord.emoji.Emoji:
            await self.bot.pg_con.execute("UPDATE reactions "
                                          "SET removed = TRUE "
                                          "WHERE message_id = $1 AND user_id = $2 AND emoji_id = $3",
                                          reaction.message_id, reaction.user_id, reaction.emoji.id)
        else:
            await self.bot.pg_con.execute("UPDATE reactions "
                                          "SET removed = TRUE "
                                          "WHERE message_id = $1 AND user_id = $2 AND unicode_emoji = $3",
                                          reaction.message_id, reaction.user_id, reaction.emoji)

    @Cog.listener("on_guild_channel_pins_update")
    async def channel_pins_update(self, channel, last_pin):
        absolute_pins = await self.bot.pg_con.fetch("SELECT * "
                                                    "FROM absolute_pinned_position "
                                                    "WHERE channel_id = $1 "
                                                    "ORDER BY position", channel.id)
        if absolute_pins is not None:
            pins = await channel.pins()
            for x in reversed(range(len(absolute_pins))):
                if pins[x].id != absolute_pins[x]['message_id']:
                    for pin in pins:
                        if pin.id == absolute_pins[x]['message_id']:
                            await pin.unpin()
                            await asyncio.sleep(0.5)
                            await pin.pin()
                            break

    @commands.command(
        name="pinned_absolute",
        alias=['pa']
    )
    async def pinned_absolute(self, ctx, message_id: int, position: int):
        pre = await self.bot.pg_con.fetchrow("SELECT * FROM absolute_pinned_position WHERE message_id = $1",
                                             message_id)
        if pre is None:
            await self.bot.pg_con.execute("INSERT INTO absolute_pinned_position VALUES($1,$2,$3)",
                                          message_id, ctx.channel.id, position)
        else:
            await self.bot.pg_con.execute("UPDATE absolute_pinned_position SET position = $1 WHERE message_id = $2",
                                          position, message_id)

    @Cog.listener("on_member_join")
    async def member_join(self, member):
        await self.bot.pg_con.execute("INSERT INTO join_leave VALUES($1,$2,$3,$4,$5,$6,$7)",
                                      member.name, member.id, datetime.now(), "JOIN",
                                      member.guild.name, member.guild.id, member.created_at)

    @Cog.listener("on_member_remove")
    async def member_remove(self, member):
        await self.bot.pg_con.execute("INSERT INTO join_leave VALUES($1,$2,$3,$4,$5,$6,$7)",
                                      member.name, member.id, datetime.now(), "LEAVE",
                                      member.guild.name, member.guild.id, member.created_at)


def setup(bot):
    bot.add_cog(StatsCogs(bot))

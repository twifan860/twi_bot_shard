import asyncio
import logging
import typing
from datetime import datetime, timedelta

import asyncpg
import dateparser
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
            connection = await self.bot.pg_con.acquire()
            async with connection.transaction():
                await self.bot.pg_con.execute("INSERT INTO reactions "
                                              "VALUES($1,$2,$3,$4,$5,$6,$7,$8)",
                                              emoji,
                                              reaction.message.id, user.id,
                                              name, animated, emoji_id, str(url), datetime.now())
            await self.bot.pg_con.release(connection)
    except Exception as e:
        logging.error(f"Failed to insert reaction into db. {e}")


async def save_message(self, message):
    for mention in message.mentions:
        connection = await self.bot.pg_con.acquire()
        async with connection.transaction():
            await self.bot.pg_con.execute("INSERT INTO mentions(message_id, user_mention) VALUES ($1,$2)",
                                          message.id, mention.id)
        await self.bot.pg_con.release(connection)

    for role_mention in message.role_mentions:
        connection = await self.bot.pg_con.acquire()
        async with connection.transaction():
            await self.bot.pg_con.execute("INSERT INTO mentions(message_id, role_mention) VALUES ($1,$2)",
                                          message.id, role_mention.id)
        await self.bot.pg_con.release(connection)

    if message.attachments:
        for attachment in message.attachments:
            connection = await self.bot.pg_con.acquire()
            async with connection.transaction():
                await self.bot.pg_con.execute("INSERT INTO attachments "
                                              "VALUES($1,$2,$3,$4,$5,$6,$7,$8)",
                                              attachment.id, attachment.filename, attachment.url,
                                              attachment.size, attachment.height, attachment.width,
                                              attachment.is_spoiler(), message.id)
            await self.bot.pg_con.release(connection)

    if message.reactions:
        for reaction in message.reactions:
            await save_reaction(self, reaction)

    try:
        nick = message.author.nick
    except AttributeError:
        nick = ""

    try:
        reference = message.reference.message_id
    except AttributeError:
        reference = None

    try:
        connection = await self.bot.pg_con.acquire()
        async with connection.transaction():
            await self.bot.pg_con.execute(
                "INSERT INTO messages(message_id, created_at, content, user_name, server_name, server_id, channel_id, "
                "channel_name, user_id, user_nick, jump_url, is_bot, deleted, reference) "
                "VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14)",
                message.id, message.created_at, message.content, message.author.name, message.guild.name,
                message.guild.id, message.channel.id, message.channel.name,
                message.author.id, nick,
                message.jump_url, message.author.bot, False, reference)
        await self.bot.pg_con.release(connection)
    except asyncpg.exceptions.UniqueViolationError:
        logging.warning(f"{message.id} already in DB")
    except asyncpg.exceptions.ForeignKeyViolationError as e:
        logging.error(f"{e}")
        connection = await self.bot.pg_con.acquire()
        async with connection.transaction():
            await self.bot.pg_con.execute(
                "INSERT INTO users(user_id, created_at, bot, username) VALUES($1,$2,$3,$4)",
                message.author.id, message.author.created_at, message.author.bot, message.author.name
            )
        await self.bot.pg_con.release(connection)
        connection = await self.bot.pg_con.acquire()
        async with connection.transaction():
            await self.bot.pg_con.execute(
                "INSERT INTO messages(message_id, created_at, content, user_name, server_name, server_id, channel_id, "
                "channel_name, user_id, user_nick, jump_url, is_bot, deleted, reference) "
                "VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14)",
                message.id, message.created_at, message.content, message.author.name, message.guild.name,
                message.guild.id, message.channel.id, message.channel.name,
                message.author.id, nick,
                message.jump_url, message.author.bot, False, reference)
        await self.bot.pg_con.release(connection)


class StatsCogs(commands.Cog, name="stats"):

    def __init__(self, bot):
        self.bot = bot
        self.stats_loop.start()

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
        name="save_users",
        hidden=True
    )
    @commands.check(admin_or_me_check)
    async def save_users(self, ctx):
        await ctx.message.delete()
        try:
            for guild in self.bot.guilds:
                logging.info(f"Fetching members list")
                members_list = guild.members
                connection = await self.bot.pg_con.acquire()
                async with connection.transaction():
                    user_ids = await self.bot.pg_con.fetch("SELECT user_id FROM users")
                await self.bot.pg_con.release(connection)
                flat_user_ids = [item for sublist in user_ids for item in sublist]
                logging.debug(f"{flat_user_ids=}")
                logging.debug(f"{user_ids=}")
                for member in members_list:
                    logging.debug(f"{member=}")
                    if member.id not in flat_user_ids:
                        connection = await self.bot.pg_con.acquire()
                        async with connection.transaction():
                            await self.bot.pg_con.execute("INSERT INTO "
                                                          "users(user_id, created_at, bot, username) "
                                                          "VALUES($1,$2,$3,$4)",
                                                          member.id, member.created_at, member.bot, member.name)
                        await self.bot.pg_con.release(connection)
                        connection = await self.bot.pg_con.acquire()
                        async with connection.transaction():
                            await self.bot.pg_con.execute(
                                "INSERT INTO server_membership(user_id, server_id) VALUES ($1,$2)",
                                member.id, member.guild.id)
                        await self.bot.pg_con.release(connection)
                    else:
                        connection = await self.bot.pg_con.acquire()
                        async with connection.transaction():
                            await self.bot.pg_con.execute(
                                "INSERT INTO server_membership(user_id, server_id) VALUES ($1,$2) "
                                "ON CONFLICT DO NOTHING",
                                member.id, member.guild.id)
                        await self.bot.pg_con.release(connection)
        except Exception as e:
            logging.error(f'{type(e).__name__} - {e}')

    @commands.command(
        name="save_servers",
        hidden=True
    )
    @commands.is_owner()
    async def save_servers(self, ctx):
        for guild in self.bot.guilds:
            connection = await self.bot.pg_con.acquire()
            async with connection.transaction():
                await self.bot.pg_con.execute(
                    "INSERT INTO servers(server_id, server_name, creation_date) VALUES ($1,$2,$3)"
                    " ON CONFLICT DO NOTHING ",
                    guild.id, guild.name, guild.created_at)
            await self.bot.pg_con.release(connection)
        await ctx.send("Done")

    @commands.command(
        name="save_channels",
        hidden=True
    )
    @commands.is_owner()
    async def save_channels(self, ctx):
        for guild in self.bot.guilds:
            for channel in guild.text_channels:
                try:
                    connection = await self.bot.pg_con.acquire()
                    async with connection.transaction():
                        await self.bot.pg_con.execute("INSERT INTO "
                                                      "channels(id, name, category_id, created_at, guild_id, position, topic, is_nsfw) "
                                                      "VALUES ($1,$2,$3,$4,$5,$6,$7,$8)",
                                                      channel.id, channel.name, channel.category_id, channel.created_at,
                                                      channel.guild.id, channel.position, channel.topic,
                                                      channel.is_nsfw())
                    await self.bot.pg_con.release(connection)
                except Exception as e:
                    logging.error(f'{type(e).__name__} - {e}')
                except asyncpg.UniqueViolationError:
                    logging.debug("Already in DB")
        await ctx.send("Done")

    @commands.command(
        name="save_categories",
        hidden=True
    )
    @commands.is_owner()
    async def save_categories(self, ctx):
        for guild in self.bot.guilds:
            for category in guild.categories:
                try:
                    connection = await self.bot.pg_con.acquire()
                    async with connection.transaction():
                        await self.bot.pg_con.execute("INSERT INTO "
                                                      "categories(id, name, created_at, guild_id, position, is_nsfw) "
                                                      "VALUES ($1,$2,$3,$4,$5,$6)",
                                                      category.id, category.name, category.created_at,
                                                      category.guild.id, category.position, category.is_nsfw())
                    await self.bot.pg_con.release(connection)
                except Exception as e:
                    logging.error(f'{type(e).__name__} - {e}')
                except asyncpg.UniqueViolationError:
                    logging.debug("Already in DB")
        await ctx.send("Done")

    @commands.command(
        name="save_roles",
        hidden=True
    )
    @commands.is_owner()
    async def save_roles(self, ctx):
        for guild in self.bot.guilds:
            logging.debug(f"{guild=}")
            for role in guild.roles:
                logging.debug(f"{role=}")
                if role.is_default():
                    continue
                try:
                    connection = await self.bot.pg_con.acquire()
                    async with connection.transaction():
                        await self.bot.pg_con.execute("INSERT INTO "
                                                      "roles(id, name, color, created_at, hoisted, managed, position, guild_id) "
                                                      "VALUES ($1,$2,$3,$4,$5,$6,$7,$8)",
                                                      role.id, role.name, str(role.color), role.created_at, role.hoist,
                                                      role.managed, role.position, guild.id)
                    await self.bot.pg_con.release(connection)
                except asyncpg.UniqueViolationError:
                    logging.debug(f"Role already in DB")
                for member in role.members:
                    try:
                        connection = await self.bot.pg_con.acquire()
                        async with connection.transaction():
                            await self.bot.pg_con.execute("INSERT INTO role_membership(user_id, role_id) VALUES($1,$2)",
                                                          member.id, role.id)
                        await self.bot.pg_con.release(connection)
                    except asyncpg.UniqueViolationError:
                        logging.debug(f"connection already in DB {member} - {role}")
        await ctx.send("Done")

    @commands.command(
        name="save_users_from_join_leave",
        hidden=True
    )
    @commands.is_owner()
    async def save_users_from_join_leave(self, ctx):
        connection = await self.bot.pg_con.acquire()
        async with connection.transaction():
            jn_users = await self.bot.pg_con.fetch("SELECT user_id,created_at FROM join_leave")
        await self.bot.pg_con.release(connection)
        for user in jn_users:
            logging.debug(user)
            try:
                connection = await self.bot.pg_con.acquire()
                async with connection.transaction():
                    await self.bot.pg_con.execute("INSERT INTO "
                                                  "users(user_id, created_at, bot, username) "
                                                  "VALUES($1,$2,$3,$4)",
                                                  user['user_id'], user['created_at'], False, user['user_name'])
                await self.bot.pg_con.release(connection)

            except asyncpg.UniqueViolationError:
                logging.debug("Users already in DB")
        await ctx.send("Done")

    @commands.command(
        name="save_channels_from_messages",
        hidden=True
    )
    @commands.is_owner()
    async def save_users_from_messages(self, ctx):
        connection = await self.bot.pg_con.acquire()
        async with connection.transaction():
            m_channels = await self.bot.pg_con.fetch("""SELECT reactions.message_id FROM reactions
                                                    LEFT JOIN messages m on reactions.message_id = m.message_id
                                                    WHERE m.message_id IS NULL
                                                    GROUP BY reactions.message_id""")
        await self.bot.pg_con.release(connection)
        for channel in m_channels:
            try:
                message = await self.bot.fetch_message(channel['message_id'])
                logging.info(f"{message}")
                connection = await self.bot.pg_con.acquire()
                async with connection.transaction():
                    await self.bot.pg_con.execute("INSERT INTO users(user_id, username, bot) VALUES($1,$2,$3)",
                                                  channel['user_id'], channel['user_name'], channel['is_bot'])
                await self.bot.pg_con.release(connection)
                logging.info(f"inserting {channel}")
            except Exception as e:
                logging.info(f"{e}")
        await ctx.send("Done")

    @commands.command(
        name="save",
        hidden=True
    )
    @commands.check(admin_or_me_check)
    async def save(self, ctx):
        await ctx.message.delete()
        logging.info(f"starting save")
        for guild in self.bot.guilds:
            logging.debug(f"{guild=}")
            channels = guild.text_channels
            for channel in channels:
                logging.debug(f"{channel=}")
                logging.info(f"Starting with {channel.name}")
                if channel.permissions_for(channel.guild.me).read_message_history:
                    connection = await self.bot.pg_con.acquire()
                    async with connection.transaction():
                        last_message = await self.bot.pg_con.fetchrow(
                            'SELECT created_at FROM messages WHERE channel_id = $1 ORDER BY message_id DESC LIMIT 1',
                            channel.id)
                    await self.bot.pg_con.release(connection)
                    logging.debug(f"Fetching done. found {last_message}")
                    if last_message is None:
                        logging.debug("No last row found")
                        first = datetime.strptime('2015-01-01', '%Y-%m-%d')
                    else:
                        logging.debug("Last row found")
                        first = last_message['created_at']
                    logging.info(f"Last message at {first}")
                    count = 0
                    async for message in channel.history(limit=None, after=first, oldest_first=True):
                        logging.debug(f"Saving {message.id} to database")
                        count += 1
                        await save_message(self, message)
                        await asyncio.sleep(0.05)
                    logging.info(f"{channel.name} Done. saved {count} messages")
                else:
                    logging.info(f"I was not allowed access to {channel.name}")
        logging.info("!save completed")
        if self.save_listener not in self.bot.extra_events['on_message']:
            self.bot.add_listener(self.save_listener, name='on_message')
        if self.message_deleted not in self.bot.extra_events['on_raw_message_delete']:
            self.bot.add_listener(self.message_deleted, name='on_raw_message_delete')
        if self.reaction_add not in self.bot.extra_events['on_raw_reaction_add']:
            self.bot.add_listener(self.reaction_add, name='on_raw_reaction_add')
        if self.reaction_remove not in self.bot.extra_events['on_raw_reaction_remove']:
            self.bot.add_listener(self.reaction_remove, name='on_raw_reaction_remove')

    @Cog.listener("on_message")
    async def save_listener(self, message):
        await save_message(self, message)

    @Cog.listener("on_raw_message_delete")
    async def message_deleted(self, message):
        connection = await self.bot.pg_con.acquire()
        async with connection.transaction():
            await self.bot.pg_con.execute("UPDATE public.messages SET deleted = true WHERE message_id = $1",
                                          message.message_id)
        await self.bot.pg_con.release(connection)

    @Cog.listener("on_raw_reaction_add")
    async def reaction_add(self, reaction):
        if type(reaction.emoji) == discord.partial_emoji.PartialEmoji or type(
                reaction.emoji) == discord.emoji.Emoji:
            connection = await self.bot.pg_con.acquire()
            async with connection.transaction():
                old_react = await self.bot.pg_con.fetchrow("SELECT * "
                                                           "FROM reactions "
                                                           "WHERE (message_id = $1 AND user_id = $2 AND emoji_id = $3)",
                                                           reaction.message_id, reaction.user_id, reaction.emoji.id)
            await self.bot.pg_con.release(connection)
        else:
            connection = await self.bot.pg_con.acquire()
            async with connection.transaction():
                old_react = await self.bot.pg_con.fetchrow("SELECT * "
                                                           "FROM reactions "
                                                           "WHERE (message_id = $1 AND user_id = $2 AND unicode_emoji = $3)",
                                                           reaction.message_id, reaction.user_id, reaction.emoji)
            await self.bot.pg_con.release(connection)
        if type(reaction.emoji) == discord.partial_emoji.PartialEmoji or type(
                reaction.emoji) == discord.emoji.Emoji:
            if old_react is not None:
                connection = await self.bot.pg_con.acquire()
                async with connection.transaction():
                    await self.bot.pg_con.execute("UPDATE reactions "
                                                  "SET removed = FALSE "
                                                  "WHERE message_id = $1 AND user_id = $2 AND emoji_id = $3",
                                                  reaction.message_id, reaction.user_id, reaction.emoji.id)
                await self.bot.pg_con.release(connection)
                return
        else:
            if old_react is not None:
                connection = await self.bot.pg_con.acquire()
                async with connection.transaction():
                    await self.bot.pg_con.execute("UPDATE reactions "
                                                  "SET removed = FALSE "
                                                  "WHERE message_id = $1 AND user_id = $2 AND unicode_emoji = $3",
                                                  reaction.message_id, reaction.user_id, reaction.emoji)
                await self.bot.pg_con.release(connection)
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
        connection = await self.bot.pg_con.acquire()
        async with connection.transaction():
            await self.bot.pg_con.execute("INSERT INTO reactions "
                                          "VALUES($1,$2,$3,$4,$5,$6,$7,$8)",
                                          emoji, reaction.message_id, reaction.user_id,
                                          name, animated, emoji_id,
                                          f"https://cdn.discordapp.com/emojis/{emoji_id}.{'gif' if animated else 'png'}",
                                          datetime.now())
        await self.bot.pg_con.release(connection)

    @Cog.listener("on_raw_reaction_remove")
    async def reaction_remove(self, reaction):
        if type(reaction.emoji) == discord.partial_emoji.PartialEmoji or type(
                reaction.emoji) == discord.emoji.Emoji:
            connection = await self.bot.pg_con.acquire()
            async with connection.transaction():
                await self.bot.pg_con.execute("UPDATE reactions "
                                              "SET removed = TRUE "
                                              "WHERE message_id = $1 AND user_id = $2 AND emoji_id = $3",
                                              reaction.message_id, reaction.user_id, reaction.emoji.id)
            await self.bot.pg_con.release(connection)
        else:
            connection = await self.bot.pg_con.acquire()
            async with connection.transaction():
                await self.bot.pg_con.execute("UPDATE reactions "
                                              "SET removed = TRUE "
                                              "WHERE message_id = $1 AND user_id = $2 AND unicode_emoji = $3",
                                              reaction.message_id, reaction.user_id, reaction.emoji)
            await self.bot.pg_con.release(connection)

    @Cog.listener("on_member_join")
    async def member_join(self, member):
        connection = await self.bot.pg_con.acquire()
        async with connection.transaction():
            await self.bot.pg_con.execute("INSERT INTO join_leave VALUES($1,$2,$3,$4,$5,$6)",
                                          member.id, datetime.now(), "JOIN",
                                          member.guild.name, member.guild.id, member.created_at)
        await self.bot.pg_con.release(connection)
        try:
            connection = await self.bot.pg_con.acquire()
            async with connection.transaction():
                await self.bot.pg_con.execute("INSERT INTO "
                                              "users(user_id, created_at, bot, username) "
                                              "VALUES($1,$2,$3,$4) ON CONFLICT (user_id) DO UPDATE SET username = $4",
                                              member.id, member.created_at, member.bot, member.name)
                await self.bot.pg_con.execute(
                    "INSERT INTO server_membership(user_id, server_id) VALUES ($1,$2)",
                    member.id, member.guild.id)
            await self.bot.pg_con.release(connection)
        except asyncpg.UniqueViolationError:
            logging.error("Failed to insert user into server_membership")
        except Exception as e:
            channel = self.bot.get_channel(297916314239107072)
            await channel.send(f"{e}")

    @Cog.listener("on_member_remove")
    async def member_remove(self, member):
        connection = await self.bot.pg_con.acquire()
        async with connection.transaction():
            await self.bot.pg_con.execute("DELETE FROM server_membership WHERE user_id = $1 AND server_id = $2",
                                          member.id, member.guild.id)
        await self.bot.pg_con.release(connection)
        connection = await self.bot.pg_con.acquire()
        async with connection.transaction():
            await self.bot.pg_con.execute("INSERT INTO join_leave VALUES($1,$2,$3,$4,$5,$6)",
                                          member.id, datetime.now(), "LEAVE",
                                          member.guild.name, member.guild.id, member.created_at)
        await self.bot.pg_con.release(connection)

    @Cog.listener("on_member_update")
    async def member_roles_update(self, before, after):
        if before.roles != after.roles:
            if len(before.roles) < len(after.roles):
                gained = set(after.roles) - set(before.roles)
                gained = gained.pop()
                connection = await self.bot.pg_con.acquire()
                async with connection.transaction():
                    await self.bot.pg_con.execute("INSERT INTO role_membership(user_id, role_id) VALUES($1,$2)",
                                                  after.id, gained.id)
                await self.bot.pg_con.release(connection)
                connection = await self.bot.pg_con.acquire()
                async with connection.transaction():
                    await self.bot.pg_con.execute(
                        "INSERT INTO role_history(role_id, user_id, date) VALUES($1,$2,$3)",
                        gained.id, after.id, datetime.now())
                await self.bot.pg_con.release(connection)
            else:
                lost = set(before.roles) - set(after.roles)
                lost = lost.pop()
                connection = await self.bot.pg_con.acquire()
                async with connection.transaction():
                    await self.bot.pg_con.execute(
                        "DELETE FROM role_membership WHERE user_id = $1 AND role_id = $2",
                        after.id, lost.id)
                await self.bot.pg_con.release(connection)
                connection = await self.bot.pg_con.acquire()
                async with connection.transaction():
                    await self.bot.pg_con.execute(
                        "INSERT INTO role_history(role_id, user_id, date, gained) VALUES($1,$2,$3,FALSE)",
                        lost.id, after.id, datetime.now())
                await self.bot.pg_con.release(connection)

    @Cog.listener("on_user_update")
    async def user_update(self, before, after):
        if before.name != after.name:
            try:
                connection = await self.bot.pg_con.acquire()
                async with connection.transaction():
                    await self.bot.pg_con.execute("UPDATE users SET username = $1 WHERE user_id = $2",
                                                  after.name, after.id)
                await self.bot.pg_con.release(connection)
                connection = await self.bot.pg_con.acquire()
                async with connection.transaction():
                    await self.bot.pg_con.execute(
                        'INSERT INTO updates(updated_table, action, before, after, date, primary_key) VALUES($1,$2,$3,$4,$5,$6)',
                        "users", "UPDATE_USERNAME", before.name, after.name, datetime.now(), str(after.id))
                await self.bot.pg_con.release(connection)
            except Exception as e:
                logging.error(f"Error {e}")

    @Cog.listener("on_guild_channel_create")
    async def guild_channel_create(self, channel):
        logging.info(f"{channel.type}")
        logging.info(f"{channel.type == discord.ChannelType.text}")
        if channel.type == discord.ChannelType.text:
            try:
                connection = await self.bot.pg_con.acquire()
                async with connection.transaction():
                    await self.bot.pg_con.execute("INSERT INTO "
                                                  "channels(id, name, category_id, created_at, guild_id, position, topic, is_nsfw) "
                                                  "VALUES ($1,$2,$3,$4,$5,$6,$7,$8)",
                                                  channel.id, channel.name, channel.category_id,
                                                  channel.created_at,
                                                  channel.guild.id, channel.position, channel.topic,
                                                  channel.is_nsfw())
                await self.bot.pg_con.release(connection)
            except Exception as e:
                logging.error(f"{e}")
        elif channel.type == discord.ChannelType.category:
            try:
                connection = await self.bot.pg_con.acquire()
                async with connection.transaction():
                    await self.bot.pg_con.execute(
                        "INSERT INTO categories(id, name, created_at, guild_id, position, is_nsfw) VALUES($1,$2,$3,$4,$5,$6)",
                        channel.id, channel.name, channel.created_at, channel.guild_id, channel.position,
                        channel.is_nsfw())
                await self.bot.pg_con.release(connection)
            except Exception as e:
                logging.error(f"{e}")

    @Cog.listener("on_guild_channel_delete")
    async def guild_channel_delete(self, channel):
        connection = await self.bot.pg_con.acquire()
        async with connection.transaction():
            await self.bot.pg_con.execute("UPDATE channels set deleted = TRUE where id = $1",
                                          channel.id)
        await self.bot.pg_con.release(connection)
        connection = await self.bot.pg_con.acquire()
        async with connection.transaction():
            await self.bot.pg_con.execute("UPDATE messages SET deleted = TRUE where channel_id = $1",
                                          channel.id)
        await self.bot.pg_con.release(connection)
        connection = await self.bot.pg_con.acquire()
        async with connection.transaction():
            await self.bot.pg_con.execute(
                'INSERT INTO updates(updated_table, action, before, after, date, primary_key) VALUES($1,$2,$3,$4,$5,$6)',
                "channel", "DELETED_CHANNEL", channel.name, channel.name, datetime.now(), str(channel.id))
        await self.bot.pg_con.release(connection)

    @Cog.listener("on_guild_channel_update")
    async def guild_channel_update(self, before, after):
        if before.name != after.name:
            connection = await self.bot.pg_con.acquire()
            async with connection.transaction():
                await self.bot.pg_con.execute("UPDATE channels set name = $1 where id = $2",
                                              after.name, after.id)
            await self.bot.pg_con.release(connection)
            connection = await self.bot.pg_con.acquire()
            async with connection.transaction():
                await self.bot.pg_con.execute(
                    'INSERT INTO updates(updated_table, action, before, after, date, primary_key) VALUES($1,$2,$3,$4,$5,$6)',
                    "channels", "UPDATE_CHANNEL_NAME", before.name, after.name, datetime.now(), str(after.id))
            await self.bot.pg_con.release(connection)
        if before.category_id != after.category_id:
            connection = await self.bot.pg_con.acquire()
            async with connection.transaction():
                await self.bot.pg_con.execute("UPDATE channels set category_id = $1 where id = $2",
                                              after.category_id, after.id)
            await self.bot.pg_con.release(connection)
            connection = await self.bot.pg_con.acquire()
            async with connection.transaction():
                await self.bot.pg_con.execute(
                    'INSERT INTO updates(updated_table, action, before, after, date, primary_key) VALUES($1,$2,$3,$4,$5,$6)',
                    "channels", "UPDATE_CHANNEL_CATEGORY_ID", before.category_id, after.category_id,
                    datetime.now(),
                    str(after.id))
            await self.bot.pg_con.release(connection)
        if before.position != after.position:
            connection = await self.bot.pg_con.acquire()
            async with connection.transaction():
                await self.bot.pg_con.execute("UPDATE channels set position = $1 where id = $2",
                                              after.position, after.id)
            await self.bot.pg_con.release(connection)
            connection = await self.bot.pg_con.acquire()
            async with connection.transaction():
                await self.bot.pg_con.execute(
                    'INSERT INTO updates(updated_table, action, before, after, date, primary_key) VALUES($1,$2,$3,$4,$5,$6)',
                    "channels", "UPDATE_CHANNEL_POSITION", before.position, after.position, datetime.now(),
                    str(after.id))
            await self.bot.pg_con.release(connection)
        if before.topic != after.topic:
            connection = await self.bot.pg_con.acquire()
            async with connection.transaction():
                await self.bot.pg_con.execute("UPDATE channels set topic = $1 where id = $2",
                                              after.topic, after.id)
            await self.bot.pg_con.release(connection)
            connection = await self.bot.pg_con.acquire()
            async with connection.transaction():
                await self.bot.pg_con.execute(
                    'INSERT INTO updates(updated_table, action, before, after, date, primary_key) VALUES($1,$2,$3,$4,$5,$6)',
                    "channels", "UPDATE_CHANNEL_TOPIC", before.topic, after.topic, datetime.now(),
                    str(after.id))
            await self.bot.pg_con.release(connection)
        if before.is_nsfw() != after.is_nsfw():
            connection = await self.bot.pg_con.acquire()
            async with connection.transaction():
                await self.bot.pg_con.execute("UPDATE channels set is_nsfw = $1 where id = $2",
                                              after.is_nsfw(), after.id)
            await self.bot.pg_con.release(connection)
            connection = await self.bot.pg_con.acquire()
            async with connection.transaction():
                await self.bot.pg_con.execute(
                    'INSERT INTO updates(updated_table, action, before, after, date, primary_key) VALUES($1,$2,$3,$4,$5,$6)',
                    "channels", "UPDATE_CHANNEL_IS_NSFW", before.is_nsfw(), after.is_nsfw(), datetime.now(),
                    str(after.id))
            await self.bot.pg_con.release(connection)

    @Cog.listener("on_guild_update")
    async def guild_update(self, before, after):
        if before.name != after.name:
            connection = await self.bot.pg_con.acquire()
            async with connection.transaction():
                await self.bot.pg_con.execute("UPDATE servers set server_name = $1 WHERE server_id = $2",
                                              after.name, after.id)
            await self.bot.pg_con.release(connection)
            connection = await self.bot.pg_con.acquire()
            async with connection.transaction():
                await self.bot.pg_con.execute(
                    'INSERT INTO updates(updated_table, action, before, after, date, primary_key) VALUES($1,$2,$3,$4,$5,$6)',
                    "servers", "UPDATE_SERVER_NAME", before.name, after.name, datetime.now(), str(after.id))
            await self.bot.pg_con.release(connection)

    @Cog.listener("on_guild_role_create")
    async def guild_role_create(self, role):
        connection = await self.bot.pg_con.acquire()
        async with connection.transaction():
            await self.bot.pg_con.execute("INSERT INTO "
                                          "roles(id, name, color, created_at, hoisted, managed, position, guild_id) "
                                          "VALUES ($1,$2,$3,$4,$5,$6,$7,$8)",
                                          role.id, role.name, str(role.color), role.created_at, role.hoist,
                                          role.managed, role.position, role.guild.id)
        await self.bot.pg_con.release(connection)

    @Cog.listener("on_guild_role_delete")
    async def guild_role_delete(self, role):
        connection = await self.bot.pg_con.acquire()
        async with connection.transaction():
            await self.bot.pg_con.execute("UPDATE roles set deleted = TRUE where id = $1",
                                          role.id)
        await self.bot.pg_con.release(connection)
        connection = await self.bot.pg_con.acquire()
        async with connection.transaction():
            await self.bot.pg_con.execute("DELETE FROM role_membership WHERE role_id = $1", role.id)
        await self.bot.pg_con.release(connection)

    @Cog.listener("on_guild_role_update")
    async def guild_role_update(self, before, after):
        if before.name != after.name:
            connection = await self.bot.pg_con.acquire()
            async with connection.transaction():
                await self.bot.pg_con.execute("UPDATE roles set name = $1 where id = $2",
                                              after.name, after.id)
            await self.bot.pg_con.release(connection)
            connection = await self.bot.pg_con.acquire()
            async with connection.transaction():
                await self.bot.pg_con.execute(
                    'INSERT INTO updates(updated_table, action, before, after, date, primary_key) VALUES($1,$2,$3,$4,$5,$6)',
                    "roles", "UPDATE_ROLE_NAME", before.name, after.name, datetime.now(), str(after.id))
            await self.bot.pg_con.release(connection)
        if before.color != after.color:
            connection = await self.bot.pg_con.acquire()
            async with connection.transaction():
                await self.bot.pg_con.execute("UPDATE roles set color = $1 where id = $2",
                                              after.color, after.id)
            await self.bot.pg_con.release(connection)
            connection = await self.bot.pg_con.acquire()
            async with connection.transaction():
                await self.bot.pg_con.execute(
                    'INSERT INTO updates(updated_table, action, before, after, date, primary_key) VALUES($1,$2,$3,$4,$5,$6)',
                    "roles", "UPDATE_ROLE_COLOR", before.color, after.color, datetime.now(), str(after.id))
            await self.bot.pg_con.release(connection)
        if before.hoisted != after.hoisted:
            connection = await self.bot.pg_con.acquire()
            async with connection.transaction():
                await self.bot.pg_con.execute("UPDATE roles set hoisted = $1 where id = $2",
                                              after.hoisted, after.id)
            await self.bot.pg_con.release(connection)
            connection = await self.bot.pg_con.acquire()
            async with connection.transaction():
                await self.bot.pg_con.execute(
                    'INSERT INTO updates(updated_table, action, before, after, date, primary_key) VALUES($1,$2,$3,$4,$5,$6)',
                    "roles", "UPDATE_ROLE_HOISTED", before.hoisted, after.hoisted, datetime.now(),
                    str(after.id))
            await self.bot.pg_con.release(connection)
        if before.position != after.position:
            connection = await self.bot.pg_con.acquire()
            async with connection.transaction():
                await self.bot.pg_con.execute("UPDATE roles set position = $1 where id = $2",
                                              after.position, after.id)
            await self.bot.pg_con.release(connection)
            connection = await self.bot.pg_con.acquire()
            async with connection.transaction():
                await self.bot.pg_con.execute(
                    'INSERT INTO updates(updated_table, action, before, after, date, primary_key) VALUES($1,$2,$3,$4,$5,$6)',
                    "roles", "UPDATE_ROLE_POSITION", before.position, after.position, datetime.now(),
                    str(after.id))
            await self.bot.pg_con.release(connection)

    @tasks.loop(hours=24)
    async def stats_loop(self):
        logging.info("Starting daily server activity stats gathering")
        message = ""
        connection = await self.bot.pg_con.acquire()
        async with connection.transaction():
            messages_result = await self.bot.pg_con.fetch(
                """         
                SELECT COUNT(*) total, string_agg(distinct channel_name::text, ','::text) AS Channel
                FROM messages 
                WHERE created_at >= NOW() - INTERVAL '1 DAY' 
                AND server_id = 346842016480755724 
                AND is_bot = FALSE
                GROUP BY channel_id
                ORDER BY total DESC
                """)
        await self.bot.pg_con.release(connection)
        if not messages_result:
            length = 6
            logging.error(
                f"No messages found in guild 346842016480755724 during the last {datetime.now() - timedelta(hours=24)} - {datetime.now()}")
        else:
            logging.debug(f"Found results {messages_result}")
            length = len(str(messages_result[0]['total'])) + 1
            message += "==== Stats last 24 hours ====\n"
            message += "==== Messages stats ====\n"
            logging.debug(f"Build message {message}")
            for result in messages_result:
                try:
                    message += f"{result['total']:<{length}}:: {result['channel']}\n"
                except Exception as e:
                    logging.error(f'{type(e).__name__} - {e}')
            logging.debug("requesting leave/join stats")
        connection = await self.bot.pg_con.acquire()
        async with connection.transaction():
            user_join_leave_results = await self.bot.pg_con.fetchrow(
                """         
                SELECT
                COUNT(*) filter (where join_or_leave = 'JOIN') as "JOIN",
                COUNT(*) filter (where join_or_leave = 'LEAVE') as "LEAVE"
                FROM join_leave WHERE date >= NOW() - INTERVAL '1 DAY'
                AND server_id = 346842016480755724 
                """)
        await self.bot.pg_con.release(connection)
        logging.debug(f"Found stats {user_join_leave_results}")
        message += f"==== Memeber stats ====\n" \
                   f"{user_join_leave_results['JOIN']:<{length}}:: Joined\n" \
                   f"{user_join_leave_results['LEAVE']:<{length}}:: Left"
        logging.debug(f"Built message {message}")
        channel = self.bot.get_channel(297916314239107072)
        logging.debug(f"Found channel {channel.name}")
        if len(message) > 1900:
            logging.debug("Message longer than 1900 characters")
            str_list = [message[i:i + 1900] for i in range(0, len(message), 1900)]
            for string in str_list:
                await channel.send(f"```asciidoc\n{string}\n```")
                await asyncio.sleep(0.5)
        else:
            try:
                await channel.send(f"```asciidoc\n{message}\n```")
            except Exception as e:
                logging.error(f"Could not post stats_loop to channel {channel.name} - {e}")
        logging.info("Daily stats report done")

    @commands.command(
        name="messagecount",
        brief="Retrive message count from a channel in the last x hours",
        help="",
        aliases=['mc', 'count'],
        usage='[channel] [hours]',
        hidden=False,
    )
    async def message_count(self, ctx, channel: discord.TextChannel, *, time: typing.Union[int, str]):
        logging.debug(time)
        d_time = dateparser.parse(f'{time} ago')
        logging.debug(d_time)
        connection = await self.bot.pg_con.acquire()
        async with connection.transaction():
            results = await self.bot.pg_con.fetchrow(
                "SELECT count(*) total FROM messages WHERE created_at > $1 and channel_id = $2",
                d_time, channel.id)
        await self.bot.pg_con.release(connection)
        await ctx.send(f"There is a total of {results['total']} in channel {channel} since {d_time} UTC")
        logging.info(f"total messages: {results['total']} in channel {channel.name}")


def setup(bot):
    bot.add_cog(StatsCogs(bot))

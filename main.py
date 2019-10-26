import json
from datetime import datetime, timezone
from itertools import cycle

import aiohttp
import asyncpg
import discord
from discord.ext import commands, tasks
from googleapiclient.discovery import build

import gallery
import patreon_poll
import secrets

bot = commands.Bot(
    command_prefix='!',
    description="The wandering inn bot",
    case_insensitive=True, )
bot.remove_command("help")


@bot.event
async def on_ready():
    status_loop.start()
    print(f'Logged in as {bot.user.name}')
    print('------')


async def create_db_pool():
    bot.pg_con = await asyncpg.create_pool(database="testDB", user="pi", password=secrets.DB_pass)


status = cycle(["Killing the mages of Wistram",
                "Cleaning up a mess",
                "Keeping secrets",
                "Hiding corpses",
                "Mending Pirateaba's broken hands",
                "Longing for Zelkyr",
                "Banishing Chimera to #debates",
                "Hoarding knowledge",
                "Dusting off priceless artifacts",
                "Praying for Mating Rituals 2"])


@tasks.loop(seconds=10)
async def status_loop():
    await bot.change_presence(activity=discord.Game(next(status)))


@bot.event
async def on_command_error(ctx, error):
    if hasattr(ctx.command, "on_error"):
        return
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("Please pass an argument")
    elif isinstance(error, commands.NotOwner):
        await ctx.send(f"Sorry {ctx.author.display_name} only ~~Zelkyr~~ Sara may do that.")
    elif isinstance(error, commands.MissingRole):
        await ctx.send("I'm sorry, you don't seem to have the required role for that")


def admin_or_me_check(ctx):
    if ctx.message.author.id == 268608466690506753:
        return True
    elif ctx.message.author.roles == 346842813687922689:
        return True
    else:
        return False


@bot.command(aliases=["gallery"])
@commands.check(admin_or_me_check)
async def g(ctx, msg_id, *, title):
    channel_id = await bot.pg_con.fetchrow("SELECT channel_id FROM gallery_mementos WHERE channel_name = $1", "gallery")
    channel = bot.get_channel(channel_id["channel_id"])
    await gallery.add_to_gallery(ctx, msg_id, title, channel)


@bot.command(aliases=["mementos"])
@commands.check(admin_or_me_check)
async def m(ctx, msg_id, *, title):
    channel_id = await bot.pg_con.fetchrow("SELECT channel_id FROM gallery_mementos WHERE channel_name = $1",
                                           "mementos")
    channel = bot.get_channel(channel_id["channel_id"])
    await gallery.add_to_gallery(ctx, msg_id, title, channel)


@bot.command()
@commands.check(admin_or_me_check)
async def setgallery(ctx, gallery_id: int):
    channel = await bot.pg_con.fetch("SELECT * FROM gallery_mementos WHERE channel_name = $1", "gallery")
    if not channel:
        await bot.pg_con.execute("INSERT INTO gallery_mementos (channel_id, channel_name) VALUES ($1, $2)", gallery_id,
                                 "gallery")
    await bot.pg_con.execute("UPDATE gallery_mementos SET channel_id=$1 WHERE channel_name=$2", gallery_id, "gallery")


@bot.command()
@commands.check(admin_or_me_check)
async def setmementos(ctx, mementos_id: int):
    channel = await bot.pg_con.fetch("SELECT * FROM gallery_mementos WHERE channel_name = $1", "mementos")
    if not channel:
        await bot.pg_con.execute("INSERT INTO gallery_mementos (channel_id, channel_name) VALUES ($1, $2)", mementos_id,
                                 "mementos")
    await bot.pg_con.execute("UPDATE gallery_mementos SET channel_id=$1 WHERE channel_name=$2", mementos_id, "mementos")


@bot.command(aliases=["p"])
@commands.cooldown(1, 120, commands.BucketType.channel)
async def poll(ctx, x=None):
    active_polls = await bot.pg_con.fetch("SELECT * FROM poll WHERE expire_date > now()")
    if active_polls and x is None:
        await patreon_poll.p_poll(active_polls, ctx, bot)
    else:
        last_poll = await bot.pg_con.fetch("SELECT COUNT (*) FROM poll")
        if x is None:
            x = last_poll[0][0]
        value = await bot.pg_con.fetch("SELECT * FROM poll ORDER BY id OFFSET $1 LIMIT 1", int(x) - 1)
        await patreon_poll.p_poll(value, ctx, bot)


@bot.command(aliases=["pl"])
@commands.cooldown(1, 120, commands.BucketType.channel)
async def polllist(ctx, year=datetime.now(timezone.utc).year):
    polls_year = await bot.pg_con.fetch(
        "select title, poll_number from (SELECT poll.title, poll.start_date, row_number() OVER (ORDER BY poll.start_date ASC) as poll_number from poll) as numbered_polls where date_part('year', start_date) = $1",
        year)
    if not polls_year:
        await ctx.send("Sorry there were no polls that year that i could find :(")
    else:
        embed = discord.Embed(title="List of polls", color=discord.Color(0x3cd63d),
                              description=f"**{year}**")
        for polls in polls_year:
            embed.add_field(name=f"{polls['title']}", value=polls['poll_number'], inline=False)
        await ctx.send(embed=embed)


@bot.command()
@commands.is_owner()
async def getpoll(ctx):
    await patreon_poll.get_poll(bot)


@bot.command(aliases=["w"])
async def wiki(ctx, *, query):
    url = f"https://thewanderinginn.fandom.com/api/v1/Search/List?query={query}&limit=1&minArticleQuality=0"
    async with aiohttp.ClientSession() as session:
        html = await patreon_poll.fetch(session, url)
        json_data = json.loads(html)
    try:
        await ctx.send(
            f"Results from search **{query}**\n{json_data['items'][0]['title']} - {json_data['items'][0]['url']}")
    except IndexError:
        url = f"https://thewanderinginn.fandom.com/api/v1/SearchSuggestions/List?query={query}"
        async with aiohttp.ClientSession() as session:
            html = await patreon_poll.fetch(session, url)
            json_data = json.loads(html)
        try:
            await ctx.send(
                f"Sorry, i could not find a article matching that search. You could try: {json_data['items'][0]['title']}")
        except IndexError:
            await ctx.send(f"Sorry, i could not find a article matching that search.")


@bot.command()
async def link(ctx, user_input):
    query_r = await bot.pg_con.fetch("SELECT content, title FROM tags WHERE lower(title) = lower($1)", user_input)
    if query_r:
        await ctx.send(f"{query_r[0]['title']}: {query_r[0]['content']}")
    else:
        await ctx.send(f"I could not find a link with the title **{user_input}**")


@bot.command()
async def links(ctx):
    query_r = await bot.pg_con.fetch("SELECT title FROM tags ORDER BY title")
    message = ""
    for tags in query_r:
        message = f"{message} `{tags['tag']}`"
    await ctx.send(f"Tags: {message}")


@bot.command()
async def addlink(ctx, content, title, input_tag=None):
    try:
        await bot.pg_con.execute(
            "INSERT INTO tags(content, tag, user_who_added, id_user_who_added, time_added, title) "
            "VALUES ($1,$2,$3,$4,now(),$5)",
            content, input_tag, ctx.author.display_name, ctx.author.id, title)
        await ctx.send(f"Added Link: {title}\nLink: <{content}>\nTag: {input_tag}")
    except asyncpg.exceptions.UniqueViolationError:
        await ctx.send("That name is already in the list.")


@bot.command()
async def delink(ctx, title):
    result = await bot.pg_con.execute("DELETE FROM tags WHERE lower(title) = lower($1)", title)
    if result == "DELETE 1":
        await ctx.send(f"Deleted link: **{title}**")
    else:
        await ctx.send(f"I could not find a link with the title: **{title}**")


@bot.command()
async def tags(ctx):
    query_r = await bot.pg_con.fetch("SELECT tag FROM tags ORDER BY tag")
    message = ""
    for tags in query_r:
        message = f"{message} `{tags['tag']}`"
    await ctx.send(f"Tags: {message}")


@bot.command()
async def tag(ctx, user_input):
    query_r = await bot.pg_con.fetch("SELECT title FROM tags WHERE lower(tag) = lower($1) ORDER BY title", user_input)
    message = ""
    for tags in query_r:
        message = f"{message}\n`{tags['title']}`"
    await ctx.send(f"links: {message}")


def google_search(search_term, api_key, cse_id, **kwargs):
    service = build("customsearch", "v1", developerKey=api_key)
    res = service.cse().list(q=search_term, cx=cse_id, num=5, **kwargs).execute()
    return res


async def is_bot_channel(ctx):
    return ctx.channel.id == 361694671631548417


@bot.command(aliases=["f"])
@commands.check(is_bot_channel)
async def find(ctx, *, query):
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
async def isError(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send("Please use this command in <#361694671631548417> only. It takes up quite a bit of space.")


@bot.command()
async def ping(ctx):
    await ctx.send(f"{round(bot.latency * 1000)} ms")


@bot.command(aliases=["avatar"])
async def av(ctx):
    embed = discord.Embed(title="Avatar", color=discord.Color(0x3cd63d))
    embed.set_image(url=ctx.author.avatar_url)
    await ctx.send(embed=embed)


@bot.command()
async def info(ctx):
    embed = discord.Embed(title=ctx.author.display_name, color=discord.Color(0x3cd63d))
    embed.set_thumbnail(url=ctx.author.avatar_url)
    embed.add_field(name="Account created at", value=ctx.author.created_at.strftime("%d-%m-%Y @ %H:%M:%S"))
    embed.add_field(name="Joined server", value=ctx.author.joined_at.strftime("%d-%m-%Y @ %H:%M:%S"))
    embed.add_field(name="id", value=ctx.author.id)
    embed.add_field(name="Color", value=ctx.author.color)
    roles = ""
    for role in reversed(ctx.message.author.roles):
        if role.is_default():
            pass
        else:
            roles += f"{role.mention}\n"
    if roles is not "":
        embed.add_field(name="Roles", value=roles, inline=False)
    await ctx.send(embed=embed)


@bot.command()
async def help(ctx):
    embed = discord.Embed(title="Help", color=discord.Color(0x3cd63d), description="List of commands")
    embed.add_field(name="!av", value="Posts the full version of your current avatar", inline=False)
    embed.add_field(name="!ping", value="Gives you the latency of the bot", inline=False)
    embed.add_field(name="!info", value="Gives your account information", inline=False)
    embed.add_field(name="!gallery [!g]", value="Use: !gallery [message id] [title]"
                                                "\nEx: !gallery 123123123 a nice image"
                                                "\nPosts the image in the message to a specified channel"
                                                "\nNote: The image needs to be an embed")
    embed.add_field(name="!mementos [!m]", value="Use: !mementos [message id] [title]"
                                                 "\nEx: !mementos 123123123 a good meme"
                                                 "\nPosts the image in the message to a specified channel"
                                                 "\nNote: The image needs to be an embed")
    embed.add_field(name="!setgallery", value="Use: !setgallery [channel id]\n"
                                              "sets which channel !gallery should post in", inline=False)
    embed.add_field(name="!setmementos",
                    value="Use: !setmementos [channel id]\n" "sets which channel !mementos should post in",
                    inline=False)
    embed.add_field(name="!poll [!p]",
                    value="Use: !poll, !poll [id]\nShows the current active polls if no id is given. If there is no active poll, the latest poll is shown.",
                    inline=False)
    embed.add_field(name="!polllist [!pl]",
                    value="Use: !polllist, !polllist [year]\nShows the list of ids of all polls sorted by year.",
                    inline=False)
    embed.add_field(name="!wiki [!w]",
                    value="Use: !wiki Toren, !w Niers\nSearches the TWI wiki for a matching article.", inline=False)
    embed.add_field(name="!link", value="Use: !link [title]\nPosts the link with the given name.", inline=False)
    embed.add_field(name="!links", value="Use: !links\nView all links.", inline=False)
    embed.add_field(name="!addlink",
                    value="Use: !link [url][title][tag]\nAdds a link with the given name to the given url and tag",
                    inline=False)
    embed.add_field(name="!delink", value="Use: !delink [title]\nDeletes a link with the given name", inline=False)
    embed.add_field(name="!tags", value="Use: !tags\nSee all available tags", inline=False)
    embed.add_field(name="!tag", value="Use: !tag [tag]\nView all links that got a certain tag", inline=False)
    embed.add_field(name="!find [f]", value="Use: !find [query]\n"
                                            "Does a google search on wanderinginn.com and returns the results",
                    inline=False)
    await ctx.author.send(embed=embed)


# TODO: Allow to switch page (show more results) on !find
# TODO: Add score tracker on !trivia?
# TODO: Rewrite !help - Look at dragons help message.
# TODO:

bot.loop.run_until_complete(create_db_pool())
bot.run(secrets.bot_token)

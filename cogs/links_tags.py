import asyncpg
from discord.ext import commands


class LinkTags(commands.Cog, name="Links commands"):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(
        name="link",
        description="Posts the link with the given name.",
        usage='[title]',
        hidden=False,
    )
    async def link(self, ctx, user_input):
        query_r = await self.bot.pg_con.fetch("SELECT content, title FROM tags WHERE lower(title) = lower($1)",
                                              user_input)
        if query_r:
            await ctx.send(f"{query_r[0]['title']}: {query_r[0]['content']}")
        else:
            await ctx.send(f"I could not find a link with the title **{user_input}**")

    @commands.command(
        name="links",
        description="View all links.",
        hidden=False,
    )
    async def links(self, ctx):
        query_r = await self.bot.pg_con.fetch("SELECT title FROM tags ORDER BY title")
        message = ""
        for tags in query_r:
            message = f"{message} `{tags['tag']}`"
        await ctx.send(f"Tags: {message}")

    @commands.command(
        name="addlink",
        description="Adds a link with the given name to the given url and tag",
        usage='[url][title][tag]',
        hidden=False,
    )
    async def add_link(self, ctx, content, title, input_tag=None):
        try:
            await self.bot.pg_con.execute(
                "INSERT INTO tags(content, tag, user_who_added, id_user_who_added, time_added, title) "
                "VALUES ($1,$2,$3,$4,now(),$5)",
                content, input_tag, ctx.author.display_name, ctx.author.id, title)
            await ctx.send(f"Added Link: {title}\nLink: <{content}>\nTag: {input_tag}")
        except asyncpg.exceptions.UniqueViolationError:
            await ctx.send("That name is already in the list.")

    @commands.command(
        name="delink",
        description="Deletes a link with the given name",
        aliases=['removelink', 'deletelink'],
        usage='[title]',
        hidden=False,
    )
    async def delete_link(self, ctx, title):
        result = await self.bot.pg_con.execute("DELETE FROM tags WHERE lower(title) = lower($1)", title)
        if result == "DELETE 1":
            await ctx.send(f"Deleted link: **{title}**")
        else:
            await ctx.send(f"I could not find a link with the title: **{title}**")

    @commands.command(
        name="tags",
        description="See all available tags",
        aliases=['listtags', 'showtags'],
        hidden=False,
    )
    async def tags(self, ctx):
        query_r = await self.bot.pg_con.fetch("SELECT tag FROM tags ORDER BY tag")
        message = ""
        for tags in query_r:
            message = f"{message} `{tags['tag']}`"
        await ctx.send(f"Tags: {message}")

    @commands.command(
        name="tag",
        description="View all links that got a certain tag",
        aliases=['showtag'],
        usage='[tag]',
        hidden=False,
    )
    async def tag(self, ctx, user_input):
        query_r = await self.bot.pg_con.fetch("SELECT title FROM tags WHERE lower(tag) = lower($1) ORDER BY title",
                                              user_input)
        message = ""
        for tags in query_r:
            message = f"{message}\n`{tags['title']}`"
        await ctx.send(f"links: {message}")


def setup(bot):
    bot.add_cog(LinkTags(bot))

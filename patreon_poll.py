import json
from datetime import datetime, timezone
from operator import itemgetter

import aiohttp
import discord

import secrets


async def fetch(session, url):
    async with session.get(url, cookies=secrets.cookies) as respons:
        return await respons.text()


async def get_poll(bot):
    url = "https://www.patreon.com/api/posts?include=Cpoll.choices%2Cpoll.current_user_responses.poll&sort=-published_at&filter[campaign_id]=568211"
    while True:
        async with aiohttp.ClientSession() as session:
            html = await fetch(session, url)
            json_data = json.loads(html)
        for posts in json_data['data']:
            if posts['relationships']['poll']['data'] is not None:
                poll_id = await bot.pg_con.fetch("SELECT * FROM poll WHERE id = $1",
                                                 int(posts['relationships']['poll']['data']['id']))
                if not poll_id:
                    async with aiohttp.ClientSession() as session:
                        html = await fetch(session, posts['relationships']['poll']['links']['related'])
                        json_data2 = json.loads(html)
                    print("https://www.patreon.com" + posts['attributes']['patreon_url'])
                    print(posts['relationships']['poll']['links']['related'])
                    open_at_converted = datetime.fromisoformat(json_data2['data']['attributes']['created_at'])
                    try:
                        closes_at_converted = datetime.fromisoformat(json_data2['data']['attributes']['closes_at'])
                    except TypeError:
                        closes_at_converted = None
                    title = json_data2['data']['attributes']['question_text']
                    if closes_at_converted is None or closes_at_converted < datetime.now(timezone.utc):
                        await bot.pg_con.execute(
                            "INSERT INTO poll(api_url, poll_url, id, start_date, expire_date, title, total_votes, expired, num_options)"
                            "VALUES ($1,$2,$3,$4,$5,$6,$7, TRUE, $8)",
                            posts['relationships']['poll']['links']['related'],
                            "https://www.patreon.com" + posts['attributes']['patreon_url'],
                            int(posts['relationships']['poll']['data']['id']),
                            open_at_converted,
                            closes_at_converted,
                            title,
                            int(json_data2["data"]["attributes"]["num_responses"]),
                            len(json_data2['data']['relationships']['choices']['data']))
                        for i in range(0, len(json_data2['data']['relationships']['choices']['data'])):
                            print(json_data2['included'][i]['attributes'])
                            await bot.pg_con.execute(
                                "INSERT INTO poll_option(option_text, poll_id, num_votes, option_id)"
                                "VALUES ($1,$2,$3,$4)",
                                json_data2['included'][i]['attributes']['text_content'],
                                int(posts['relationships']['poll']['data']['id']),
                                int(json_data2['included'][i]['attributes']['num_responses']),
                                int(json_data2['data']['relationships']['choices']['data'][i]['id']))
                    else:
                        await bot.pg_con.execute(
                            "INSERT INTO poll(api_url, poll_url, id, start_date, expire_date, title, expired, num_options)"
                            "VALUES ($1,$2,$3,$4,$5,$6, FALSE, $7)",
                            posts['relationships']['poll']['links']['related'],
                            "https://www.patreon.com" + posts['attributes']['patreon_url'],
                            int(posts['relationships']['poll']['data']['id']),
                            open_at_converted,
                            closes_at_converted,
                            title,
                            len(json_data2['data']['relationships']['choices']['data']))
        try:
            url = json_data['links']['next']
        except KeyError:
            break


async def p_poll(polls, ctx, bot):
    for poll in polls:
        if not poll['expired']:
            async with aiohttp.ClientSession() as session:
                html = await fetch(session, poll["api_url"])
                json_data = json.loads(html)
            options = []
            for i in range(0, len(json_data['data']['relationships']['choices']['data'])):
                data = (json_data['included'][i]['attributes']['text_content'],
                        json_data['included'][i]['attributes']['num_responses'])
                options.append(data)
            options = sorted(options, key=itemgetter(1), reverse=True)
        else:
            options = await bot.pg_con.fetch(
                "SELECT option_text, num_votes FROM poll_option WHERE poll_id = $1 ORDER BY num_votes DESC",
                poll['id'])
        time_left = poll["expire_date"] - datetime.now(timezone.utc)
        hours = int(((time_left.total_seconds() // 3600) % 24))
        embed = discord.Embed(title="Poll", color=discord.Color(0x3cd63d),
                              description=f"**[{poll['title']}]({poll['poll_url']})**")
        embed.set_footer(
            text=f"Poll started at {poll['start_date'].strftime('%Y-%m-%d %H:%M:%S %Z')} "
                 f"and {'closed' if poll['expired'] else 'closes'} at {poll['expire_date'].strftime('%Y-%m-%d %H:%M:%S %Z')} "
                 f"({time_left.days} days and {hours} hours {'ago' if poll['expired'] else 'left'})")
        for option in options:
            embed.add_field(name=option[0], value=option[1], inline=False)
        await ctx.send(embed=embed)

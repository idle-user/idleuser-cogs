import asyncio
import logging
from datetime import datetime

import discord
from redbot.core import commands

from .api import IdleUserAPI, WEB_URL
from .entities import User, Superstar, Match
from .errors import ResourceNotFound, ValidationError
from .utils import quickembed

log = logging.getLogger("red.idleuser-cogs.WatchWrestling")


class Matches(IdleUserAPI, commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def grab_user(self, ctx, registration_required_message=False) -> User:
        try:
            data = await self.get_user_by_discord_id(ctx.author.id)
            user = User(data)
            user.discord = ctx.author
        except ResourceNotFound:
            user = User.unregistered_user()
            user.discord = ctx.author
            if registration_required_message:
                embed = quickembed.error(
                    desc="You must be registered to use this command. Use `!register` to register.",
                    user=user)
                await ctx.send(embed=embed)
        return user

    @commands.command(name="stats", aliases=["me", "bal", "points"])
    async def user_stats(self, ctx, season=7):
        user = await self.grab_user(ctx, True)
        if user.is_registered:
            user_stats_data = await self.get_user_stats_by_season_id(user.id, season)
            await ctx.send(embed=user.stats_embed(user_stats_data))

    @commands.command(name="rumble", aliases=["royalrumble"])
    async def royalrumble_info(self, ctx):
        user = await self.grab_user(ctx, True)
        if user.is_registered:
            await self.dm_user_login_link(user, redirect_to="/projects/matches/royalrumble")
            embed = quickembed.success(desc="Royal Rumble link DMed", user=user)
            await ctx.send(embed=embed)

    @commands.command(name="ppv", aliases=["events"])
    async def upcoming_events(self, ctx):
        user = await self.grab_user(ctx)
        try:
            event_list = await self.get_future_events()
        except ResourceNotFound:
            embed = quickembed.error(desc="No future events found", user=user)
            await ctx.send(embed=embed)
            return
        current_date = datetime.now().date()
        embed_field_strings = []
        for event in event_list:
            event_dt_object = datetime.strptime(event["date_time"], "%Y-%m-%d %H:%M:%S")
            event_time_format = "R" if event_dt_object.date() == current_date else "f"
            epoch_time = int(event_dt_object.timestamp())
            embed_field_strings.append("<t:{}:{}> - **{}**".format(epoch_time, event_time_format, event["name"]))
        embed = quickembed.info(desc="Upcoming Events (PT)", user=user)
        embed.add_field(
            name="\u200b",
            value="\n".join(embed_field_strings)
        )
        await ctx.send(embed=embed)

    @commands.command(name="superstar", aliases=["bio"])
    async def superstar_search(self, ctx, *, keyword):
        user = await self.grab_user(ctx)
        try:
            data = await self.get_superstar_search(keyword)
        except ResourceNotFound:
            embed = quickembed.error(desc="Unable to find superstar matching `{}`".format(keyword), user=user)
            await ctx.send(embed=embed)
            return

        superstar_list = [Superstar(d) for d in data]
        if len(superstar_list) > 1:
            msg = "Select Superstar from List ...\n```"
            for i, e in enumerate(superstar_list):
                msg = msg + "{}. {}\n".format(i + 1, e.name)
            msg = msg + "```"
            await ctx.send(embed=quickembed.question(desc=msg, user=user))
            try:
                response = await self.bot.wait_for(
                    "message",
                    check=lambda m: m.author == ctx.author
                                    and m.content.isdigit()
                                    and 1 <= int(m.content) <= len(superstar_list),
                    timeout=15.0,
                )
                index = int(response.content)
                embed = superstar_list[index - 1].info_embed()
            except asyncio.TimeoutError:
                embed = quickembed.error("Took too long to confirm. Try again.", user=user)
        else:
            embed = superstar_list[0].info_embed()
        await ctx.send(embed=embed)

    @commands.command(name="leaderboard", aliases=["top"])
    async def leaderboard(self, ctx, season=7):
        try:
            stat_list = await self.get_leaderboard_by_season_id(season)
        except ResourceNotFound:
            embed = quickembed.error("Unable to retrieve leaderboard for season `{}`".format(season))
            await ctx.send(embed=embed)
            return

        embed = discord.Embed(description="Season {}".format(season), color=0x0080FF)
        embed.set_author(
            name="Leaderboard",
            url=WEB_URL + "projects/matches/leaderboard?season_id={}".format(season),
            icon_url=self.bot.user.display_avatar,
        )
        lb = [
            "{}. {} ({:,})".format(i + 1, v["username"], int(v["total_points"]))
            for i, v in enumerate(stat_list[:10])
        ]
        embed.add_field(
            name="\u200b", value="\n".join(lb) if lb else "Nothing found", inline=True
        )
        await ctx.send(embed=embed)

    @commands.command(name="match", aliases=["match-info"])
    async def match_info(self, ctx, match_id=None):
        try:
            match_data = await self.get_match_by_id(match_id)
            match = Match(match_data)
            embed = match.info_embed()
        except ResourceNotFound:
            embed = quickembed.error("Unable to retrieve match `{}`".format(match_id))
        await ctx.send(embed=embed)

    @commands.command(name="matches", aliases=["open-matches"])
    async def open_matches(self, ctx):
        try:
            openbet_match_data = await self.get_openbet_matches()
        except ResourceNotFound:
            embed = quickembed.error("Unable to retrieve any open matches")
            await ctx.send(embed=embed)
            return

        openbet_matches = []
        for match_data in openbet_match_data:
            temp_match = Match(match_data)
            if temp_match.match_type_id == 0:
                continue
            openbet_matches.append(temp_match)
        if len(openbet_matches) == 1:
            embed = openbet_matches[0].info_embed()
        else:
            embed = quickembed.info(desc="Short View - Use `!match [id]` for full view")
            embed.set_author(name="Open Bet Matches")
            for match in openbet_matches:
                if match.match_type_id == 0:
                    continue
                embed.add_field(
                    name="[Match {}]".format(match.id),
                    value="{}".format(match.info_text_short()),
                    inline=True,
                )
        await ctx.send(embed=embed)

    @commands.command(name="current-match", aliases=["currentmatch"])
    async def current_match_info(self, ctx):
        try:
            match_data = await self.get_current_match()
            match = Match(match_data)
            embed = match.info_embed()
        except ResourceNotFound as e:
            embed = quickembed.error(desc=str(e))
        await ctx.send(embed=embed)

    @commands.command(name="recent-match", aliases=["lastmatch", "last-match"])
    async def recent_match_info(self, ctx):
        try:
            match_data = await self.get_recent_match()
            match = Match(match_data)
            embed = match.info_embed()
        except ResourceNotFound as e:
            embed = quickembed.error(desc=str(e))
        await ctx.send(embed=embed)

    @commands.command(name="rate", aliases=["rate-match"])
    async def rate_match(self, ctx, rating: float):
        user = await self.grab_user(ctx, True)
        if not user.is_registered:
            return
        try:
            match_data = await self.get_recent_match()
        except ResourceNotFound as e:
            embed = quickembed.error(desc=str(e))
            await ctx.send(embed=embed)
            return
        match = Match(match_data)
        await self.post_match_rating(user.id, match.id, rating)
        stars = ""
        for i in range(1, 6):
            if rating >= i:
                stars += "★"
            else:
                stars += "☆"
        msg = "Rated `Match {}` {} ({})\n{}".format(
            match.id, stars, rating, match.info_text_short()
        )
        embed = quickembed.success(desc=msg, user=user)
        await ctx.send(embed=embed)

    @commands.command(name="bet", aliases=["bet-match"])
    async def bet_match(self, ctx, bet: str, *, superstar_name: str):
        user = await self.grab_user(ctx, True)
        if not user.is_registered:
            return
        bet = int(bet.replace(",", ""))
        match = None
        increase_bet_attempt = False
        # find open matches matching superstar name
        try:
            openbet_match_data = await self.get_openbet_matches()
            for match_data in openbet_match_data:
                temp_match = Match(match_data)
                if temp_match.match_type_id == 0:
                    continue
                if superstar_name.lower() in temp_match.contestants.lower():
                    match = temp_match
                    break
        except ResourceNotFound:
            embed = quickembed.error(desc="No open bet matches available", user=user)
            await ctx.send(embed=embed)
        # if match not found, prepare error message
        if not match:
            error_msg = "Unable to find an open match for contestant `{}`".format(
                superstar_name
            )
            embed = quickembed.error(desc=error_msg, user=user)
            await ctx.send(embed=embed)
        # if match found, gather info and confirm bet
        else:
            # check if already bet
            try:
                await self.get_bet_by_id(match.id, user.id)
                increase_bet_attempt = True
            except ResourceNotFound:
                pass
            # gather team info by superstar name
            team_id = match.team_id_by_member_name(superstar_name)
            team = match.team_by_id(team_id)
            # confirm bet
            confirm_embed = quickembed.question(
                desc="**Place this bet?**",
                footer="All bets are final. You can only increase existing bets.",
                user=user,
            )
            confirm_embed.add_field(
                name="Match {}".format(match.id),
                value=match.info_text_short(),
                inline=False,
            )
            confirm_embed.add_field(
                name="Bet Amount", value="{:,}".format(bet), inline=True
            )
            confirm_embed.add_field(
                name="Betting On", value=team["members"], inline=True
            )
            confirm_message = await ctx.send(embed=confirm_embed)
            await confirm_message.add_reaction("✅")
            await confirm_message.add_reaction("❎")
            try:
                reaction, author = await self.bot.wait_for(
                    "reaction_add",
                    check=lambda reaction, author: author == ctx.author
                                                   and str(reaction.emoji) in ["✅", "❎"],
                    timeout=15.0,
                )
            except asyncio.TimeoutError:
                reaction = False
                embed = quickembed.error(
                    desc="Bet cancelled.",
                    footer="Took too long to confirm. Try again.",
                    user=user,
                )
            # await user confirmation via reaction
            if reaction:
                if str(reaction.emoji) == "✅":
                    # process bet
                    try:
                        if increase_bet_attempt:
                            await self.patch_match_bet(user.id, match.id, team_id, bet)
                            embed = quickembed.success(
                                desc="Increased bet to `{:,}` on `{}`".format(bet, team["members"]),
                                footer="All bets are final. You can only increase existing bets.",
                                user=user,
                            )
                        else:
                            await self.post_match_bet(user.id, match.id, team_id, bet)
                            embed = quickembed.success(
                                desc="Placed `{:,}` point bet on `{}`".format(bet, team["members"]),
                                footer="All bets are final. You can only increase existing bets.",
                                user=user,
                            )
                    except ValidationError as e:
                        embed = quickembed.error(desc=str(e), user=user)
                else:
                    embed = quickembed.error(desc="Bet cancelled.", footer="Requested by user.", user=user)
            await confirm_message.edit(embed=embed)
            await confirm_message.clear_reactions()

    @commands.command(name="bets")
    async def user_current_bets(self, ctx):
        user = await self.grab_user(ctx, True)
        if user.is_registered:
            try:
                bets_info = await self.get_user_current_bets(user.id)
                embed = user.bets_embed(bets_info)
            except ResourceNotFound:
                embed = quickembed.error(desc="No current bets found", user=user)
            await ctx.send(embed=embed)

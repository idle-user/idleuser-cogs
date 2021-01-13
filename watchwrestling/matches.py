import asyncio
import logging


import discord
from redbot.core import commands

from .api import IdleUserAPI, WEB_URL
from .utils import quickembed, checks
from .entities import User, Superstar, Match
from .errors import (
    IdleUserAPIError,
    UserNotRegistered,
    ResourceNotFound,
    ValidationError,
)

log = logging.getLogger("red.idleuser-cogs.WatchWrestling")


class Matches(IdleUserAPI, commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandInvokeError):
            error_msg = None
            if isinstance(error.original, asyncio.TimeoutError):
                error_msg = "Took too long to confirm. Try again."
            elif isinstance(error.original, (ValueError, IndexError)):
                error_msg = "Invalid index"
            elif isinstance(error.original, UserNotRegistered):
                error_msg = (
                    "Must be registered to use that command. `!register` to register."
                )
            elif isinstance(error.original, IdleUserAPIError):
                error_msg = str(error.original)
            if error_msg:
                user = await self.grab_user(ctx.author)
                await ctx.send(embed=quickembed.error(desc=error_msg, user=user))
            else:
                await ctx.send(
                    embed=quickembed.error(desc="Something broke. Check logs.")
                )
                raise error

    async def grab_user(self, author: discord.User) -> User:
        try:
            data = await self.get_user_by_discord_id(author.id)
            user = User(data)
            user.discord = author
        except ResourceNotFound:
            user = User.unregistered_user()
            user.discord = author
        return user

    async def dm_user_login_link(self, user: User):
        login_token = await self.post_user_login_token(user.id)
        login_link = WEB_URL + "?login_token={}&redirect_to=/projects/matches/".format(
            login_token
        )
        desc = "Quick login link for you!\n<{}>".format(login_link)
        footer = "Link expires in 5 minutes. Do not share it."
        embed = quickembed.general(desc=desc, footer=footer, user=user)
        await user.discord.send(embed=embed)

    async def dm_user_reset_link(self, user: User):
        secret_token = await self.post_user_secret_token(user.id)
        reset_link = WEB_URL + "reset-password?reset_token={}".format(secret_token)
        desc = "Quick password reset link for you!\n<{}>".format(reset_link)
        footer = "Link expires in 30 minutes. Do not share it."
        embed = quickembed.general(desc=desc, footer=footer, user=user)
        await user.discord.send(embed=embed)

    @commands.command(name="login")
    async def user_login_token_link(self, ctx):
        user = await self.grab_user(ctx.author)
        if not user.is_registered:
            raise UserNotRegistered()
        await self.dm_user_login_link(user)
        embed = quickembed.success(desc="Login link DMed", user=user)
        await ctx.send(embed=embed)

    @user_login_token_link.error
    async def user_login_token_link_error(self, ctx, error):
        pass

    @commands.command(name="register")
    async def user_register(self, ctx):
        user = await self.grab_user(ctx.author)
        if user.is_registered:
            embed = quickembed.notice(
                desc="Your Discord is already registered. Use `!login` to login.",
                user=user,
            )
        else:
            username = "{}{}".format(user.discord.name, user.discord.discriminator)
            data = await self.post_user_register(
                username=username, discord_id=str(user.discord.id)
            )
            user = User(data)
            user.discord = ctx.author
            await self.dm_user_login_link(user)
            embed = quickembed.success(desc="Successfully registered", user=user)
        if embed:
            await ctx.send(embed=embed)

    @user_register.error
    async def user_register_error(self, ctx, error):
        pass

    @commands.command(name="password-reset", aliases=["reset-pw", "reset-password"])
    async def user_secret_token_link(self, ctx):
        user = await self.grab_user(ctx.author)
        if not user.is_registered:
            raise UserNotRegistered()
        await self.dm_user_reset_link(user)
        embed = quickembed.success(desc="Password reset link DMed", user=user)
        await ctx.send(embed=embed)

    @user_secret_token_link.error
    async def user_login_secret_link_error(self, ctx, error):
        pass

    @commands.command(name="stats", aliases=["me", "bal", "points"])
    async def user_stats(self, ctx, season=4):
        user = await self.grab_user(ctx.author)
        if not user.is_registered:
            raise UserNotRegistered()
        user_stats_data = await self.get_user_stats_by_season_id(user.id, season)
        await ctx.send(embed=user.stats_embed(user_stats_data))

    @user_stats.error
    async def user_stats_error(self, ctx, error):
        pass

    @commands.command(name="ppv", aliases=["events"])
    async def upcoming_events(self, ctx):
        user = await self.grab_user(ctx.author)
        event_list = await self.get_future_events()
        embed = quickembed.info(desc="Upcoming Events (PT)", user=user)
        embed.add_field(
            name="\u200b",
            value="\n".join(
                ["{} - **{}**".format(e["date_time"], e["name"]) for e in event_list]
            ),
        )
        await ctx.send(embed=embed)

    @upcoming_events.error
    async def upcoming_events_error(self, ctx, error):
        pass

    @commands.command(name="superstar", aliases=["bio"])
    async def superstar_search(self, ctx, *, keyword):
        user = await self.grab_user(ctx.author)
        data = await self.get_superstar_search(keyword)
        superstar_list = [Superstar(d) for d in data]
        if len(superstar_list) > 1:
            msg = "Select Superstar from List ...\n```"
            for i, e in enumerate(superstar_list):
                msg = msg + "{}. {}\n".format(i + 1, e.name)
            msg = msg + "```"
            await ctx.send(embed=quickembed.question(desc=msg, user=user))
            response = await self.bot.wait_for(
                "message", check=checks.is_number(ctx.author), timeout=15.0
            )
            index = int(response.content)
            embed = superstar_list[index - 1].info_embed()
        else:
            embed = superstar_list[0].info_embed()
        await ctx.send(embed=embed)

    @superstar_search.error
    async def superstar_search_error(self, ctx, error):
        pass

    @commands.command(name="leaderboard", aliases=["top"])
    async def leaderboard(self, ctx, season=4):
        stat_list = await self.get_leaderboard_by_season_id(season)
        embed = discord.Embed(description="Season {}".format(season), color=0x0080FF)
        embed.set_author(
            name="Leaderboard",
            url=WEB_URL + "projects/matches/leaderboard?season_id={}".format(season),
            icon_url=self.bot.user.avatar_url,
        )
        lb = [
            "{}. {} ({:,})".format(i + 1, v["username"], int(v["total_points"]))
            for i, v in enumerate(stat_list[:10])
        ]
        embed.add_field(
            name="\u200b", value="\n".join(lb) if lb else "Nothing found", inline=True
        )
        await ctx.send(embed=embed)

    @leaderboard.error
    async def leaderboard_error(self, ctx, error):
        pass

    @commands.command(name="match", aliases=["match-info"])
    async def match_info(self, ctx, match_id=None):
        match_data = await self.get_match_by_id(match_id)
        match = Match(match_data)
        embed = match.info_embed()
        await ctx.send(embed=embed)

    @match_info.error
    async def match_info_error(self, ctx, error):
        pass

    @commands.command(name="matches", aliases=["open-matches"])
    async def open_matches(self, ctx):
        openbet_match_data = await self.get_openbet_matches()
        openbet_matches = []
        for match_data in openbet_match_data:
            temp_match = Match(match_data)
            if temp_match.match_type_id == 0:
                continue
            openbet_matches.append(temp_match)
        if len(openbet_matches) == 1:
            embed = openbet_matches[0].info_embed()
        elif len(openbet_matches) > 1:
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
        else:
            raise ResourceNotFound("No open bet matches found")
        await ctx.send(embed=embed)

    @open_matches.error
    async def open_matches_error(self, ctx, error):
        pass

    @commands.command(name="current-match", aliases=["currentmatch"])
    async def current_match_info(self, ctx):
        match_data = await self.get_current_match()
        match = Match(match_data)
        embed = match.info_embed()
        await ctx.send(embed=embed)

    @current_match_info.error
    async def current_match_info_error(self, ctx, error):
        pass

    @commands.command(name="recent-match", aliases=["lastmatch", "last-match"])
    async def recent_match_info(self, ctx):
        match_data = await self.get_recent_match()
        match = Match(match_data)
        embed = match.info_embed()
        await ctx.send(embed=embed)

    @recent_match_info.error
    async def recent_match_info_error(self, ctx, error):
        pass

    @commands.command(name="rate", aliases=["rate-match"])
    async def rate_match(self, ctx, rating: float):
        user = await self.grab_user(ctx.author)
        match_data = await self.get_recent_match()
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

    @rate_match.error
    async def rate_match_error(self, ctx, error):
        pass

    @commands.command(name="bet", aliases=["bet-match"])
    async def bet_match(self, ctx, bet: str, *, superstar_name: str):
        bet = int(bet.replace(",", ""))
        user = await self.grab_user(ctx.author)
        match = None
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
        # if match not found, prepare error message
        if not match:
            error_msg = "Unable to find an open match for contestant `{}`".format(
                superstar_name
            )
            embed = quickembed.error(desc=error_msg, user=user)
        # if match found, gather info and confirm bet
        else:
            # check if already bet
            try:
                await self.get_bet_by_id(match.id, user.id)
                raise IdleUserAPIError("Bet on this match already placed")
            except ResourceNotFound:
                pass
            # gather team info by superstar name
            team_id = match.team_id_by_member_name(superstar_name)
            team = match.team_by_id(team_id)
            # confirm bet
            question_embed = quickembed.question(
                desc="[Y/N] Place this bet?", user=user
            )
            question_embed.add_field(
                name="Info", value=match.info_text_short(), inline=False
            )
            question_embed.add_field(
                name="Betting", value="{:,}".format(bet), inline=True
            )
            question_embed.add_field(
                name="Betting On", value=team["members"], inline=True
            )
            await ctx.send(embed=question_embed)
            confirm = await self.bot.wait_for(
                "message", check=checks.confirm(ctx.author), timeout=15.0
            )
            confirm.content = confirm.content.upper()
            # await user confirmation
            if confirm.content == "Y":
                # process bet
                await self.post_match_bet(user.id, match.id, team_id, bet)
                msg = "Placed `{:,}` point bet on `{}`".format(bet, team["members"])
                embed = quickembed.success(desc=msg, user=user)
            elif confirm.content == "N":

                # cancel bet
                embed = quickembed.error(desc="Bet cancelled", user=user)
        await ctx.send(embed=embed)

    @bet_match.error
    async def bet_match_error(self, ctx, error):
        pass

import logging

from redbot.core import commands

from .api import IdleUserAPI, WEB_URL
from .entities import User
from .errors import ResourceNotFound
from .utils import quickembed

log = logging.getLogger("red.idleuser-cogs.idleuser")


class IdleUser(IdleUserAPI, commands.Cog):
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

    async def dm_user_login_link(self, user: User, redirect_to="/projects/matches/"):
        login_token = await self.post_user_login_token(user.id)
        login_link = WEB_URL + "?login_token={}&redirect_to={}".format(
            login_token, redirect_to
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
        user = await self.grab_user(ctx, True)
        if user.is_registered:
            await self.dm_user_login_link(user)
            embed = quickembed.success(desc="Login link DMed", user=user)
            await ctx.send(embed=embed)

    @commands.command(name="register")
    async def user_register(self, ctx):
        user = await self.grab_user(ctx)
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
        await ctx.send(embed=embed)

    @commands.command(name="password-reset", aliases=["reset-pw", "reset-password"])
    async def user_secret_token_link(self, ctx):
        user = await self.grab_user(ctx)
        if user.is_registered:
            await self.dm_user_reset_link(user)
            embed = quickembed.success(desc="Password reset link DMed", user=user)
            await ctx.send(embed=embed)

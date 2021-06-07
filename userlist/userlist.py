import re
import string
import logging

import string

import discord
from redbot.core import commands

log = logging.getLogger("red.idleuser-cogs.UserList")


class UserList(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.users_max = 10
        self.users = []
        self.message_channel = None
        self.message_id = None
        self.easy_color_list = {
            "red": 0xFF0000,
            "blue": 0x0080FF,
            "green": 0x80FF00,
            "white": 0xFFFFFF,
            "black": 0x000000,
            "orange": 0xFF8000,
            "yellow": 0xFFFF00,
        }

    async def create_embed(self, title, description, footer, color_str):
        color_str = color_str.replace("#", "")
        if all(c in string.hexdigits for c in color_str):
            color = int(color_str, 16)
        else:
            color = self.easy_color_list.get(color_str, 0x36393F)
        embed = discord.Embed(color=color)
        embed.set_author(name=title)
        embed.set_footer(text=footer)
        embed.description = description
        return embed

    @commands.command(name="userlist-max")
    @commands.has_permissions(manage_messages=True)
    async def set_existing_list(self, ctx, users_max: int):
        self.users_max = users_max
        await ctx.message.add_reaction("✅")

    @commands.command(name="userlist-set")
    @commands.has_permissions(manage_messages=True)
    async def set_existing_list(
        self, ctx, channel: discord.TextChannel, message_id: int
    ):
        try:
            message = await channel.fetch_message(message_id)
            current_embed = message.embeds[0]
            self.message_channel = channel
            self.message_id = message_id
            self.users_max = re.sub("[^0-9]", "", current_embed.footer.text)
            for field in current_embed.fields:
                self.users.append(field.name)
            await ctx.message.add_reaction("✅")
        except discord.HTTPException:
            return await ctx.send("Existing list not found.")

    @commands.command(name="userlist-create", aliases=["userlist-start"])
    @commands.has_permissions(manage_messages=True)
    async def create_list(
        self,
        ctx,
        title: str = "User List",
        description: str = None,
        users_max: int = 10,
        color_str: str = "blue",
    ):
        try:
            await ctx.message.delete()
        except:
            pass
        footer = "{} entries max".format(users_max)
        embed = await self.create_embed(title, description, footer, color_str)
        message = await ctx.send(embed=embed)
        self.users_max = users_max
        self.users = []
        self.message_channel = message.channel
        self.message_id = message.id

    @commands.command(name="userlist-clear")
    @commands.has_permissions(manage_messages=True)
    async def clear_list(self, ctx):
        try:
            message = await self.message_channel.fetch_message(self.message_id)
            current_embed = message.embeds[0]
            current_embed.clear_fields()
            self.users = []
            await message.edit(embed=current_embed)
            await ctx.message.add_reaction("✅")
        except discord.HTTPException:
            return await ctx.send("No message found.")

    @commands.command(name="userlist-pop", aliases=["userlist-remove"])
    @commands.has_permissions(manage_messages=True)
    async def remove_from_list(self, ctx, index: int = 0):
        try:
            message = await self.message_channel.fetch_message(self.message_id)
            current_embed = message.embeds[0]
            current_embed.remove_field(index)
            self.users.pop(index)
            await message.edit(embed=current_embed)
            await ctx.message.add_reaction("✅")
        except discord.HTTPException:
            return await ctx.send("No message found.")

    @commands.command(name="userlist-join", aliases=["userlist-enter"])
    async def join_list(self, ctx, *, comment: str):
        if self.message_channel and self.message_id:
            if ctx.author not in self.users:
                try:
                    message = await self.message_channel.fetch_message(self.message_id)
                    embed = message.embeds[0]
                    if len(embed.fields) < self.users_max:
                        embed.add_field(name=ctx.author, value=comment, inline=False)
                        await message.edit(embed=embed)
                        self.users.append(ctx.author)
                        await ctx.message.add_reaction("✅")
                    else:
                        await ctx.send(
                            "Current list has reached max of {}. Please try later.".format(
                                self.users_max
                            )
                        )
                except discord.HTTPException:
                    await ctx.send("List not found.")
            else:
                await ctx.send("You're already in the list!")
        else:
            await ctx.send("No existing list found.")

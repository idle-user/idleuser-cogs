import logging
import string

import discord
from redbot.core import commands, checks

log = logging.getLogger("red.idleuser-cogs.EasyEmbed")


class EasyEmbed(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
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

    @commands.command(name="easyembed", aliases=["embedthis"])
    @checks.is_owner()
    async def embed_message(self, ctx, title: str, description: str, footer: str, color: str):
        try:
            await ctx.message.delete()
        except:
            pass
        embed = await self.create_embed(title, description, footer, color)
        await ctx.send(embed=embed)

    @commands.command(name="easyembed-edit", aliases=["easyembed-update", "replacethis"])
    @checks.is_owner()
    async def replace_embed_message(
            self,
            ctx,
            channel: discord.TextChannel,
            message_id: int,
            title: str,
            description: str,
            footer: str,
            color: str,
    ):
        try:
            await ctx.message.delete()
        except:
            pass
        try:
            message = await channel.fetch_message(message_id)
        except discord.HTTPException:
            return await ctx.maybe_send_embed("No message found to replace.")
        embed = await self.create_embed(title, description, footer, color)

        await message.edit(embed=embed)

import asyncio
import logging

import discord
from redbot.core import commands

from .api import IdleUserAPI
from .entities import User, Prompt, Choice
from .errors import ResourceNotFound, IdleUserAPIError, ConflictError
from .utils import quickembed

log = logging.getLogger("red.idleuser-cogs.pickem")


class Pickem(IdleUserAPI, commands.Cog):
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

    @commands.command(name="pickem-stats", aliases=["pickstats", "pickemstats"])
    async def user_stats(self, ctx):
        user = await self.grab_user(ctx, True)
        if user.is_registered:
            user_stats_data = await self.get_pickem_stats_by_id(user.id)
            await ctx.send(embed=user.stats_embed(user_stats_data))

    # @commands.command(name="leaderboard", aliases=["top"])
    # async def leaderboard(self, ctx, season=7):
    #     stat_list = await self.get_leaderboard_by_season_id(season)
    #     embed = discord.Embed(description="Season {}".format(season), color=0x0080FF)
    #     embed.set_author(
    #         name="Leaderboard",
    #         url=WEB_URL + "projects/matches/leaderboard?season_id={}".format(season),
    #         icon_url=self.bot.user.display_avatar,
    #     )
    #     lb = [
    #         "{}. {} ({:,})".format(i + 1, v["username"], int(v["total_points"]))
    #         for i, v in enumerate(stat_list[:10])
    #     ]
    #     embed.add_field(
    #         name="\u200b", value="\n".join(lb) if lb else "Nothing found", inline=True
    #     )
    #     await ctx.send(embed=embed)
    #
    # @leaderboard.error
    # async def leaderboard_error(self, ctx, error):
    #     pass

    @commands.command(name="pick", aliases=["picks"])
    async def open_pickem_prompts(self, ctx):
        user = await self.grab_user(ctx, True)
        if not user.is_registered:
            return

        try:
            open_prompts_data = await self.get_pickem_prompts(1)
        except ResourceNotFound:
            await ctx.send(embed=quickembed.error("No open Pickems available.\nCreate one with: `!pickem`", user=user))
            return

        open_prompts = []
        open_prompts_len = len(open_prompts_data)
        for i, prompt_data in enumerate(open_prompts_data):
            prompt = Prompt(prompt_data)

            embed = quickembed.info(desc="[Pickem {}]".format(prompt.id))
            embed.set_author(
                name="Open Pickem Prompts",
                icon_url=ctx.author.display_avatar
            )
            embed.set_footer(text="☑️ to Pick - Page [{}/{}]".format(i + 1, open_prompts_len))
            embed.add_field(
                name="{}".format(prompt.subject),
                value="",
                inline=True,
            )
            prompt.page_prompt_embed = embed
            open_prompts.append(prompt)

        await self.start_pick_pages(ctx, open_prompts, user)

    async def start_pick_pages(self, ctx, open_prompts: list[Prompt], user: User):
        page_i = None
        page_i_max = len(open_prompts) - 1
        valid_reactions = ["⬅️", "☑️", "➡️"]
        active_message = await ctx.send(embed=open_prompts[0].page_prompt_embed)
        while True:
            if page_i is not None:
                print(f"Page: {page_i}")
                embed = open_prompts[page_i].page_prompt_embed
                await active_message.edit(embed=embed)
                await active_message.clear_reactions()
            else:
                page_i = 0
            for valid_reaction in valid_reactions:
                await active_message.add_reaction(valid_reaction)

            reaction = False
            try:
                reaction, author = await self.bot.wait_for(
                    "reaction_add",
                    check=lambda reaction, author: author == ctx.author
                                                   and str(reaction.emoji) in valid_reactions,
                    timeout=15.0,
                )
            except asyncio.TimeoutError:
                pass

            if reaction:
                if str(reaction.emoji) == "⬅️":
                    # previous page
                    if page_i == 0:
                        page_i = page_i_max
                    else:
                        page_i -= 1
                    continue
                elif str(reaction.emoji) == "➡️":
                    # next page
                    if page_i >= page_i_max:
                        page_i = 0
                    else:
                        page_i += 1
                    continue
                elif str(reaction.emoji) == "☑️":
                    selected_prompt = open_prompts[page_i]
                    if not selected_prompt.choices:
                        selected_prompt_data = await self.get_pickem_prompt_by_id(open_prompts[page_i].id)
                        selected_prompt = Prompt(selected_prompt_data)
                        selected_prompt.page_prompt_embed = open_prompts[page_i].page_prompt_embed
                        open_prompts[page_i] = selected_prompt
                    active_message = await self.start_pick(ctx,
                                                           prompt=selected_prompt,
                                                           user=user,
                                                           active_message=active_message)
                    if not active_message:
                        return
                else:
                    embed = quickembed.error(
                        desc="Something went wrong.",
                        footer="Couldn't find any valid reaction emojis.",
                        user=user,
                    )
                    await active_message.edit(embed=embed, delete_after=5)
                    return

            else:
                embed = quickembed.error(
                    desc="Pickems cancelled.",
                    footer="No action received. `!picks` to try again.",
                    user=user,
                )
                await active_message.edit(embed=embed)
                await active_message.clear_reactions()
                return

    async def start_pick(self, ctx, prompt: Prompt, user: User, active_message: discord.Message = None):
        if active_message is None:
            await ctx.send(embed=prompt.info_embed())
        else:
            await active_message.edit(embed=prompt.info_embed())
        await active_message.clear_reactions()

        valid_reactions = Choice.choice_emojis + ["❌"]
        max_i = len(prompt.choices)
        for i, valid_reaction in enumerate(valid_reactions):
            if i >= max_i:
                break
            await active_message.add_reaction(valid_reaction)
        await active_message.add_reaction("❌")

        reaction = False
        try:
            reaction, author = await self.bot.wait_for(
                "reaction_add",
                check=lambda reaction, author: author == ctx.author
                                               and str(reaction.emoji) in valid_reactions,
                timeout=15.0,
            )
        except asyncio.TimeoutError:
            pass

        delete_after = 5
        if reaction:
            if str(reaction.emoji) == "❌":
                return active_message
            elif str(reaction.emoji) in Choice.choice_emojis:
                pick_choice_i = Choice.choice_emojis.index(str(reaction))
                pick_choice = prompt.choices[pick_choice_i]

                put_title = None
                try:
                    try:
                        await self.post_pickem_pick(user.id, prompt.id, pick_choice.id)
                        put_title = "Pick Added"
                    except ConflictError as e:
                        await self.patch_pickem_pick(user.id, prompt.id, pick_choice.id)
                        put_title = "Pick Updated"
                except IdleUserAPIError as e:
                    embed = quickembed.error(desc=str(e), user=user)

                if put_title:
                    embed = quickembed.success(desc="[Pickem {}]".format(prompt.id))
                    embed.set_author(
                        name="Pick Added",
                        icon_url=ctx.author.display_avatar
                    )
                    embed.set_footer(text="You are allowed update existing picks.")
                    embed.add_field(
                        name="{}".format(prompt.subject),
                        value="{}".format(pick_choice.subject),
                        inline=True,
                    )
                    delete_after = None
            else:
                embed = quickembed.error(
                    desc="Something went wrong.",
                    footer="Couldn't find any valid reaction emojis.",
                    user=user,
                )
        else:
            embed = quickembed.error(
                desc="Pickems cancelled.",
                footer="No action received. `!picks` to try again.",
                user=user,
            )

        await active_message.edit(embed=embed, delete_after=delete_after)
        await active_message.clear_reactions()
        return False

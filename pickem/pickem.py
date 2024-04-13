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

    async def grab_user(self, ctx: commands.Context, author=None, registration_required_message=False) -> User:
        author = author if author is not None else ctx.author
        try:
            data = await self.get_user_by_discord_id(author.id)
            user = User(data)
            user.discord = author
        except ResourceNotFound:
            user = User.unregistered_user()
            user.discord = author
            if registration_required_message:
                embed = quickembed.error(
                    desc=f"You must be registered to use this command. Use `{ctx.prefix}register` to register.",
                    user=user)
                await ctx.send(embed=embed)
        return user

    @commands.command(name="pickem-stats", aliases=["pickstats", "pickemstats", "pstats", "ps"])
    async def user_stats(self, ctx: commands.Context, show_more=None):
        user = await self.grab_user(ctx, registration_required_message=True)
        if user.is_registered:
            try:
                user_stats_data = await self.get_pickem_stats_by_id(user.id)
                if show_more:
                    embed = user.stats_full_embed(user_stats_data)
                else:
                    embed = user.stats_embed(user_stats_data)
                await ctx.send(embed=embed)
            except IdleUserAPIError as e:
                await ctx.send(embed=quickembed.error(str(e), user=user))

    @commands.command(name="top-picks", aliases=["toppicks", "picks-leaderboard", "ptop"], enabled=False)
    async def leaderboard(self, ctx: commands.Context):
        # TODO
        pass

    @commands.command(name="pickem", aliases=["pickems", "open"])
    async def add_pickem_prompt(self, ctx: commands.Context, subject: str, *choice_subjects: str):
        user = await self.grab_user(ctx, registration_required_message=True)
        if not user.is_registered:
            return
        choices_len = len(choice_subjects) if choice_subjects is not None else 0
        if choices_len < 2 or choices_len > 5:
            embed = quickembed.error("Please provide at 2-5 choices.", user=user)
            await ctx.send(embed=embed, delete_after=10)
            return

        # confirm pickem creation
        confirm_embed = quickembed.question(
            desc="**{}**".format(subject),
            footer="Pickem creations are final.",
            user=user,
        )
        confirm_embed.set_author(
            name="Create Pickem?",
            icon_url=user.discord.display_avatar,
            url=user.url,
        )
        for i, valid_reaction in enumerate(Choice.choice_emojis):
            if i >= choices_len:
                break
            confirm_embed.add_field(
                name="{} {}".format(valid_reaction, choice_subjects[i]),
                value="",
                inline=False,
            )

        confirm_message = await ctx.send(embed=confirm_embed)
        await confirm_message.add_reaction("✅")
        await confirm_message.add_reaction("❌")
        try:
            reaction, author = await self.bot.wait_for(
                "reaction_add",
                check=lambda reaction, author: author == ctx.author
                                               and reaction.message.id == confirm_message.id
                                               and str(reaction.emoji) in ["✅", "❌"],
                timeout=30.0,
            )
        except asyncio.TimeoutError:
            reaction = False
            embed = quickembed.error(
                desc="Pickem creation cancelled.",
                footer="Took too long to confirm. Try again.",
                user=user,
            )
            await confirm_message.edit(embed=embed)
            await confirm_message.clear_reactions()

        if reaction:
            if str(reaction.emoji) == "✅":
                try:
                    prompt_data = await self.post_pickem_prompt(user_id=user.id,
                                                                group_id=ctx.guild.id,
                                                                subject=subject,
                                                                choices=choice_subjects)
                except IdleUserAPIError as e:
                    embed = quickembed.error(desc=str(e), user=user)
                    await confirm_message.edit(embed=embed, delete_after=10)
                    return

                prompt = Prompt(prompt_data)
                prompt.user = user
                active_message = await self.start_pick(ctx, prompt=prompt, user=user, active_message=confirm_message)
                if active_message:
                    await active_message.clear_reactions()
                    return
            else:
                embed = quickembed.error(desc="Pickem creation cancelled.", footer="Requested by user.", user=user)
                await confirm_message.edit(embed=embed)
                await confirm_message.clear_reactions()

    @commands.command(name="pick", aliases=["picks"])
    async def open_pickem_prompts(self, ctx: commands.Context):
        user = await self.grab_user(ctx, registration_required_message=True)
        if not user.is_registered:
            return

        try:
            open_prompts_data = await self.get_pickem_prompts(ctx.guild.id, prompt_open=1)
        except ResourceNotFound:
            await ctx.send(
                embed=quickembed.error(desc=f"No open Pickems available.\nCreate one with: `{ctx.prefix}pickem`",
                                       user=user))
            return

        open_prompts = []
        open_prompts_len = len(open_prompts_data)
        for i, prompt_data in enumerate(open_prompts_data):
            prompt = Prompt(prompt_data)

            embed = quickembed.info(desc="")
            embed.set_author(
                name="Open Pickems",
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

    @commands.command(name="close", aliases=["mypickems", "close-pickems", "close-picks"])
    async def user_pickem_prompts(self, ctx: commands.Context):
        user = await self.grab_user(ctx, registration_required_message=True)
        if not user.is_registered:
            return

        try:
            open_prompts_data = await self.get_pickem_prompts(ctx.guild.id, prompt_open=1, user_id=user.id)
        except ResourceNotFound:
            await ctx.send(
                embed=quickembed.error(
                    desc=f"You don't have any Pickems available.\nCreate one with: `{ctx.prefix}pickem`",
                    user=user))
            return

        open_prompts = []
        open_prompts_len = len(open_prompts_data)
        for i, prompt_data in enumerate(open_prompts_data):
            prompt = Prompt(prompt_data)

            embed = quickembed.info(desc="")
            embed.set_author(
                name="Close Your Pickem?",
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

        await self.start_pick_pages(ctx, open_prompts, user, is_closing_prompt=True)

    async def start_pick_pages(self, ctx: commands.Context,
                               open_prompts: list[Prompt],
                               user: User,
                               is_closing_prompt=False):
        page_i = None
        page_i_max = len(open_prompts) - 1
        valid_reactions = ["⬅️", "☑️", "➡️"] if len(open_prompts) > 1 else ["☑️"]
        active_message = await ctx.send(embed=open_prompts[0].page_prompt_embed)
        while True:
            if page_i is not None:
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
                                                   and reaction.message.id == active_message.id
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
                        user_data = await self.get_user_by_id(selected_prompt.user_id)
                        selected_prompt.user = User(user_data)
                        open_prompts[page_i] = selected_prompt

                    if is_closing_prompt:
                        return await self.start_close_pickem_prompt(ctx,
                                                                    prompt=selected_prompt,
                                                                    user=user,
                                                                    active_message=active_message)
                    else:
                        active_message = await self.start_pick(ctx,
                                                               prompt=selected_prompt,
                                                               user=user,
                                                               active_message=active_message,
                                                               allow_back=True)
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
                if is_closing_prompt:
                    embed = quickembed.error(
                        desc="Close Pickems cancelled.",
                        footer=f"No action received. `{ctx.prefix}close` to try again.",
                        user=user,
                    )
                else:
                    embed = quickembed.error(
                        desc="Select Pick cancelled.",
                        footer=f"No action received. `{ctx.prefix}picks` to try again.",
                        user=user,
                    )
                await active_message.edit(embed=embed)
                await active_message.clear_reactions()
                return

    async def start_pick(self, ctx: commands.Context, prompt: Prompt, user: User,
                         active_message: discord.Message = None,
                         allow_back=False):
        prompt_embed = prompt.info_embed(caller=user, custom_title="Picks Started")
        if active_message is None:
            active_message = await ctx.send(embed=prompt_embed)
        else:
            await active_message.edit(embed=prompt_embed)
        await active_message.clear_reactions()

        valid_reactions = Choice.choice_emojis
        if allow_back:
            valid_reactions += ["❌"]
        max_i = len(prompt.choices)
        for i, valid_reaction in enumerate(valid_reactions):
            if i >= max_i:
                break
            await active_message.add_reaction(valid_reaction)
        if allow_back:
            await active_message.add_reaction("❌")

        try:
            while True:
                reaction, author = await self.bot.wait_for(
                    "reaction_add",
                    check=lambda reaction, author: reaction.message.id == active_message.id
                                                   and str(reaction.emoji) in valid_reactions,
                    timeout=15.0,
                )
                if allow_back and author == ctx.author and str(reaction.emoji) == "❌":
                    return active_message
                elif str(reaction.emoji) != "❌" and str(reaction.emoji) in Choice.choice_emojis:
                    pick_choice_i = Choice.choice_emojis.index(str(reaction.emoji))
                    pick_choice = prompt.choices[pick_choice_i]
                    await self.start_pick_submit(ctx, author, prompt, pick_choice)
        except asyncio.TimeoutError:
            prompt_embed = prompt.info_embed(caller=user,
                                             custom_title=f"Picks Closed - `{ctx.prefix}picks` to start again",
                                             red=True)
            await active_message.edit(embed=prompt_embed)
            await active_message.clear_reactions()
            return False

    async def start_pick_submit(self, ctx: commands.Context, author, prompt: Prompt, choice: Choice):
        user = await self.grab_user(ctx, author, registration_required_message=True)
        if not user.is_registered:
            return

        put_title = None
        try:
            try:
                await self.post_pickem_pick(user.id, prompt.id, choice.id)
                put_title = "Pick Added"
            except ConflictError as e:
                await self.patch_pickem_pick(user.id, prompt.id, choice.id)
                put_title = "Pick Updated"
        except IdleUserAPIError as e:
            embed = quickembed.error(desc=str(e), user=user)

        if put_title:
            embed = quickembed.success(desc="{}".format(prompt.subject))
            embed.set_author(
                name="{} - {}".format(user.username, put_title),
                icon_url=user.discord.display_avatar
            )
            embed.set_footer(text="You are allowed update existing picks. [pickem {}]".format(prompt.id))
            embed.add_field(
                name="{}".format(choice.subject),
                value="",
                inline=True,
            )

        await ctx.send(embed=embed)

    async def start_close_pickem_prompt(self, ctx: commands.Context, prompt: Prompt, user: User,
                                        active_message: discord.Message = None):
        prompt_embed = prompt.info_embed(caller=user, custom_title="Close Pickem - Select Pick Result")
        if active_message is None:
            active_message = await ctx.send(embed=prompt_embed)
        else:
            await active_message.edit(embed=prompt_embed)
        await active_message.clear_reactions()

        valid_reactions = Choice.choice_emojis + ["❌"]
        max_i = len(prompt.choices)
        for i, valid_reaction in enumerate(valid_reactions):
            if i >= max_i:
                break
            await active_message.add_reaction(valid_reaction)
        await active_message.add_reaction("❌")

        try:
            reaction, author = await self.bot.wait_for(
                "reaction_add",
                check=lambda reaction, author: author == ctx.author
                                               and reaction.message.id == active_message.id
                                               and str(reaction.emoji) in valid_reactions,
                timeout=15.0,
            )
            if str(reaction.emoji) in Choice.choice_emojis:
                pick_choice_i = Choice.choice_emojis.index(str(reaction))
                pick_choice = prompt.choices[pick_choice_i]
                prompt_embed = await self.start_pickem_result_submit(ctx, prompt, pick_choice)
            else:
                prompt_embed = quickembed.error(desc="Close Pickem cancelled.", footer="Requested by user.", user=user)
        except asyncio.TimeoutError:
            prompt_embed = quickembed.error(desc="Close Pickem cancelled.",
                                            footer="Ran out of time - `{ctx.prefix}close` to start again", user=user)

        await active_message.edit(embed=prompt_embed)
        await active_message.clear_reactions()

    async def start_pickem_result_submit(self, ctx: commands.Context, prompt: Prompt, choice: Choice):
        user = await self.grab_user(ctx, registration_required_message=True)
        if not user.is_registered:
            return

        try:
            await self.patch_pickem_prompt(user_id=user.id, prompt_id=prompt.id, prompt_open=0, choice_result=choice.id)
            embed = quickembed.success(desc="{}".format(prompt.subject))
            embed.set_author(
                name="Pickem Closed - Result Added",
                icon_url=ctx.author.display_avatar
            )
            embed.set_footer(text="Pickem results are final. [pickem {}]".format(prompt.id))
            embed.add_field(
                name="{}".format(choice.subject),
                value="",
                inline=True,
            )
        except IdleUserAPIError as e:
            embed = quickembed.error(desc=str(e), user=user)

        return embed

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

    @commands.command(name="top-picks", aliases=["toppicks", "picks-leaderboard"], enabled=False)
    async def open_pickem_prompts(self, ctx):
        # TODO
        pass

    @commands.command(name="pickem", aliases=["pickems"])
    async def add_pickem_prompt(self, ctx, subject: str, *choice_subjects: str):
        user = await self.grab_user(ctx, True)
        if not user.is_registered:
            return
        choices_len = len(choice_subjects) if choice_subjects is not None else 0
        if choices_len < 2 or choices_len > 5:
            embed = quickembed.error("Please provide at 2-5 choices.", user=user)
            await ctx.send(embed=embed, delete_after=10)
            return

        # confirm pickem creation
        confirm_embed = quickembed.question(
            desc="**Confirm Pickem Creation?**",
            footer="Pickem creations are final. Are you sure you want to submit?",
            user=user,
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
                check=lambda reaction, author: author == ctx.author and str(reaction.emoji) in ["✅", "❌"],
                timeout=15.0,
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
                    prompt_data = await self.post_pickem_prompt(user_id=user.id, subject=subject,
                                                                choices=choice_subjects)
                except IdleUserAPIError as e:
                    embed = quickembed.error(desc=str(e), user=user)
                    await confirm_message.edit(embed=embed, delete_after=10)
                    return

                prompt = Prompt(prompt_data)
                active_message = await self.start_pick(ctx, prompt=prompt, user=user, active_message=confirm_message)
                if active_message:
                    await active_message.clear_reactions()
                    return
            else:
                embed = quickembed.error(desc="Pickem creation cancelled.", footer="Requested by user.", user=user)
                await confirm_message.edit(embed=embed)
                await confirm_message.clear_reactions()

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
            active_message = await ctx.send(embed=prompt.info_embed())
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

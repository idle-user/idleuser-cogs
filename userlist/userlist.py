import re
import string
import logging

import string

import discord
from redbot.core import commands

log = logging.getLogger("red.idleuser-cogs.UserList")


class UserList(commands.Cog):
    """This cog contains commands used for creating a list of users.

    This is designed as a quick tool for moderators to allows users to join a queue.
    Moderators are able to remove and limit users from the queue.
    Moderators can set the toggle history checking from previous queues.

    Messages for the commands are deleted after a response.
    """

    def __init__(self, bot):
        self.bot = bot
        self.users = []
        self.users_max = 10
        self.history = []
        self.history_max = 3
        self.history_users = []
        self.history_on = False
        self.userlist_message = None
        self.deletion_delay = 5.0
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
        """
        Called to create a quick embeded message.
        """
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

    async def message_is_list(self, message):
        """
        Called to check if the message is a previous UserList.
        """
        if message.author == self.bot.user:
            try:
                current_embed = message.embeds[0]
                self.users_max = int(re.sub("[^0-9]", "", current_embed.footer.text))
                return True
            except:
                pass
        return False

    async def update_history(self):
        """
        Called to update the UserList history.
        """
        if self.userlist_message:
            async for message in self.userlist_message.channel.history(
                limit=100, before=self.userlist_message, oldest_first=False
            ):
                if await self.message_is_list(message):
                    self.history.append(message)
                    for field in message.embeds[0].fields:
                        self.history_users.append(field.name)
                    if len(self.history) >= self.history_max - 1:
                        break

    @commands.command(name="userlist-info")
    @commands.has_permissions(manage_messages=True)
    async def view_info(self, ctx):
        """View the current UserList settings."""
        description = "Max Entries: {0.users_max}\nCurrent Entries: {1}\n\nTracking History: {0.history_on}\nHistory Max: {0.history_max}".format(
            self, len(self.users)
        )
        if self.userlist_message:
            description += "\n\n[Current List]({})".format(
                self.userlist_message.jump_url
            )
        else:
            description += (
                "\n\nNo current UserList set.\nUse `!userlist-start` or `!userlist-set`"
            )
        footer = ""
        embed = await self.create_embed(
            "UserList Settings", description, footer, "white"
        )
        await ctx.send(embed=embed)

    @commands.command(name="userlist-create", aliases=["userlist-start"])
    @commands.has_permissions(manage_messages=True)
    async def create_list(
        self,
        ctx,
        title: str = "UserList",
        description: str = None,
        users_max: int = 10,
        color_str: str = "blue",
    ):
        """Creates a new UserList in the current channel.

        Example:
            - `[p]userlist-create`
            - `[p]userlist-create Title`
            - `[p]userlist-create Title "The description goes here"`
            - `[p]userlist-create Title "The description goes here" 5`
            - `[p]userlist-create Title "The description goes here" 5 yellow`
        Remember to use quotes if using more than one word per arguement.

        **Arguments:**

        - `<title>` The title of the UserList to be displayed.
        - `<description>` The description of the UserList to be displayed.
        - `<users_max>` The max number of entries for the UserList. Must be integer.
        - `<color_str>` The color of the embeded message.
            Color options: ["red", "blue", "green", "white", black", "orange", "yellow"]
        """
        footer = "{} entries max".format(users_max)
        embed = await self.create_embed(title, description, footer, color_str)
        self.userlist_message = await ctx.send(embed=embed)
        self.users = []
        self.users_max = users_max
        await ctx.message.delete(delay=self.deletion_delay)
        if self.history_on:
            await self.update_history()

    @commands.command(name="userlist-join", aliases=["userlist-enter"])
    async def join_list(self, ctx, *, comment: str):
        """Enters the current UserList.

        Example:
            - `[p]userlist-join Can't wait to till it's my turn`

        **Arguments:**

        - `<comment>` A comment to be displayed along with the UserList entry.
        """
        if self.userlist_message:
            if str(ctx.author) not in self.users:
                if self.history_on and str(ctx.author) in self.history_users:
                    await ctx.send(
                        "You've already entered in the past `{}` UserLists.\nPlease try another time.".format(
                            self.history_max
                        ),
                        delete_after=self.deletion_delay,
                    )
                else:
                    try:
                        embed = self.userlist_message.embeds[0]
                        if len(embed.fields) < self.users_max:
                            embed.add_field(
                                name=ctx.author, value=comment, inline=False
                            )
                            await self.userlist_message.edit(embed=embed)
                            self.users.append(str(ctx.author))
                            await ctx.message.add_reaction("✅")
                        else:
                            await ctx.send(
                                "Current list has reached max of {}. Please try later.".format(
                                    self.users_max
                                ),
                                delete_after=self.deletion_delay,
                            )
                    except discord.HTTPException:
                        await ctx.send(
                            "List not found.", delete_after=self.deletion_delay
                        )
            else:
                await ctx.send(
                    "You're already in the list!",
                    delete_after=self.deletion_delay,
                )
        else:
            await ctx.send("No existing list found.", delete_after=self.deletion_delay)
        await ctx.message.delete(delay=self.deletion_delay)

    @commands.command(name="userlist-set")
    @commands.has_permissions(manage_messages=True)
    async def set_existing_list(
        self, ctx, channel: discord.TextChannel, message_id: int
    ):
        """Define the UserList to continue using instead of starting a new one.

        Example:
            - `[p]userlist-set #userlist-channel 012345689`

        **Arguments:**

        - `<channel>` The text channel the UserList message is in.
        - `<message_id>` The id of the UserList message.
        """
        try:
            message = await channel.fetch_message(message_id)
            if await self.message_is_list(message):
                current_embed = message.embeds[0]
                self.userlist_message = message
                self.users_max = int(re.sub("[^0-9]", "", current_embed.footer.text))
                self.users = []
                for field in current_embed.fields:
                    self.users.append(field.name)
                await ctx.message.add_reaction("✅")
                await ctx.message.delete(delay=self.deletion_delay)
                if self.history_on:
                    await self.update_history()
            else:
                await ctx.send("Invalid UserList.", delete_after=self.deletion_delay)
        except discord.HTTPException:
            return await ctx.send(
                "Existing UserList not found.", delete_after=self.deletion_delay
            )

    @commands.command(name="userlist-max")
    @commands.has_permissions(manage_messages=True)
    async def set_user_max(self, ctx, users_max: int):
        """Set the max number of entries for the UserList.

        Example:
            - `[p]userlist-max 5`

        **Arguments:**

        - `<users_max>` The max number of entries for the UserList. Must be integer.
        """
        self.users_max = users_max
        await ctx.message.add_reaction("✅")
        await ctx.send(
            "UserList Max set to: `{}`.".format(users_max),
            delete_after=self.deletion_delay,
        )
        await ctx.message.delete(delay=self.deletion_delay)

    @commands.command(name="userlist-history")
    @commands.has_permissions(manage_messages=True)
    async def toggle_history(self, ctx):
        """Toggle whether or not there is a check on past UserLists.

        This is used to limit users who routinely join UserLists, allowing for other users to join.
        """
        self.history_on = not self.history_on
        await ctx.message.add_reaction("✅")
        await ctx.send(
            "UserList history is now `{}`.".format("ON" if self.history_on else "OFF"),
            delete_after=self.deletion_delay,
        )
        await ctx.message.delete(delay=self.deletion_delay)
        if self.history_on:
            await self.update_history()

    @commands.command(name="userlist-history-max")
    @commands.has_permissions(manage_messages=True)
    async def set_history_max(self, ctx, history_max: int):
        """Set the max number of UserLists to watch.

        Example:
            - `[p]userlist-history-max 2`
        This will check the current and the previous UserList.
        Users in the previous UserList will not be able to join the current one.
        UserList History must be turned on. Toggle with: `userlist-history`

        **Arguments:**

        - `<history_max>` The max number of UserLists to watch. Must be integer.
        """
        self.history_max = history_max
        await ctx.message.add_reaction("✅")
        await ctx.send(
            "Now tracking the last `{}` UserLists.".format(self.history_max),
            delete_after=self.deletion_delay,
        )
        await ctx.message.delete(delay=self.deletion_delay)
        if self.history_on:
            await self.update_history()

    @commands.command(name="userlist-delete-delay")
    @commands.has_permissions(manage_messages=True)
    async def set_message_delete(self, ctx, deletion_delay: float = 5.0):
        """Set the delay timer for when messages are deleted.

        Example:
            - `[p]userlist-delete-delay 10.0`
        This will set the message deletion delay to 10 seconds.

        **Arguments:**

        - `<deletion_delay>` The number of seconds before the message is deleted. Must be float.
        """
        self.deletion_delay = deletion_delay
        await ctx.message.add_reaction("✅")
        await ctx.send(
            "Message deleletion delay set to: `{}`.".format(self.deletion_delay),
            delete_after=self.deletion_delay,
        )
        await ctx.message.delete(delay=self.deletion_delay)

    @commands.command(name="userlist-rename")
    @commands.has_permissions(manage_messages=True)
    async def change_title_and_description(self, ctx, title: str, description: str):
        """Change the current UserList's title and description

        Example:
            - `[p]userlist-rename "New Title" "New Description"`
        Remember to use quotes if using more than one word per arguement.

        **Arguments:**

        - `<title>` The new title of the UserList to be displayed.
        - `<description>` The new description of the UserList to be displayed.
        """
        if self.userlist_message:
            current_embed = self.userlist_message.embeds[0]
            current_embed.title = title
            current_embed.description = description
            await self.userlist_message.edit(embed=current_embed)
            await ctx.message.add_reaction("✅")
            await ctx.message.delete(delay=self.deletion_delay)
        else:
            await ctx.send("No existing list found.", delete_after=self.deletion_delay)

    @commands.command(name="userlist-clear")
    @commands.has_permissions(manage_messages=True)
    async def clear_list(self, ctx):
        """Empties out the current UserList."""
        if self.userlist_message:
            current_embed = self.userlist_message.embeds[0]
            current_embed.clear_fields()
            self.users = []
            await self.userlist_message.edit(embed=current_embed)
            await ctx.message.add_reaction("✅")
            await ctx.message.delete(delay=self.deletion_delay)
            if self.history_on:
                await self.update_history()
        else:
            await ctx.send("No existing list found.", delete_after=self.deletion_delay)

    @commands.command(name="userlist-pop")
    @commands.has_permissions(manage_messages=True)
    async def pop_from_list(self, ctx, index: int = 0):
        """Remove an entry off the UserList based on index.

        Example:
            - `[p]userlist-pop`
            - `[p]userlist-pop 2

        **Arguments:**

        - `<index>` The index to remove from the UserList. Must be integer. Default is 0.
        """
        if self.userlist_message:
            current_embed = self.userlist_message.embeds[0]
            current_embed.remove_field(index)
            self.users.pop(index)
            await self.userlist_message.edit(embed=current_embed)
            await ctx.message.add_reaction("✅")
            await ctx.message.delete(delay=self.deletion_delay)
        else:
            await ctx.send("No existing list found.", delete_after=self.deletion_delay)

    @commands.command(name="userlist-remove")
    @commands.has_permissions(manage_messages=True)
    async def remove_from_list(self, ctx, username: str):
        """Remove an entry off the UserList based on string.

        Example:
            - `[p]userlist-remove username#123`

        **Arguments:**

        - `<username>` The user to remove off the UserList. Best to copy/paste from the UserList.
        """
        if self.userlist_message:
            current_embed = self.userlist_message.embeds[0]
            pop_index = -1
            for field_index, field in enumerate(current_embed.fields):
                if field.name == username:
                    pop_index = field_index
            if pop_index > -1:
                self.users.pop(pop_index)
                current_embed.remove_field(pop_index)
                await self.userlist_message.edit(embed=current_embed)
                await ctx.message.add_reaction("✅")
            else:
                await ctx.send(
                    "Unable to find `{}` in recent list.".format(username),
                    delete_after=self.deletion_delay,
                )
            await ctx.message.delete(delay=self.deletion_delay)
        else:
            await ctx.send("No existing list found.", delete_after=self.deletion_delay)

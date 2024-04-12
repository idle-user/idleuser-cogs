from .api import WEB_URL
from .utils import quickembed


class User:
    def __init__(self, data):
        self.id = data["id"]
        self.username = data["username"]
        self.last_login = data["last_login"]
        self.date_created = data["date_created"]
        self.url = WEB_URL + "projects/matches/user?user_id={}".format(self.id)
        self.is_registered = True if self.id else False

    @classmethod
    def unregistered_user(cls):
        return cls(
            {
                "id": 0,
                "username": 0,
                "last_login": 0,
                "date_created": 0,
            }
        )

    def stats_embed(self, data):
        embed = quickembed.general(desc="Pickem Stats", user=self)
        embed.add_field(name="Picks", value=data["picks_made"], inline=True)
        combined_picks_closed = data["picks_correct"] + data["picks_wrong"]
        embed.add_field(
            name="Ratio",
            value="{:.2f}".format(
                (data["picks_correct"] / (1 if combined_picks_closed == 0 else combined_picks_closed)) * 100
            ),
            inline=True,
        )
        embed.add_field(name="Pickems Created", value=data["prompts_created"], inline=False)
        if self.date_created:
            embed.set_footer(
                text="Member since: {}".format(self.date_created.split()[0])
            )
        return embed

    def stats_full_embed(self, data):
        embed = quickembed.general(desc="Pickem Stats", user=self)
        embed.add_field(name="Picks", value=data["picks_made"], inline=True)
        embed.add_field(name="Correct", value=data["picks_correct"], inline=True)
        embed.add_field(name="Wrong", value=data["picks_wrong"], inline=True)
        combined_picks_closed = data["picks_correct"] + data["picks_wrong"]
        embed.add_field(
            name="Ratio",
            value="{:.2f}%".format(
                (data["picks_correct"] / (1 if combined_picks_closed == 0 else combined_picks_closed)) * 100
            ),
            inline=True,
        )
        embed.add_field(name=" ", value="__Pickems Created by Others__", inline=False)
        embed.add_field(name="Picks Correct", value=data["picks_correct_others"], inline=True)
        embed.add_field(
            name="Ratio",
            value="{:.2f}%".format(
                (data["picks_correct_others"] / (1 if combined_picks_closed == 0 else combined_picks_closed)) * 100
            ),
            inline=True,
        )
        embed.add_field(name=" ", value=" ", inline=False)
        embed.add_field(name="Pickems Created", value=data["prompts_created"], inline=True)
        embed.add_field(name="Pickems Created (today)", value=data["prompts_created_today"], inline=True)
        if self.date_created:
            embed.set_footer(
                text="Member since: {}".format(self.date_created.split()[0])
            )
        return embed


class Prompt:
    def __init__(self, data):
        if 'prompt' in data:
            self.id = data['prompt']["id"]
            self.user_id = data['prompt']["user_id"]
            self.subject = data['prompt']["subject"]
            self.open = data['prompt']["open"]
            self.choice_result = data['prompt']["choice_result"]
            self.picks = data['prompt']["picks"]
            self.expires_at = data['prompt']["expires_at"]
            self.created_at = data['prompt']["created_at"]
            self.updated_at = data['prompt']["updated_at"]
        else:
            self.id = data["id"]
            self.user_id = data["user_id"]
            self.subject = data["subject"]
            self.open = data["open"]
            self.choice_result = data["choice_result"]
            self.picks = data["picks"]
            self.expires_at = data["expires_at"]
            self.created_at = data["created_at"]
            self.updated_at = data["updated_at"]
        self.choices = []
        if 'choices' in data:
            for choice_data in data["choices"]:
                self.choices.append(Choice(choice_data))
        self.page_prompt_embed = None
        self.user = None

    def info_embed(self, caller: User = None, custom_title: str = None, red=False):
        if red:
            embed = quickembed.error(
                desc="**{}**".format(self.subject),
                footer="created by {}".format(self.user.username),
                user=caller,
            )
        else:
            embed = quickembed.question(
                desc="**{}**".format(self.subject),
                footer="created by {}".format(self.user.username),
                user=caller,
            )
        if custom_title:
            embed.set_author(
                name="{}".format(custom_title),
                icon_url=caller.discord.display_avatar,
                url=caller.url,
            )
        for i, choice in enumerate(self.choices):
            embed.add_field(name="{} {}".format(Choice.choice_emojis[i], choice.subject), value="", inline=False)
        return embed


class Choice:
    choice_emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]  # order matters

    def __init__(self, data):
        self.id = data["id"]
        self.prompt_id = data["prompt_id"]
        self.subject = data["subject"]
        self.picks = data["picks"]
        self.created_at = data["created_at"]
        self.updated_at = data["updated_at"]

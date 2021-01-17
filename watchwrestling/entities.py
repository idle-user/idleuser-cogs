from datetime import datetime
import json

from .api import WEB_URL
from .utils import quickembed

import discord


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
        embed = quickembed.general(desc="Season {}".format(data["season"]), user=self)
        embed.add_field(name="Wins", value=data["wins"], inline=True)
        embed.add_field(name="Losses", value=data["losses"], inline=True)
        embed.add_field(
            name="Ratio",
            value="{:.3f}".format(
                data["wins"] / (1 if data["losses"] == 0 else data["losses"])
            ),
            inline=True,
        )
        embed.add_field(
            name="Total Points",
            value="{:,}".format(int(data["total_points"])),
            inline=True,
        )
        embed.add_field(
            name="Available Points",
            value="{:,}".format(int(data["available_points"])),
            inline=True,
        )
        if self.date_created:
            embed.set_footer(
                text="Member since: {}".format(self.date_created.split()[0])
            )
        return embed


class Superstar:
    def __init__(self, data):
        self.id = data["id"]
        self.name = data["name"]
        self.brand_id = data["brand_id"]
        self.height = data["height"]
        self.weight = data["weight"]
        self.hometown = data["hometown"]
        self.dob = data["dob"]
        self.signature_move = data["signature_move"]
        self.page_url = data["page_url"]
        self.image_url = data["image_url"]
        self.bio = data["bio"]
        self.twitter_id = data["twitter_id"]
        self.twitter_username = data["twitter_username"]
        self.last_updated = data["last_updated"]

    def calculate_age(self):
        today = datetime.now().date()
        dob = datetime.strptime(self.dob, "%Y-%m-%d").date()
        return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

    def info_embed(self):
        embed = discord.Embed(color=quickembed.color["blue"])
        embed.set_author(
            name=self.name,
            url=WEB_URL + "superstar?superstar_id={}".format(self.id),
        )
        if self.dob:
            embed.add_field(
                name="Age",
                value="{} ({})\n".format(self.calculate_age(), self.dob),
                inline=True,
            )
        if self.height:
            embed.add_field(name="Height", value=self.height, inline=True)
        if self.weight:
            embed.add_field(name="Weight", value=self.weight, inline=True)
        if self.hometown:
            embed.add_field(name="Hometown", value=self.hometown, inline=True)
        if self.signature_move:
            embed.add_field(
                name="Signature Moves(s)",
                value="\n".join(self.signature_move.split(";")),
                inline=True,
            )
        if self.bio:
            bio = "{} ...".format(self.bio[:900]) if len(self.bio) > 900 else self.bio
            embed.add_field(name="\u200b", value="```{}```".format(bio), inline=False)
        if self.image_url:
            embed.set_image(url=self.image_url)
        if self.last_updated:
            embed.set_footer(text="Last updated: {}".format(self.last_updated))
        return embed


class Match:
    def __init__(self, data):
        self.id = data["id"]
        self.event_id = data["event_id"]
        self.title_id = data["title_id"]
        self.match_type_id = data["match_type_id"]
        self.match_note = data["match_note"]
        self.team_won = data["team_won"]
        self.winner_note = data["winner_note"]
        self.bet_open = data["bet_open"]
        self.info_last_updated_by_id = data["info_last_updated_by_id"]
        self.info_last_updated = data["info_last_updated"]
        self.completed = data["completed"]
        self.pot_valid = data["pot_valid"]
        self.contestants = data["contestants"]
        self.contestants_won = data["contestants_won"]
        self.contestants_lost = data["contestants_lost"]
        self.bet_multiplier = data["bet_multiplier"]
        self.base_pot = data["base_pot"]
        self.total_pot = data["total_pot"]
        self.base_winner_pot = data["base_winner_pot"]
        self.base_loser_pot = data["base_loser_pot"]
        self.user_bet_cnt = data["user_bet_cnt"]
        self.user_bet_winner_cnt = data["user_bet_winner_cnt"]
        self.user_bet_loser_cnt = data["user_bet_loser_cnt"]
        self.user_rating_avg = data["user_rating_avg"]
        self.user_rating_cnt = data["user_rating_cnt"]
        self.calc_last_updated = data["calc_last_updated"]
        self.event = data["event"]
        self.date = data["date"]
        self.title = data["title"]
        self.match_type = data["match_type"]
        self.last_updated_by_username = data["last_updated_by_username"]
        self.star_rating = "".join(
            ["★" if self.user_rating_avg >= i else "☆" for i in range(1, 6)]
        )
        self.url = WEB_URL + "projects/matches/matches?match_id={}".format(self.id)
        self.team_list = data["team_list"]

    def team_id_by_member_name(self, name):
        name = name.lower()
        for team in self.team_list:
            if name in team["members"].lower():
                return team["team"]
        return False

    def team_by_id(self, team_id):
        for team in self.team_list:
            if team_id == team["team"]:
                return team
        return False

    def info_text_short(self):
        if self.title:
            return "{} | {} | {}".format(
                self.match_type,
                self.title,
                " vs ".join([team["members"] for team in self.team_list]),
            )
        else:
            return "{} | {}".format(
                self.match_type,
                " vs ".join([team["members"] for team in self.team_list]),
            )

    def info_text(self):
        if self.completed:
            rating = "{0.star_rating} ({0.user_rating_avg})".format(self)
            pot = "{0.base_pot:,} ({0.bet_multiplier}x) -> {0.total_pot:,}".format(self)
        else:
            rating = ""
            pot = "{0.base_pot:,} (?x) -> TBD".format(self)
        if self.title and self.match_note:
            match_detail = "({0.title} - {0.match_note})".format(self)
        elif self.title:
            match_detail = "({0.title})".format(self)
        elif self.match_note:
            match_detail = "({0.match_note})".format(self)
        else:
            match_detail = ""
        teams = "\n\t".join(
            "Team {}. ({}x) {}".format(
                team["team"],
                team["bet_multiplier"],
                team["members"],
            )
            for team in self.team_list
        )
        team_won = self.team_won if self.team_won else "TBD"
        winner_note = "({0.winner_note})".format(self) if self.winner_note else ""
        betting = "Open" if self.bet_open else "Closed"
        return (
            "[Match {0.id}] {1}\n"
            "Event: {0.event} {0.date}\n"
            "Bets: {2}\nPot: {3}\n"
            "{0.match_type} {4}\n"
            "\t{5}\nTeam Won: {6} {7}".format(
                self, rating, betting, pot, match_detail, teams, team_won, winner_note
            )
        )

    def info_embed(self):
        if self.completed:
            header = "[Match {0.id}] {0.star_rating} ({0.user_rating_avg:.3f})".format(
                self
            )
        else:
            header = "[Match {0.id}]".format(self)
        bet_status = "Open" if self.bet_open else "Closed"
        teams = "\n".join(
            "{}. ({}x) {}".format(
                team["team"],
                team["bet_multiplier"],
                team["members"],
            )
            for team in self.team_list
        )

        color = quickembed.color["blue"]
        embed = discord.Embed(color=color)
        embed.set_author(name="{}".format(header), url="{}".format(self.url))
        embed.description = "{0.date} | {0.event}".format(self)
        embed.add_field(name="Bets", value="{}".format(bet_status), inline=True)
        embed.add_field(
            name="Base Pot", value="{:,}".format(self.base_pot), inline=True
        )
        if self.completed:
            embed.add_field(
                name="Multiplier", value="{}x".format(self.bet_multiplier), inline=True
            )
            embed.add_field(
                name="Total Pot", value="{:,}".format(self.total_pot), inline=True
            )
        embed.add_field(
            name="Match Type", value="{}".format(self.match_type), inline=False
        )
        if self.title:
            embed.add_field(name="Title", value="{}".format(self.title), inline=False)
        embed.add_field(name="Teams", value="{}".format(teams), inline=True)
        if self.team_won:
            embed.add_field(
                name="Team Won", value="{}".format(self.team_won), inline=True
            )
        if self.calc_last_updated:
            embed.set_footer(text="Last updated: {}".format(self.calc_last_updated))
        return embed

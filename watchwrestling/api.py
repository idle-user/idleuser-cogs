import aiohttp
import logging
import random
import string

import discord

from .errors import IdleUserAPIError, ResourceNotFoundError, ValidationError


API_URL = "https://api.idleuser.com/"
WEB_URL = "https://idleuser.com/projects/matches/"

log = logging.getLogger("red.idleuser-cogs.WatchWrestling")


class IdleUserAPI:
    def __init__(self, bot):
        self.bot = bot

    async def get_response(self, route, params={}):
        auth = await self.stored_auth_token()
        params.update(auth)
        return await self.get_idleusercom_response(route, params=params)

    async def post_response(self, route, payload):
        auth = await self.stored_auth_token()
        return await self.post_idleusercom_response(route, params=auth, payload=payload)

    async def get_idleusercom_response(self, route, params):
        async with aiohttp.ClientSession() as session:
            async with session.get(API_URL + route, params=params) as resp:
                return await self.handle_response(resp)

    async def post_idleusercom_response(self, route, params, payload):
        async with aiohttp.ClientSession() as session:
            async with session.post(
                API_URL + route, params=params, json=payload
            ) as resp:
                return await self.handle_response(resp)

    async def handle_response(self, response):
        try:
            data = await response.json()
        except UnicodeDecodeError:
            data = await response.json(encoding="latin-1")
        except Exception:
            raise Exception("Error decoding response.")
        if response.status == 200:
            return data["data"]
        else:
            error_msg = data["error"]["description"]
            if response.status == 404:
                raise ResourceNotFoundError(error_msg)
            elif response.status == 422:
                raise ValidationError(error_msg)
            else:
                log.error(data)
                raise IdleUserAPIError(error_msg)

    async def stored_auth_token(self):
        auth = await self.bot.get_shared_api_tokens("idleuser")
        return auth

    async def get_user_by_id(self, user_id):
        return await self.get_response("users/{}".format(user_id))

    async def get_user_by_username(self, username):
        return await self.get_response("users/username/{}".format(username))

    async def get_user_by_discord_id(self, discord_id):
        return await self.get_response("users/discord/{}".format(discord_id))

    async def get_user_stats_by_season_id(self, user_id, season_id):
        return await self.get_response(
            "watchwrestling/stats/user/{}/season/{}".format(user_id, season_id)
        )

    async def get_bet_by_id(self, match_id, user_id):
        return await self.get_response(
            "watchwrestling/bets/match/{}/user/{}".format(match_id, user_id)
        )

    async def get_leaderboard_by_season_id(self, season_id):
        return await self.get_response(
            "watchwrestling/stats/leaderboard/season/{}".format(season_id)
        )

    async def get_match_by_id(self, match_id):
        return await self.get_response(
            "watchwrestling/matches/{}/detail".format(match_id)
        )

    async def get_openbet_matches(self):
        return await self.get_response("watchwrestling/matches/betopen/detail")

    async def get_current_match(self):
        return await self.get_response("watchwrestling/matches/current/detail")

    async def get_recent_match(self):
        return await self.get_response("watchwrestling/matches/recent/detail")

    async def get_superstar_search(self, keyword):
        return await self.get_response(
            "watchwrestling/superstars/search/{}".format(keyword)
        )

    async def get_superstar_by_id(self, superstar_id):
        return await self.get_response(
            "watchwrestling/superstars/{}".format(superstar_id)
        )

    async def get_future_events(self):
        return await self.get_response("watchwrestling/events/future")

    async def post_match_rating(self, user_id, match_id, rating):
        payload = {
            "user_id": user_id,
            "match_id": match_id,
            "rating": rating,
        }
        return await self.post_response("watchwrestling/rate", payload)

    async def post_match_bet(self, user_id, match_id, team_id, points):
        payload = {
            "user_id": user_id,
            "match_id": match_id,
            "team": team_id,
            "points": points,
        }
        return await self.post_response("watchwrestling/bet", payload)

    async def post_user_login_token(self, user_id):
        payload = {
            "user_id": user_id,
        }
        return await self.post_response("users/login/token", payload)

    async def post_user_register(self, username, discord_id=None, chatango_id=None):
        payload = {
            "username": username,
            "secret": "".join(
                random.choices(string.ascii_letters + string.digits, k=15)
            ),
            "discord_id": discord_id,
            "chatango_id": chatango_id,
        }
        return await self.post_response("users/register", payload)

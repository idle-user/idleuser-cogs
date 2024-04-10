import logging

import aiohttp

from .errors import (
    IdleUserAPIError,
    BadRequest,
    Unauthenticated,
    InsufficientPrivileges,
    ResourceNotFound,
    MethodNotAllowed,
    ConflictError,
    ValidationError,
)

API_URL = "https://api.idleuser.com/"
WEB_URL = "https://idleuser.com/"

log = logging.getLogger("red.idleuser-cogs.pickem")


class IdleUserAPI:
    def __init__(self, bot):
        self.bot = bot

    async def stored_auth_token(self):
        auth = await self.bot.get_shared_api_tokens("idleuser")
        return auth

    async def get_headers(self):
        auth = await self.stored_auth_token()
        auth_token = auth.get("auth_token", "")
        headers = {"Authorization": "Bearer {}".format(auth_token)}
        return headers

    async def get_idleusercom_response(self, route, params={}):
        headers = await self.get_headers()
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(API_URL + route, params=params) as resp:
                return await self.handle_response(resp)

    async def post_idleusercom_response(self, route, payload={}):
        headers = await self.get_headers()
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.post(API_URL + route, json=payload) as resp:
                return await self.handle_response(resp)

    async def patch_idleusercom_response(self, route, payload={}):
        headers = await self.get_headers()
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.patch(API_URL + route, json=payload) as resp:
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
            if response.status == 400:
                raise BadRequest(error_msg)
            elif response.status == 401:
                raise Unauthenticated(error_msg)
            elif response.status == 403:
                raise InsufficientPrivileges(error_msg)
            elif response.status == 404:
                raise ResourceNotFound(error_msg)
            elif response.status == 405:
                raise MethodNotAllowed(error_msg)
            elif response.status == 409:
                raise ConflictError(error_msg)
            elif response.status == 422:
                raise ValidationError(error_msg)
            else:
                log.error(data)
                raise IdleUserAPIError("{} - {}".format(response.status, error_msg))

    async def get_user_by_id(self, user_id):
        return await self.get_idleusercom_response(route="users/{}".format(user_id))

    async def get_user_by_username(self, username):
        return await self.get_idleusercom_response(
            route="users/username/{}".format(username)
        )

    async def get_user_by_discord_id(self, discord_id):
        return await self.get_idleusercom_response(
            route="users/discord/{}".format(discord_id)
        )

    async def get_pickem_prompts(self, group_id, prompt_open=0):
        return await self.get_idleusercom_response(
            route="pickem/prompts?group_id={}&open={}".format(group_id, prompt_open)
        )

    async def get_pickem_prompt_by_id(self, prompt_id):
        return await self.get_idleusercom_response(
            route="pickem/prompts/{}".format(prompt_id)
        )

    async def get_pickem_picks(self, prompt_id=0, choice_id=0, user_id=0):
        return await self.get_idleusercom_response(
            route="pickem/picks?promptId={}&choiceId={}&userId={}".format(prompt_id, choice_id, user_id)
        )

    async def get_pickem_stats(self):
        return await self.get_idleusercom_response(
            route="pickem/stats"
        )

    async def get_pickem_stats_by_id(self, user_id):
        return await self.get_idleusercom_response(
            route="pickem/stats/{}".format(user_id)
        )

    async def post_pickem_prompt(self, user_id, group_id, subject, choices):
        payload = {
            "user_id": user_id,
            "group_id": group_id,
            "subject": subject,
            "choices": choices,
        }
        return await self.post_idleusercom_response(
            route="pickem/prompt", payload=payload
        )

    async def patch_pickem_prompt(self, user_id, prompt_id, prompt_open, choice_result):
        payload = {
            "user_id": user_id,
            "prompt_id": prompt_id,
            "open": prompt_open,
            "choice_result": choice_result,
        }
        return await self.patch_idleusercom_response(
            route="pickem/prompt", payload=payload
        )

    async def post_pickem_pick(self, user_id, prompt_id, choice_id):
        payload = {
            "user_id": user_id,
            "prompt_id": prompt_id,
            "choice_id": choice_id,
        }
        return await self.post_idleusercom_response(
            route="pickem/pick", payload=payload
        )

    async def patch_pickem_pick(self, user_id, prompt_id, choice_id):
        payload = {
            "user_id": user_id,
            "prompt_id": prompt_id,
            "choice_id": choice_id,
        }
        return await self.patch_idleusercom_response(
            route="pickem/pick", payload=payload
        )

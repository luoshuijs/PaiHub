import secrets
from typing import TYPE_CHECKING, Optional

from async_lru import alru_cache

from birdnet.client.base import BaseClient
from birdnet.client.web.authorization import AuthorizationToken
from birdnet.client.web.error import error_message_by_reason
from birdnet.client.web.features import DEFAULT_FEATURES
from birdnet.client.web.headers import HeadersKeyName, DEFAULT_HEADERS
from birdnet.client.web.variables import DEFAULT_VARIABLES
from birdnet.errors import BadRequest, NetworkError
from birdnet.utils.types import JSONDict

try:
    import ujson as jsonlib
except ImportError:
    import json as jsonlib

if TYPE_CHECKING:
    from httpx._types import TimeoutTypes


class WebClient(BaseClient):
    def __init__(self, timeout: "Optional[TimeoutTypes]" = None):
        csrf_token = secrets.token_hex(16)
        cookies = {"ct0": csrf_token}
        headers = DEFAULT_HEADERS.copy()
        headers[HeadersKeyName.CSRF_TOKEN] = csrf_token
        super().__init__(cookies=cookies, headers=headers, timeout=timeout)

    async def tweet_result_by_rest_id(self, tweet_id: str):
        api = "https://twitter.com/i/api/graphql/0hWvDhmW8YQ-S_ib3azIrw/TweetResultByRestId"
        variables = DEFAULT_VARIABLES.copy()
        variables.update({"tweetId": tweet_id})
        params = {
            "variables": jsonlib.dumps(variables),
            "features": jsonlib.dumps(DEFAULT_FEATURES),
        }
        self.client.headers.update({HeadersKeyName.AUTHORIZATION: AuthorizationToken.LOGGED_IN})
        await self._require_auth()
        response = await self.request_json("GET", api, params=params)
        result: "JSONDict" = response["data"]["tweetResult"]["result"]
        if result.get("__typename") == "TweetUnavailable":
            reason = error_message_by_reason(result.get("reason"))
            raise BadRequest(message=f"Tweet is unavailable, reason: {reason}.")
        return result

    async def _require_auth(self):
        if not self.client.headers.get(HeadersKeyName.AUTH_TYPE):
            await self._get_guest_token()

    @alru_cache(maxsize=32, ttl=3600)
    async def _get_guest_token(self):
        self.client.headers[HeadersKeyName.GUEST_TOKEN] = ""
        self.client.cookies["gt"] = ""
        api = "https://api.twitter.com/1.1/guest/activate.json"
        response = await self.request_json("POST", api)
        token = response.get("guest_token")
        if not token:
            raise NetworkError(f"Failed to get guest token: {response}")
        self.client.headers[HeadersKeyName.GUEST_TOKEN] = token
        self.client.cookies["gt"] = token
        return token

import re
from datetime import datetime
from typing import List, Dict, Optional, Union

import toml

from birdnet.client.web.client import WebClient
from birdnet.errors import BadRequest as BirdNetBadRequest, TimedOut as BirdNetTimedOut
from paihub.base import BaseApi
from paihub.error import BadRequest, ArtWorkNotFoundError
from paihub.log import logger
from paihub.sites.twitter.cache import WebClientCache
from paihub.sites.twitter.entities import TwitterArtWork, TwitterAuthor


class WebClientApi(BaseApi):
    def __init__(self, web_cache: WebClientCache):
        self.web_cache = web_cache
        self.config: dict = {}
        with open("config/twitter.toml", "r", encoding="utf-8") as f:
            self.config = toml.load(f)
        login = self.config.get("login")
        auth_token = login.get("auth_token")
        self.web = WebClient(auth_token=auth_token)
        self.login_status = False

    async def initialize(self) -> None:
        if self.web.auth_token is not None:
            try:
                account_settings = await self.web.get_account_settings()
                screen_name = account_settings.get("screen_name")
                logger.info("Twitter Web API Login with Auth Token Success, Login User [%s]", screen_name)
                self.login_status = True
            except BirdNetBadRequest as exc:
                logger.error("Twitter Web Login Error: %s", exc.message)
            except BirdNetTimedOut:
                logger.error("Twitter Web Login Timed Out")
        else:
            logger.warning("Twitter Web API Auth Token Not Found")

    async def shutdown(self) -> None:
        await self.web.shutdown()

    async def get_artwork(self, artwork_id: int) -> TwitterArtWork:
        if self.login_status:
            return await self.get_tweet_detail(artwork_id)
        return await self.get_tweet_result_by_rest_id(artwork_id)

    async def get_artwork_images(self, artwork_id: int) -> List[bytes]:
        if self.login_status:
            return await self.get_tweet_detail_images(artwork_id)
        return await self.get_tweet_images_result_by_rest_id(artwork_id)

    async def get_tweet_detail(self, tweet_id: int) -> TwitterArtWork:
        response = await self.web_cache.get_tweet_detail(tweet_id)
        if response is None:
            try:
                response = await self.web.tweet_detail(str(tweet_id))
            except BirdNetBadRequest as exc:
                if "No status found" in exc.message:
                    raise ArtWorkNotFoundError from exc
                raise BadRequest(exc.message) from exc
            await self.web_cache.set_tweet_detail(tweet_id, response)

        tweet = self.get_tweet_from_tweet_detail(response, tweet_id)

        return self.get_artwork_from_tweet(tweet, tweet_id)

    async def get_tweet_detail_images(self, tweet_id: int) -> List[bytes]:
        response = await self.web_cache.get_tweet_detail(tweet_id)
        if response is None:
            try:
                response = await self.web.tweet_detail(str(tweet_id))
            except BirdNetBadRequest as exc:
                if "No status found" in exc.message:
                    raise ArtWorkNotFoundError from exc
                raise BadRequest(exc.message) from exc
            await self.web_cache.set_tweet_detail(tweet_id, response)

        tweet = self.get_tweet_from_tweet_detail(response, tweet_id)
        result: List[bytes] = []
        medias: "List[Dict]" = tweet["legacy"]["extended_entities"]["media"]
        for media in medias:
            result.append(await self.web.download(media["media_url_https"]))
        return result

    async def get_tweet_result_by_rest_id(self, tweet_id: int) -> TwitterArtWork:
        data = await self.web_cache.get_tweet_result_by_rest_id(tweet_id)
        if data is None:
            try:
                data = await self.web.tweet_result_by_rest_id(str(tweet_id))
            except BirdNetBadRequest as exc:
                if "No status found" in exc.message:
                    raise ArtWorkNotFoundError from exc
                raise BadRequest(exc.message) from exc
            await self.web_cache.set_tweet_result_by_rest_id(tweet_id, data)

        return self.get_artwork_from_tweet(data, tweet_id)

    async def get_tweet_images_result_by_rest_id(self, tweet_id: int) -> List[bytes]:
        data = await self.web_cache.get_tweet_result_by_rest_id(tweet_id)
        if data is None:
            try:
                data = await self.web.tweet_result_by_rest_id(str(tweet_id))
            except BirdNetBadRequest as exc:
                if "No status found" in exc.message:
                    raise ArtWorkNotFoundError from exc
                raise BadRequest from exc
            await self.web_cache.set_tweet_result_by_rest_id(tweet_id, data)
        result: List[bytes] = []
        medias: "List[Dict]" = data["legacy"]["extended_entities"]["media"]
        for media in medias:
            result.append(await self.web.download(media["media_url_https"]))
        return result

    @staticmethod
    def get_artwork_from_tweet(tweet: Dict, tweet_id: int):
        author = TwitterAuthor(
            auther_id=int(tweet["legacy"]["user_id_str"]),
            name=tweet["core"]["user_results"]["result"]["legacy"]["name"],
            username=tweet["core"]["user_results"]["result"]["legacy"]["screen_name"],
        )
        full_text = tweet["legacy"]["full_text"]
        title = re.sub(r"https?://t\.co/\S+|#\S+|\n", "", full_text)
        tags = re.findall(r"#(\S+)", full_text)
        time_str = tweet["legacy"]["created_at"]
        create_time = datetime.strptime(time_str, "%a %b %d %H:%M:%S %z %Y")
        return TwitterArtWork(artwork_id=tweet_id, author=author, title=title, create_time=create_time, tags=tags)

    @staticmethod
    def get_tweet_from_tweet_detail(data: Dict, tweet_id: Union[str, int]):
        instructions = data["threaded_conversation_with_injections_v2"]["instructions"]
        entries: "List[Dict]" = []
        for instruction in instructions:
            if instruction.get("type") == "TimelineAddEntries":
                entries = instruction["entries"]
                break
        tweet: "Optional[Dict]" = None
        for entry in entries:
            if entry["entryId"] == f"tweet-{tweet_id}":
                tweet_results = entry["content"]["itemContent"]["tweet_results"]
                tweet = tweet_results.get("result")
                if tweet is None:
                    raise BadRequest(
                        "Tweet result is empty, maybe it's a sensitive tweet "
                        "or the author limited visibility, "
                        "you may try setting an AUTH_TOKEN."
                    )
                break
        if tweet is None:
            raise BadRequest("Failed to find tweet detail in response")

        # Check if tweet is available
        typename = tweet.get("__typename")
        if typename == "TweetTombstone":
            tombstone = tweet["tombstone"]["text"]
            text = tombstone["text"]
            if text.startswith("Age-restricted"):
                raise BadRequest("Age-restricted adult content. Please set Twitter auth token.")
            raise BadRequest(text)

        if typename == "TweetWithVisibilityResults" or tweet.get("tweet"):
            tweet = tweet["tweet"]

        return tweet

from contextlib import AbstractAsyncContextManager
from types import TracebackType
from typing import TYPE_CHECKING, Any, TypeVar

from httpx import AsyncClient, Headers, HTTPError, Timeout, TimeoutException

from pixnet.utils.types import JSONDict

if TYPE_CHECKING:
    from httpx import Response
    from httpx._types import CookieTypes, HeaderTypes, QueryParamTypes, RequestData, TimeoutTypes, URLTypes

from pixnet.errors import BadRequest, NetworkError, NotExited, TimedOut, TooManyRequest

try:
    import orjson as jsonlib

except ImportError:
    import json as jsonlib


__all__ = ("BaseClient",)

RT = TypeVar("RT", bound="BaseClient")


class BaseClient(AbstractAsyncContextManager["BaseClient"]):
    def __init__(
        self,
        user_id: int | None = None,
        cookies: "CookieTypes | None" = None,
        headers: "HeaderTypes | None" = None,
        timeout: "TimeoutTypes | None" = None,
        lang: str | None = None,
    ) -> None:
        """Initialize the client with the given parameters."""
        if timeout is None:
            timeout = Timeout(
                connect=5.0,
                read=5.0,
                write=5.0,
                pool=1.0,
            )

        headers = Headers(headers)
        headers.setdefault("User-Agent", self.user_agent)
        headers.setdefault("Referer", "https://www.pixiv.net")
        self.client = AsyncClient(cookies=cookies, timeout=timeout, headers=headers)
        self.user_id = user_id
        self.lang = lang

    async def __aenter__(self: RT) -> RT:
        """Enter the async context manager and initialize the client."""
        try:
            await self.initialize()
        except Exception:
            await self.shutdown()
            raise
        else:
            return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit the async context manager and shutdown the client."""
        await self.shutdown()

    async def shutdown(self):
        """Shutdown the client."""
        if self.client.is_closed:
            return

        await self.client.aclose()

    async def initialize(self):
        """Initialize the client."""

    @property
    def user_agent(self) -> str:
        return (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/90.0.4430.72 Safari/537.36"
        )

    async def request(
        self,
        method: str,
        url: "URLTypes",
        data: "RequestData | None" = None,
        json: Any | None = None,
        params: "QueryParamTypes | None" = None,
        headers: "HeaderTypes | None" = None,
    ) -> "Response":
        try:
            return await self.client.request(
                method,
                url,
                data=data,
                json=json,
                params=params,
                headers=headers,
            )
        except TimeoutException as exc:
            raise TimedOut from exc
        except HTTPError as exc:
            raise NetworkError from exc

    async def request_api(
        self,
        method: str,
        url: "URLTypes",
        json: Any | None = None,
        params: "QueryParamTypes | None" = None,
        headers: "HeaderTypes | None" = None,
    ) -> JSONDict:
        response = await self.request(
            method,
            url,
            json=json,
            params=params,
            headers=headers,
        )
        if not response.is_error:
            data = jsonlib.loads(response.content)
            error = data.get("error", False)
            if error:
                raise BadRequest(response=data)
            return data["body"]
        try:
            data = jsonlib.loads(response.content)
        except jsonlib.JSONDecodeError:
            data = None
        if response.status_code == 404:
            raise NotExited(response=data)
        if response.status_code == 500:
            raise TooManyRequest(response=data)
        raise BadRequest(status_code=response.status_code, response=data)

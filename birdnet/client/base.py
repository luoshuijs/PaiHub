from contextlib import AbstractAsyncContextManager
from datetime import datetime
from types import TracebackType
from typing import TYPE_CHECKING, Any, Self, TypeVar

from httpx import AsyncClient, Headers, HTTPError, Timeout, TimeoutException

from birdnet.client.web.headers import HeadersKeyName
from birdnet.utils.types import JSONDict

if TYPE_CHECKING:
    from httpx import Response
    from httpx._types import CookieTypes, HeaderTypes, QueryParamTypes, RequestData, TimeoutTypes, URLTypes

from birdnet.errors import BadRequest, NetworkError, TimedOut

__all__ = ("BaseClient",)

RT = TypeVar("RT", bound="BaseClient")


class BaseClient(AbstractAsyncContextManager["BaseClient"]):
    def __init__(
        self,
        cookies: "CookieTypes | None" = None,
        headers: "HeaderTypes | None" = None,
        timeout: "TimeoutTypes | None" = None,
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
        self.client = AsyncClient(cookies=cookies, timeout=timeout, headers=headers)

    async def __aenter__(self) -> Self:
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
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/121.0.0.0 Safari/537.36"
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

    async def request_json(
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
            return response.json()
        if "application/json" in response.headers.get("Content-Type", ""):
            return response.json()
        if response.status_code == 401:
            raise BadRequest(
                message="Tweet result is empty, maybe it's a sensitive tweet "
                "or the author limited visibility, you may try setting an AUTH_TOKEN."
            )
        if response.status_code == 429:
            headers = response.headers
            detail = ""
            if HeadersKeyName.RATE_LIMIT_LIMIT in headers and HeadersKeyName.RATE_LIMIT_RESET in headers:
                rate_limit = int(headers[HeadersKeyName.RATE_LIMIT_LIMIT])
                reset_time = int(headers[HeadersKeyName.RATE_LIMIT_RESET])
                reset_time = datetime.fromtimestamp(reset_time)
                detail = f"Rate limit: {rate_limit}, Reset time: {reset_time}"
            raise BadRequest(message="Hit API rate limit, please try again later. " + detail)
        raise BadRequest(status_code=response.status_code)

    async def request_api(
        self,
        method: str,
        url: "URLTypes",
        data: Any | None = None,
        params: "QueryParamTypes | None" = None,
        headers: "HeaderTypes | None" = None,
    ) -> JSONDict:
        result = await self.request_json(method, url, json=data, params=params, headers=headers)
        errors = result.get("errors")
        if errors:
            raise BadRequest(message="\n".join([error["message"] for error in errors]))
        return result["data"]

    async def download(self, url: "URLTypes", chunk_size: int | None = None) -> bytes:
        data = b""
        async with self.client.stream("GET", url) as response:
            async for chunk in response.aiter_bytes(chunk_size):
                data += chunk
        return data

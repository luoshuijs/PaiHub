from types import TracebackType
from typing import AsyncContextManager, Type, Optional, Any, TypeVar, TYPE_CHECKING

from httpx import AsyncClient, TimeoutException, HTTPError, Timeout, Headers

from pixnet.utils.types import JSONDict

if TYPE_CHECKING:
    from httpx import Response
    from httpx._types import RequestData, URLTypes, QueryParamTypes, HeaderTypes, CookieTypes, TimeoutTypes

from pixnet.errors import BadRequest, NotSupported, TimedOut, NetworkError

__all__ = ("BaseClient",)

RT = TypeVar("RT", bound="BaseClient")


class BaseClient(AsyncContextManager["BaseClient"]):
    def __init__(
        self,
        user_id: Optional[int] = None,
        cookies: "Optional[CookieTypes]" = None,
        headers: "Optional[HeaderTypes]" = None,
        timeout: "Optional[TimeoutTypes]" = None,
        lang: Optional[str] = None,
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
            return self
        except Exception as exc:
            await self.shutdown()
            raise exc

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
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
        data: "Optional[RequestData]" = None,
        json: Optional[Any] = None,
        params: "Optional[QueryParamTypes]" = None,
        headers: "Optional[HeaderTypes]" = None,
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
        url: URLTypes,
        json: Optional[Any] = None,
        params: Optional[QueryParamTypes] = None,
        headers: Optional[HeaderTypes] = None,
    ) -> JSONDict:
        response = await self.request(
            method,
            url,
            json=json,
            params=params,
            headers=headers,
        )
        if not response.is_error:
            data = response.json()
            ret_code = data.get("error", False)
            if ret_code:
                raise BadRequest(response.json())
            return data["body"]
        if response.status_code == 404:
            raise NotSupported
        raise BadRequest(status_code=response.status_code, message=response.text)

    async def request_json(
        self,
        url: URLTypes,
        method: Optional[str] = None,
        data: Optional[Any] = None,
        params: Optional[QueryParamTypes] = None,
        headers: Optional[HeaderTypes] = None,
    ) -> JSONDict:
        if method is None:
            method = "GET" if data else "POST"
        return await self.request_api(method=method, url=url, json=data, params=params, headers=headers)

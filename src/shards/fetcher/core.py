import asyncio
import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

import aiohttp

from .exceptions import FetchError
from .resource import Resource

logger = logging.getLogger(__name__)

DEFAULT_USER_AGENT = "Fetcher/1.0"

DEFAULT_HEADERS = {
    "User-Agent": DEFAULT_USER_AGENT,
    "Accept-Encoding": "gzip, deflate",
}


class HttpMethod(str, Enum):
    GET = "GET"
    POST = "POST"


class Fetcher:
    def __init__(
        self,
        *,
        concurrency: int = 1,
        timeout: float = 10.0,
        retries: int = 3,
    ) -> None:
        """
        :param concurrency: Maximum number of concurrent fetches.
        :param timeout: Timeout for each fetch in seconds.
        :param retries: Number of retries for failed fetches.
        :param user_agent: User-Agent string to use for requests.
        """
        self.semaphore = asyncio.Semaphore(concurrency)
        self.timeout = timeout
        self.retries = retries
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        """
        Async context manager entry. Ensures the session is created.
        """
        return self

    async def __aexit__(self, exc_type, exc, tb):
        """
        Async context manager exit. Ensures the session is closed.
        """
        await self.aclose()

    async def _ensure_session(self):
        """
        Ensure that the aiohttp ClientSession is created.
        If it already exists and is open, do nothing.
        """
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self.session = aiohttp.ClientSession(timeout=timeout)

    async def aclose(self):
        """
        Close the aiohttp ClientSession if it exists.
        """
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None

    async def fetch(
        self,
        url: str,
        method: HttpMethod = HttpMethod.GET,
        stream_to: Optional[str] = None,
        headers: Optional[dict] = None,
        data: Optional[dict | bytes | str] = None,
        json: Optional[dict] = None,
    ) -> Resource:
        """
        Fetch a URL, returning a Resource object. Supports optional streaming to a file.

        :param url: The URL to fetch.
        :param method: HTTP method to use (default is GET).
        :param stream_to: Optional file path to stream the content to.
        :param headers: Optional headers to include in the request.
        :param data: Optional data to send in the body of the request.
        :param json: Optional JSON data to send in the body of the request.
        :return: A Resource object representing the fetched content.
        """
        async with self.semaphore:
            await self._ensure_session()
            return await self._fetch_with_retries(
                url, method=method, stream_to=stream_to, headers=headers
            )

    def sync_fetch(
        self,
        url: str,
        method: HttpMethod = HttpMethod.GET,
        stream_to: Optional[str] = None,
        headers: Optional[dict] = None,
        data: Optional[dict | bytes | str] = None,
        json: Optional[dict] = None,
    ) -> Resource:
        """
        Synchronous wrapper around the asynchronous fetch method.

        :param url: The URL to fetch.
        :param method: HTTP method to use (default is "GET").
        :param stream_to: Optional file path to stream the content to.
        :param headers: Optional headers to include in the request.
        :param data: Optional data to send in the body of the request.
        :param json: Optional JSON data to send in the body of the request.
        :return: A Resource object representing the fetched content.
        """
        return asyncio.run(
            self.fetch(
                url,
                method=method,
                stream_to=stream_to,
                headers=headers,
                data=data,
                json=json,
            )
        )

    async def _fetch_with_retries(
        self,
        url: str,
        method: HttpMethod = HttpMethod.GET,
        stream_to: Optional[str] = None,
        headers: Optional[dict] = None,
    ) -> Resource:
        """
        Fetch a URL with retries on failure.

        :param url: The URL to fetch.
        :param method: HTTP method to use (default is "GET").
        :param stream_to: Optional file path to stream the content to.
        :param headers: Optional headers to include in the request.
        :return: A Resource object representing the fetched content.
        """
        delay_base = 1
        attempt = 0
        while True:
            attempt += 1
            try:
                return await self._fetch_once(
                    url, method=method, stream_to=stream_to, headers=headers
                )
            except ValueError as ve:
                logger.error(f"Non-retriable error for {url}, {str(ve)}")
                raise FetchError(url, str(ve))
            except Exception as e:
                logger.warning(
                    f"Retrying {url}, attempt {attempt}/{self.retries} due to error: {str(e)}"
                )
                if attempt == self.retries:
                    logger.error(f"Failed to fetch {url} after {self.retries} attempts")
                    raise FetchError(url, str(e))
                await asyncio.sleep(delay_base * (2**attempt))

    async def _fetch_once(
        self,
        url: str,
        method: HttpMethod = HttpMethod.GET,
        stream_to: Optional[str] = None,
        headers: Optional[dict] = None,
    ) -> Resource:
        """
        Fetch a URL once, returning a Resource object.

        :param url: The URL to fetch.
        :param method: HTTP method to use (default is "GET").
        :param stream_to: Optional file path to stream the content to.
        :param headers: Optional headers to include in the request.
        :return: A Resource object representing the fetched content.
        """
        logger.info(f"Fetching {url} {'(streaming)' if stream_to else '(in-memory)'}")

        headers = headers or DEFAULT_HEADERS.copy()

        if method == HttpMethod.GET:
            resp = await self.session.get(url, headers=headers)
        elif method == HttpMethod.POST:
            resp = await self.session.post(url, headers=headers)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")

        if resp.url != url:
            logger.info(f"Redirected {url} to {resp.url}")

        return await Resource.from_response(
            url=url,
            resp=resp,
            fetched_at=datetime.now(timezone.utc).isoformat(),
            stream_to=stream_to,
        )

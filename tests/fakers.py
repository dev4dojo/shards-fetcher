from unittest.mock import AsyncMock

import aiohttp


class FakeResponse:
    def __init__(
        self,
        url: str = "http://example.com",
        status: int = 200,
        body: bytes = b"mock content",
        headers: dict = None,
        redirected_url: str = None,
    ):
        self._url = aiohttp.client.URL(url)
        self._redirected_url = aiohttp.client.URL(redirected_url or url)
        self.status = status
        self._body = body
        self.headers = headers or {"Content-Type": "text/plain"}
        self.reason = "OK"

    async def read(self):
        return self._body

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    @property
    def url(self):
        return self._redirected_url

    @property
    def content(self):
        mock = AsyncMock()
        mock.read.return_value = self._body
        return mock

    def get_encoding(self):
        content_type = self.headers.get("Content-Type", "")
        if "charset=" in content_type:
            return content_type.split("charset=")[-1]
        return None


class FakeSession:
    """
    Mimics aiohttp.ClientSession.
    Can be patched into code with monkeypatch.
    """

    def __init__(self, response: FakeResponse = None):
        self._response = response or FakeResponse()
        self.closed = False

        # You can patch both .get() and .request()
        self.get_calls = []
        self.request_calls = []

    async def get(self, url, **kwargs):
        self.get_calls.append((url, kwargs))
        return self._response

    async def post(self, url, **kwargs):
        self.get_calls.append((url, kwargs))
        return self._response

    async def request(self, method, url, **kwargs):
        self.request_calls.append((method, url, kwargs))
        return self._response

    async def close(self):
        self.closed = True

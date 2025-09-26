from datetime import datetime, timezone

import aiohttp
import pytest

from shards.fetcher.core import Fetcher, FetchError, HttpMethod
from shards.fetcher.resource import Resource

from .fakers import FakeResponse, FakeSession

DEFAULT_TEST_URL = "http://example.com"
DEFAULT_TEST_CONTENT = b"<html><body>Hello, World!</body></html>"


@pytest.fixture
def fake_session():
    response = FakeResponse(
        url=DEFAULT_TEST_URL,
        status=200,
        body=DEFAULT_TEST_CONTENT,
        headers={"Content-Type": "text/html; charset=utf-8"},
    )
    return FakeSession(response=response)


@pytest.mark.asyncio
async def test_fetcher_get(monkeypatch, fake_session):
    """
    Test fetching a simple HTML page successfully. Method: GET (default)
    """
    monkeypatch.setattr("aiohttp.ClientSession", lambda *args, **kwargs: fake_session)

    fetcher = Fetcher()
    try:
        resource = await fetcher.fetch(DEFAULT_TEST_URL)
        assert isinstance(resource, Resource)
        assert resource.url == DEFAULT_TEST_URL
        assert resource.metadata["status_code"] == 200
        assert resource.metadata["mime"] == "text/html"
        assert resource.metadata["encoding"] == "utf-8"
        assert b"Hello" in resource.content
        assert isinstance(resource.hash, str)
    finally:
        await fetcher.aclose()
    # assert False


def test_fetcher_get_sync(monkeypatch, fake_session):
    """
    Test fetching a simple HTML page successfully. Method: GET (default), sync_fetch
    """
    monkeypatch.setattr("aiohttp.ClientSession", lambda *args, **kwargs: fake_session)
    fetcher = Fetcher()
    resource = fetcher.sync_fetch(DEFAULT_TEST_URL)
    assert isinstance(resource, Resource)
    assert resource.url == DEFAULT_TEST_URL
    assert resource.metadata["status_code"] == 200
    assert resource.metadata["mime"] == "text/html"
    assert resource.metadata["encoding"] == "utf-8"
    assert b"Hello" in resource.content
    assert isinstance(resource.hash, str)


@pytest.mark.asyncio
async def test_fetcher_post(monkeypatch, fake_session):
    """
    Test fetching a simple HTML page successfully. Method: POST
    """
    monkeypatch.setattr("aiohttp.ClientSession", lambda *args, **kwargs: fake_session)
    fetcher = Fetcher()
    try:
        resource = await fetcher.fetch(DEFAULT_TEST_URL, method=HttpMethod.POST)
        assert isinstance(resource, Resource)
        assert resource.url == DEFAULT_TEST_URL
        assert resource.metadata["status_code"] == 200
        assert resource.metadata["mime"] == "text/html"
        assert resource.metadata["encoding"] == "utf-8"
        assert b"Hello" in resource.content
        assert isinstance(resource.hash, str)
    finally:
        await fetcher.aclose()


@pytest.mark.asyncio
async def test_fetcher_unsupported_method(monkeypatch):
    """
    Test fetching a simple HTML page successfully. Method: PUT (unsupported)
    """
    fetcher = Fetcher()
    try:
        with pytest.raises(FetchError):
            await fetcher.fetch(DEFAULT_TEST_URL, method="PUT")
    finally:
        await fetcher.aclose()


@pytest.mark.asyncio
async def test_fetcher_ensure_session(monkeypatch, fake_session):
    """
    Test that the aiohttp ClientSession is created and closed properly.
    """
    monkeypatch.setattr("aiohttp.ClientSession", lambda *args, **kwargs: fake_session)

    fetcher = Fetcher()
    try:
        resource = await fetcher.fetch(DEFAULT_TEST_URL)

        assert fetcher.session is not None
        assert resource.url == DEFAULT_TEST_URL
        assert resource.metadata.get("status_code") == 200
        assert resource.metadata.get("mime") == "text/html"
        assert resource.metadata.get("encoding") == "utf-8"
        assert b"Hello" in resource.content

        resource = await fetcher.fetch(DEFAULT_TEST_URL)
    finally:
        await fetcher.aclose()


@pytest.mark.asyncio
async def test_fetcher_ensure_session_closed(monkeypatch, fake_session):
    """
    Test that the aiohttp ClientSession is created and closed properly.
    """

    monkeypatch.setattr("aiohttp.ClientSession", lambda *args, **kwargs: fake_session)

    fetcher = Fetcher()
    try:
        await fetcher.fetch(DEFAULT_TEST_URL)
        assert fetcher.session is not None
    finally:
        await fetcher.aclose()

    await fetcher.aclose()
    assert fetcher.session is None


@pytest.mark.asyncio
async def test_fetcher_fetch_with_retries(monkeypatch):
    """
    Test the _fetch_with_retries method to ensure it retries on failure.
    """
    call_count = 0

    async def mock_fetch_once(url, method=HttpMethod.GET, stream_to=None, headers=None):
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise aiohttp.ClientError("Simulated network error")
        return Resource(
            url=url,
            content=b"Recovered content",
            metadata={
                "status_code": 200,
                "mime": "text/plain",
                "encoding": None,
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            },
            hash="dummyhash",
        )

    fetcher = Fetcher(retries=3, timeout=0.1)
    monkeypatch.setattr(fetcher, "_fetch_once", mock_fetch_once)

    try:
        resource = await fetcher.fetch(DEFAULT_TEST_URL)
        assert resource.content == b"Recovered content"
        assert call_count == 2  # Should have retried twice before succeeding
    finally:
        await fetcher.aclose()


@pytest.mark.asyncio
async def test_fetcher_fetch_with_exceeding_retries(monkeypatch):
    """
    Test the _fetch_with_retries method to ensure it raises FetchError after exceeding retries.
    """
    call_count = 0

    async def mock_fetch_once(url, method=HttpMethod.GET, stream_to=None, headers=None):
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise aiohttp.ClientError("Simulated network error")
        return Resource(
            url=url,
            content=b"Recovered content",
            metadata={
                "status_code": 200,
                "mime": "text/plain",
                "encoding": None,
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            },
            hash="dummyhash",
        )

    fetcher = Fetcher(retries=1, timeout=0.1)
    monkeypatch.setattr(fetcher, "_fetch_once", mock_fetch_once)

    try:
        with pytest.raises(FetchError):
            resp = await fetcher.fetch(DEFAULT_TEST_URL)
            assert resp is None
    finally:
        await fetcher.aclose()


@pytest.mark.asyncio
async def test_fetcher_context_manager(monkeypatch, fake_session):
    """
    Test using Fetcher as an async context manager.
    """
    monkeypatch.setattr("aiohttp.ClientSession", lambda *args, **kwargs: fake_session)

    async with Fetcher() as fetcher:
        resource = await fetcher.fetch(DEFAULT_TEST_URL)
        assert isinstance(resource, Resource)
        assert resource.url == DEFAULT_TEST_URL
        assert resource.metadata["status_code"] == 200
        assert resource.metadata["mime"] == "text/html"
        assert resource.metadata["encoding"] == "utf-8"
        assert b"Hello" in resource.content
        assert isinstance(resource.hash, str)

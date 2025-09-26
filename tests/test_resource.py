import hashlib
import tempfile
from pathlib import Path

import pytest

from shards.fetcher.resource import Resource


class DummyResp:
    def __init__(self, url, headers, status, content_bytes, encoding="utf-8"):
        self.url = url
        self.headers = headers
        self.status = status
        self._content_bytes = content_bytes
        self._encoding = encoding

    async def read(self):
        return self._content_bytes

    def get_encoding(self):
        return self._encoding

    class Content:
        def __init__(self, content_bytes):
            self._content_bytes = content_bytes

        async def iter_chunked(self, chunk_size):
            for i in range(0, len(self._content_bytes), chunk_size):
                yield self._content_bytes[i : i + chunk_size]

    @property
    def content(self):
        return DummyResp.Content(self._content_bytes)


@pytest.mark.asyncio
async def test_from_response_in_memory(monkeypatch):
    # Patch decompress to just return the input
    monkeypatch.setattr("shards.fetcher.resource.decompress", lambda b, e: b)
    url = "http://example.com"
    redirected_url = "http://example.com/redirect"
    content_bytes = b"hello world"
    headers = {
        "Content-Type": "text/plain; charset=utf-8",
        "Content-Encoding": "",
        "ETag": "abc123",
        "Last-Modified": "yesterday",
    }
    status = 200
    fetched_at = "2024-01-01T00:00:00Z"
    resp = DummyResp(redirected_url, headers, status, content_bytes)

    resource = await Resource.from_response(url, resp, fetched_at)

    assert resource.url == url
    assert resource.redirected_url == redirected_url
    assert resource.content == content_bytes
    assert resource.hash == hashlib.sha256(content_bytes).hexdigest()
    assert resource.metadata["status_code"] == status
    assert resource.metadata["headers"] == headers
    assert resource.metadata["mime"] == "text/plain"
    assert resource.metadata["encoding"] == "utf-8"
    assert resource.metadata["etag"] == "abc123"
    assert resource.metadata["last-modified"] == "yesterday"
    assert resource.metadata["content-encoding"] == ""
    assert resource.metadata["fetched_at"] == fetched_at
    assert resource.file_path is None


@pytest.mark.asyncio
async def test_from_response_stream_to_file(monkeypatch):
    # Patch decompress to just return the input
    monkeypatch.setattr("shards.fetcher.resource.decompress", lambda b, e: b)
    url = "http://example.com"
    redirected_url = "http://example.com/redirect"
    content_bytes = b"streamed content"
    headers = {
        "Content-Type": "application/octet-stream",
        "Content-Encoding": "",
        "ETag": None,
        "Last-Modified": None,
    }
    status = 201
    fetched_at = "2024-01-02T00:00:00Z"
    resp = DummyResp(redirected_url, headers, status, content_bytes)

    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = Path(tmpdir) / "output.bin"
        resource = await Resource.from_response(
            url, resp, fetched_at, stream_to=str(file_path)
        )

        assert resource.url == url
        assert resource.redirected_url == redirected_url
        assert resource.content is None
        assert resource.hash == hashlib.sha256(content_bytes).hexdigest()
        assert resource.metadata["status_code"] == status
        assert resource.metadata["headers"] == headers
        assert resource.metadata["mime"] == "application/octet-stream"
        assert resource.metadata["encoding"] == "utf-8"
        assert resource.metadata["etag"] is None
        assert resource.metadata["last-modified"] is None
        assert resource.metadata["content-encoding"] == ""
        assert resource.metadata["fetched_at"] == fetched_at
        assert Path(resource.file_path) == file_path
        # File should exist and contain the correct content
        with open(file_path, "rb") as f:
            assert f.read() == content_bytes


def test_repr_with_content():
    r = Resource(
        url="u",
        redirected_url="r",
        content=b"abc",
        hash="hash",
        metadata={},
        fetched_at="now",
        file_path=None,
    )
    s = repr(r)
    assert "<Resource u (3)>" in s


def test_repr_with_file_path():
    r = Resource(
        url="u",
        redirected_url="r",
        content=None,
        hash="hash",
        metadata={},
        fetched_at="now",
        file_path="somefile.txt",
    )
    s = repr(r)
    assert "<Resource u (-> somefile.txt)>" in s

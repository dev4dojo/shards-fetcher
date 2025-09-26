import hashlib
from pathlib import Path
from typing import Optional

from .decompress import decompress

CHUNK_SIZE = 8192


class Resource:
    """
    Represents a fetched resource.
    """

    def __init__(
        self,
        url: str,
        redirected_url: Optional[str] = None,
        content: Optional[bytes] = None,
        hash: Optional[str] = None,
        metadata: Optional[dict] = None,
        fetched_at: Optional[str] = None,
        file_path: Optional[str | Path] = None,
    ):
        """
        :param url: The original URL of the resource.
        :param redirected_url: The final URL after any redirects.
        :param content: The content of the resource, if loaded in memory.
        :param hash: The SHA256 hash of the content.
        :param metadata: Additional metadata about the resource.
        :param fetched_at: Timestamp when the resource was fetched.
        :param file_path: Path to the file where the content is stored, if applicable.
        """
        self.url = url
        self.redirected_url = redirected_url
        self.content = content
        self.hash = hash
        self.metadata = metadata
        self.fetched_at = fetched_at
        self.file_path = Path(file_path) if isinstance(file_path, str) else file_path

    def __repr__(self):
        """
        String representation of the Resource.
        """
        size = len(self.content) if self.content else f"-> {self.file_path}"
        return f"<Resource {self.url} ({size})>"

    @classmethod
    async def from_response(
        cls, url: str, resp, fetched_at: str, stream_to: Optional[str | Path] = None
    ) -> "Resource":
        """
        Create a Resource object from an aiohttp response.

        :param url: The original URL of the resource.
        :param resp: The aiohttp response object.
        :param fetched_at: Timestamp when the resource was fetched.
        :param stream_to: Optional file path to stream the content to.
        :return: A Resource object.
        """
        redirected_url = str(resp.url)
        content_type = resp.headers.get("Content-Type", "")
        mime = content_type.split(";")[0] if content_type else None
        encoding = resp.headers.get("Content-Encoding", "").lower()

        sha256hash = hashlib.sha256()
        content_bytes = None
        final_path = None

        if stream_to:
            final_path = await cls._stream_and_hash(resp, stream_to, sha256hash)
        else:
            content_bytes = await cls._read_and_decompress(resp, encoding)
            sha256hash.update(content_bytes)

        metadata = cls._extract_metadata(resp, content_type, mime, encoding, fetched_at)

        return cls(
            url=url,
            redirected_url=redirected_url,
            content=content_bytes,
            hash=sha256hash.hexdigest(),
            metadata=metadata,
            fetched_at=fetched_at,
            file_path=final_path,
        )

    @staticmethod
    async def _stream_and_hash(resp, stream_to: str | Path, hash: hashlib.sha256):
        """
        Stream response content to a file and compute its SHA256 hash.

        :param resp: The aiohttp response object.
        :param stream_to: File path to stream the content to.
        :param hash: A hashlib.sha256 object to update with the content.
        :return: The path to the file where content is streamed.
        """
        path = Path(stream_to) if isinstance(stream_to, str) else stream_to
        with path.open("wb") as f:
            async for chunk in resp.content.iter_chunked(CHUNK_SIZE):
                hash.update(chunk)
                f.write(chunk)
        return str(path)

    @staticmethod
    async def _read_and_decompress(resp, encoding: str):
        """
        Read and decompress response content based on its encoding.

        :param resp: The aiohttp response object.
        :param encoding: The content encoding (e.g., gzip, deflate).
        :return: The decompressed content as bytes.
        """
        raw = await resp.read()
        return decompress(raw, encoding)

    @staticmethod
    def _extract_metadata(resp, content_type, mime, encoding, fetched_at):
        """
        Extract metadata from the response.

        :param resp: The aiohttp response object.
        :param content_type: The Content-Type header value.
        :param mime: The MIME type extracted from Content-Type.
        :param encoding: The Content-Encoding header value.
        :param fetched_at: Timestamp when the resource was fetched.
        :return: A dictionary of metadata.
        """
        return {
            "headers": dict(resp.headers),
            "status_code": resp.status,
            "content-type": content_type,
            "mime": mime,
            "encoding": resp.get_encoding(),
            "etag": resp.headers.get("ETag"),
            "last-modified": resp.headers.get("Last-Modified"),
            "content-encoding": encoding,
            "fetched_at": fetched_at,
        }

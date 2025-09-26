# shards-fetcher

**Fetcher** is a reusable, efficient, and fault-tolerant HTTP content retrieval module. It supports both synchronous and asynchronous fetching with advanced features like retries, decompression, redirect tracking, and optional disk streaming.

## Features

- Asynchronous and synchronous HTTP fetching
- Automatic retry with exponential backoff
- Redirect tracking and logging
- Content decompression (`gzip`, `deflate`, `br`)
- Optional streaming directly to disk (for large files)
- Rich metadata including MIME type, encoding, ETag, etc.
- Customizable headers and payload formats (`json`, `form`, `raw`)
- Packaged `Resource` result model with content hash, metadata, and timestamps

## Installation

```bash
pip install aiohttp brotli
```

Optional: `brotli` is required only for `br` content-encoding support.

## Usage

### Asynchronous Fetch

```python
from fetcher import Fetcher
import asyncio

async def main():
    fetcher = Fetcher()
    resource = await fetcher.fetch("https://example.com/data.json")
    await fetcher.aclose()

    print(resource.content)
    print(resource.metadata)

asyncio.run(main())
```

### Synchronous Fetch

```python
from fetcher import Fetcher

fetcher = Fetcher()
resource = fetcher.sync_fetch("https://example.com/data.json")
print(resource.content)
print(resource.metadata)
```

### Stream to File

```python
await fetcher.fetch(
    "https://example.com/largefile.zip",
    stream_to="/tmp/data.zip"
)
```

## Resource Model

Every successful fetch returns a `Resource` object:

```python
Resource(
    url: str,
    redirected_url: str,
    content: Optional[bytes],
    file_path: Optional[str],
    hash: str,  # SHA-256 of content (decompressed or raw stream)
    metadata: dict,
    fetched_at: str  # ISO timestamp (UTC)
)
```

### Metadata Example

```json
{
  "status_code": 200,
  "headers": { "content-type": "application/json" },
  "mime": "application/json",
  "encoding": "utf-8",
  "etag": "abc123",
  "last-modified": "Wed, 25 Sep 2025 12:00:00 GMT",
  "content-encoding": "gzip",
  "fetched_at": "2025-09-26T18:00:00Z"
}
```

## Configuration

### Constructor Parameters

```python
Fetcher(
    concurrency=1,      # Number of concurrent sessions
    timeout=10.0,       # Per-request timeout
    retries=3           # Number of retries on failure
)
```

### Headers

Default headers:

```python
{
  "User-Agent": "Fetcher/1.0",
  "Accept-Encoding": "gzip, deflate"
}
```

> Custom headers override these defaults entirely.

## HTTP Features Summary

| Feature           | Supported                           |
| ----------------- | ----------------------------------- |
| Redirects         | (tracked in `redirected_url`)       |
| Compression       | (`gzip`, `deflate`, `br`)           |
| Streaming to disk | (with `stream_to` parameter)        |
| Retry on failure  | (network + 5xx)                     |
| Payload formats   | `json`, `form`, `bytes`, `str`      |
| Methods           | Any (GET, POST, PUT, DELETE, ...)   |

## Dependencies

* [aiohttp](https://docs.aiohttp.org/)
* [asyncio](https://docs.python.org/3/library/asyncio.html)
* [brotli](https://pypi.org/project/Brotli/) *(optional)*


## License

MIT License 


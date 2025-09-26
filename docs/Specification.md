# Fetcher Module Specification

_Last updated: 2025-09-22_

## Purpose

The `Fetcher` module is a reusable, HTTP-based content retrieval component used within the WebSync system. It supports both synchronous and asynchronous fetches, handling complex real-world scenarios like retries, compression, and streaming large responses to disk.

## Goals

- Centralized web content retrieval
- Reusable across CLI, workers, and pipelines
- Efficient: single session, streaming, decompression
- Fault-tolerant: retry, timeout, error reporting

## Fetcher Class

### Constructor

```python
class Fetcher:
    def __init__(
        concurrency: int = 1,
        timeout: float = 10.0,
        retries: int = 3,
    )
```

### Methods

#### Asynchronous Fetch

```python
async def fetch(
    url: str,
    *,
    method: str = "GET",
    headers: Optional[dict] = None,
    stream_to: Optional[str] = None,
    data: Optional[Union[dict, bytes, str]] = None,
    json: Optional[dict] = None,
) -> Resource
```

#### Synchronous Fetch

```python
def sync_fetch(...) -> Resource  # Same signature as fetch()
```

#### Close Session

```python
async def aclose()
```

## HTTP Behavior

- Uses `aiohttp.ClientSession` internally
- Only one session per Fetcher instance
- Auto-closes via `aclose()` (no context manager by default)

## Headers

- If `headers` is `None`, defaults to:

```python
{
    "User-Agent": "Fetcher/1.0",
    "Accept-Encoding": "gzip, deflate"
}
```

- If `headers` is provided, **defaults are NOT merged** — full override.

## Method and Payloads

| Parameter | Description |
|----------|-------------|
| `method` | Any HTTP method (`GET`, `POST`, etc.). Default: `"GET"` |
| `data` | Payload for `application/x-www-form-urlencoded`, raw bytes, or text |
| `json` | Payload for `application/json`. Automatically encoded. |
| `data` + `json` | Invalid. Raises an error. |

## Streaming Support

| Mode      | Behavior |
|-----------|----------|
| In-memory | Content is loaded into memory, decompressed (if needed), and passed to `Resource.content` |
| Streaming | Content is saved raw to `stream_to` path. No decompression. `Resource.content = None`, `file_path` is set |

## Retry & Timeout

- Retry on network errors and 5xx responses
- Backoff: `2 ** attempt`
- Max attempts = `1 + retries`

## Redirects

- Tracked automatically by `aiohttp`
- If `resp.url != url`, logs `Redirected: url → final_url`
- Final URL is stored in `Resource.redirected_url`

## Compression Support

| Encoding | Supported in-memory | Supported in streaming |
|----------|---------------------|--------------------------|
| gzip     | yes              | skipped (raw saved)   |
| deflate  | yes              | skipped               |
| br       | yes              | skipped               |

Decompression is handled via:
- `gzip`, `zlib`, `brotli` (optional)

---

## Resource Model

```python
class Resource:
    url: str
    redirected_url: str
    content: Optional[bytes]
    file_path: Optional[str]
    hash: str  # SHA-256 of content (uncompressed or raw stream)
    metadata: dict  # status, mime, encoding, headers, etc.
    fetched_at: str  # UTC ISO timestamp

    @classmethod
    async def from_response(
        url: str,
        resp: aiohttp.ClientResponse,
        fetched_at: str,
        stream_to: Optional[str] = None
    ) -> Resource
```

## Metadata Contents

Stored in `Resource.metadata`:

- `status_code`
- `headers` (as dict)
- `content-type`, `mime`, `encoding`
- `etag`, `last-modified`
- `content-encoding` (original)
- `fetched_at` (ISO UTC timestamp)

## External Dependencies

- `aiohttp`
- `asyncio`
- `brotli` (optional)

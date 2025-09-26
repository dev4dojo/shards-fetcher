import gzip
import zlib

from shards.fetcher.decompress import decompress


def test_decompress_gzip():
    original = b"hello gzip"
    compressed = gzip.compress(original)
    result = decompress(compressed, "gzip")
    assert result == original


def test_decompress_deflate():
    original = b"hello deflate"
    compressed = zlib.compress(original)
    result = decompress(compressed, "deflate")
    assert result == original


def test_decompress_unknown_encoding_returns_original():
    original = b"no compression"
    result = decompress(original, "unknown")
    assert result == original


def test_decompress_empty_bytes():
    result = decompress(b"", "gzip")
    assert result == b""


def test_decompress_is_chunked_skips_decompression():
    original = b"chunked data"
    compressed = gzip.compress(original)
    # Should skip decompression and return as-is
    result = decompress(compressed, "gzip", is_chunked=True)
    assert result == compressed


def test_decompress_invalid_data_returns_original():
    # Not actually gzip data
    bad_data = b"not really compressed"
    result = decompress(bad_data, "gzip")
    assert result == bad_data


def test_decompress_deflate_invalid_data_returns_original():
    bad_data = b"not deflate"
    result = decompress(bad_data, "deflate")
    assert result == bad_data

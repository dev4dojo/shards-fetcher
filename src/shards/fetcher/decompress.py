import gzip
import zlib

# import brotli


def decompress(data: bytes, encoding: str, is_chunked: bool = False) -> bytes:
    """
    Decompress data based on the specified encoding.
    :param data: The compressed data.
    :param encoding: The encoding type ('gzip', 'deflate', 'br', or
                     any other value for no decompression).
    :param is_chunked: Whether the data is chunked (streamed).
                       If True, decompression is skipped.
    :return: The decompressed data, or the original data if no
             decompression is performed.
    """
    try:
        if is_chunked:
            return data  # skip decompression for streamed chunks
        if encoding == "gzip":
            return gzip.decompress(data)
        elif encoding == "deflate":
            return zlib.decompress(data)
        # elif encoding == "br":
        #     return brotli.decompress(data)
        else:
            return data
    except Exception:
        return data

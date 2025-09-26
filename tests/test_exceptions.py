import pytest

from shards.fetcher.exceptions import FetchError


def test_fetch_error_inherits_exception():
    err = FetchError("http://example.com", "timeout")
    assert isinstance(err, Exception)


def test_fetch_error_message_and_url_attributes():
    url = "http://test.com"
    message = "not found"
    err = FetchError(url, message)
    assert err.url == url
    assert err.message == message


def test_fetch_error_str_message():
    url = "http://abc.com"
    message = "connection refused"
    err = FetchError(url, message)
    expected = f"Error fetching {url}: {message}"
    assert str(err) == expected


def test_fetch_error_raises():
    url = "http://fail.com"
    message = "failed"
    with pytest.raises(FetchError) as excinfo:
        raise FetchError(url, message)
    assert excinfo.value.url == url
    assert excinfo.value.message == message
    assert str(excinfo.value) == f"Error fetching {url}: {message}"

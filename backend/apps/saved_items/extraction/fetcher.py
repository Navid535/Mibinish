import logging
from dataclasses import dataclass
from urllib.parse import urljoin

import requests

from apps.saved_items.extraction.security import UnsafeURLError, assert_url_is_safe

logger = logging.getLogger(__name__)

CONNECT_TIMEOUT_SECONDS = 5
READ_TIMEOUT_SECONDS = 10
MAX_CONTENT_BYTES = 5 * 1024 * 1024  # 5 MB
MAX_REDIRECTS = 5
CHUNK_SIZE = 64 * 1024

USER_AGENT = "MibinishBot/1.0 (+https://mibinish.navid535.ir/bot)"


class FetchError(Exception):
    """
    Raised for any fetch failure that should be treated as non-fatal by
    the caller (unreachable host, timeout, disallowed redirect target,
    oversized body, non-2xx status, too many redirects). Never lets the
    caller mistake this for a bug — extraction failing here should just
    mean "no content this time", not a crashed task.
    """


@dataclass
class FetchResult:
    final_url: str
    status_code: int
    content_type: str  # e.g. "text/html" (without charset)
    charset: str | None
    content: bytes


def fetch_url(url: str) -> FetchResult:
    current_url = url

    with requests.Session() as session:
        for _hop in range(MAX_REDIRECTS + 1):
            try:
                assert_url_is_safe(current_url)
            except UnsafeURLError as exc:
                raise FetchError(str(exc)) from exc

            try:
                response = session.get(
                    current_url,
                    headers={"User-Agent": USER_AGENT},
                    timeout=(CONNECT_TIMEOUT_SECONDS, READ_TIMEOUT_SECONDS),
                    allow_redirects=False,
                    stream=True,
                )
            except requests.RequestException as exc:
                raise FetchError(f"Request failed for {current_url}: {exc}") from exc

            if response.is_redirect:
                location = response.headers.get("Location")
                response.close()
                if not location:
                    raise FetchError(
                        f"Redirect with no Location header from {current_url}"
                    )
                current_url = urljoin(current_url, location)
                continue

            if not (200 <= response.status_code < 300):
                response.close()
                raise FetchError(
                    f"Unexpected status code {response.status_code} from {current_url}"
                )

            return _read_body(response, current_url)

    raise FetchError(f"Too many redirects (> {MAX_REDIRECTS}) starting at {url}")


def _read_body(response: requests.Response, current_url: str) -> FetchResult:
    content_type_header = response.headers.get("Content-Type", "")
    content_type = (
        content_type_header.split(";")[0].strip().lower() or "application/octet-stream"
    )
    charset = None
    for part in content_type_header.split(";")[1:]:
        part = part.strip()
        if part.lower().startswith("charset="):
            charset = part.split("=", 1)[1].strip().strip('"')

    body = bytearray()
    try:
        for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
            body.extend(chunk)
            if len(body) > MAX_CONTENT_BYTES:
                raise FetchError(
                    f"Response body from {current_url} exceeds {MAX_CONTENT_BYTES} bytes limit"
                )
    except requests.RequestException as exc:
        raise FetchError(
            f"Error while reading response body from {current_url}: {exc}"
        ) from exc
    finally:
        response.close()

    return FetchResult(
        final_url=current_url,
        status_code=response.status_code,
        content_type=content_type,
        charset=charset,
        content=bytes(body),
    )

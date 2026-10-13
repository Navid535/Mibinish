from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from apps.saved_items.extraction.fetcher import FetchResult

HTML_CONTENT_TYPES = {"text/html", "application/xhtml+xml"}

# دامنه‌های شناخته‌شده به یه اسم خواناتر مپ می‌شن؛ هرچی توی لیست نباشه،
# همون دامنه‌ی خامش برمی‌گرده — هیچ‌وقت خالی نمی‌مونه.
KNOWN_SOURCES = {
    "instagram.com": "Instagram",
    "twitter.com": "Twitter",
    "x.com": "Twitter",
    "t.me": "Telegram",
    "telegram.me": "Telegram",
    "reddit.com": "Reddit",
    "youtube.com": "YouTube",
    "youtu.be": "YouTube",
    "github.com": "GitHub",
    "medium.com": "Medium",
    "wikipedia.org": "Wikipedia",
    "linkedin.com": "LinkedIn",
    "facebook.com": "Facebook",
    "tiktok.com": "TikTok",
}


def derive_source(url: str) -> str:
    """
    برچسب "source" فقط از روی خود URL تعیین می‌شه — نیازی به فچ کردن
    صفحه نداره. یعنی حتی اگه fetch/parse بعداً شکست بخوره، این مقدار
    از قبل و بدون وابستگی به شبکه قابل‌تعیینه.
    """
    hostname = (urlparse(url).hostname or "").lower()
    hostname = hostname[4:] if hostname.startswith("www.") else hostname

    for domain, label in KNOWN_SOURCES.items():
        if hostname == domain or hostname.endswith("." + domain):
            return label

    return hostname or ""


@dataclass
class ParsedContent:
    metadata: dict
    body_text: str | None


def parse_fetch_result(fetch_result: FetchResult) -> ParsedContent:
    """
    هیچ‌وقت exception پرت نمی‌کنه. همیشه یه چیز قابل‌استفاده برمی‌گردونه —
    برای محتوای غیر-HTML فقط content_type/اندازه، برای HTML هرچقدر که
    قبل از هر مشکلی موفق به استخراجش شدیم.
    """
    if fetch_result.content_type not in HTML_CONTENT_TYPES:
        return ParsedContent(
            metadata={
                "content_type": fetch_result.content_type,
                "content_length": len(fetch_result.content),
            },
            body_text=None,
        )

    html_text = _decode(fetch_result)

    try:
        soup = BeautifulSoup(html_text, "html.parser")
    except Exception:  # noqa: BLE001 - parsing هیچ‌وقت نباید کل pipeline رو بترکونه
        return ParsedContent(
            metadata={"content_type": fetch_result.content_type},
            body_text=None,
        )

    metadata = _extract_metadata(soup, fetch_result.final_url)
    body_text = _extract_body_text(soup)

    return ParsedContent(metadata=metadata, body_text=body_text)


def _decode(fetch_result: FetchResult) -> str:
    if fetch_result.charset:
        try:
            return fetch_result.content.decode(fetch_result.charset, errors="replace")
        except LookupError:
            pass  # اسم charset ناشناخته بود؛ می‌ریم سراغ fallback زیر

    return fetch_result.content.decode("utf-8", errors="replace")


def _meta_content(
    soup, *, property_name: str | None = None, name: str | None = None
) -> str | None:
    attrs = {"property": property_name} if property_name else {"name": name}
    tag = soup.find("meta", attrs=attrs)
    if tag and tag.get("content"):
        return tag["content"].strip()
    return None


def _extract_metadata(soup, final_url: str) -> dict:
    title = (
        _meta_content(soup, property_name="og:title")
        or _meta_content(soup, name="twitter:title")
        or (soup.title.string.strip() if soup.title and soup.title.string else None)
    )
    description = (
        _meta_content(soup, property_name="og:description")
        or _meta_content(soup, name="twitter:description")
        or _meta_content(soup, name="description")
    )
    image = _meta_content(soup, property_name="og:image") or _meta_content(
        soup, name="twitter:image"
    )
    site_name = _meta_content(soup, property_name="og:site_name")

    return {
        "title": title,
        "description": description,
        "image": image,
        "site_name": site_name,
        "final_url": final_url,
    }


NOISE_TAGS = ("script", "style", "nav", "footer", "header", "aside", "form", "noscript")


def _extract_body_text(soup) -> str | None:
    """
    بدنه‌ی متن به‌صورت best-effort. عمداً ساده نگهش داشتم (حذف
    تگ‌های واضحاً غیرمحتوایی + گرفتن بزرگ‌ترین بلوک متنی) به‌جای یه
    الگوریتم readability کامل — برای هدف نگهداری کافیه، و توی
    صفحات JS-heavy (اینستا، توییتر و...) طبیعتاً خالی برمی‌گرده که
    این یه شکست نیست، انتظار می‌ره.
    """
    for tag in soup.find_all(NOISE_TAGS):
        tag.decompose()

    candidates = soup.find_all(["article", "main"])
    if not candidates and soup.body:
        candidates = [soup.body]
    if not candidates:
        return None

    best = max(candidates, key=lambda tag: len(tag.get_text(strip=True)))
    text = best.get_text(separator="\n", strip=True)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text or None

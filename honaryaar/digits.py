import re

_PERSIAN_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
_SKIP_BLOCK = re.compile(
    r"(?is)(<(?:script|style|textarea)\b[^>]*>.*?</(?:script|style|textarea)\s*>)"
)


def _next_tag_end(html, start):
    """Return index after a tag that begins at start, respecting quoted attrs."""
    if start >= len(html) or html[start] != "<":
        return start
    if html.startswith("<!--", start):
        end = html.find("-->", start + 4)
        return len(html) if end < 0 else end + 3
    i = start + 1
    quote = None
    while i < len(html):
        ch = html[i]
        if quote:
            if ch == quote:
                quote = None
            i += 1
            continue
        if ch in "\"'":
            quote = ch
            i += 1
            continue
        if ch == ">":
            return i + 1
        i += 1
    return len(html)


def _convert_markup(html):
    out = []
    cursor = 0
    length = len(html)
    while cursor < length:
        tag_at = html.find("<", cursor)
        if tag_at < 0:
            out.append(html[cursor:].translate(_PERSIAN_DIGITS))
            break
        if tag_at > cursor:
            out.append(html[cursor:tag_at].translate(_PERSIAN_DIGITS))
        end = _next_tag_end(html, tag_at)
        out.append(html[tag_at:end])
        cursor = end
    return "".join(out)


def persian_digits_html(html):
    parts = _SKIP_BLOCK.split(html)
    converted = []
    for part in parts:
        head = part.lstrip()[:12].lower()
        if head.startswith("<script") or head.startswith("<style") or head.startswith("<textarea"):
            converted.append(part)
        else:
            converted.append(_convert_markup(part))
    return "".join(converted)


class PersianDigitsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.path.startswith("/admin"):
            return response
        content_type = response.get("Content-Type", "")
        if "text/html" not in content_type or getattr(response, "streaming", False):
            return response
        charset = response.charset or "utf-8"
        html = response.content.decode(charset)
        response.content = persian_digits_html(html).encode(charset)
        if "Content-Length" in response:
            response["Content-Length"] = str(len(response.content))
        return response

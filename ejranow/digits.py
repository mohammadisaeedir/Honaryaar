import re

_PERSIAN_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
_SKIP_BLOCK = re.compile(
    r"(?is)(<(?:script|style|textarea)\b[^>]*>.*?</(?:script|style|textarea)\s*>)"
)
_TAG_OR_TEXT = re.compile(r"(<[^>]*>)|([^<]+)")


def _convert_markup(html):
    return _TAG_OR_TEXT.sub(
        lambda match: match.group(1) if match.group(1) is not None else match.group(2).translate(_PERSIAN_DIGITS),
        html,
    )


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

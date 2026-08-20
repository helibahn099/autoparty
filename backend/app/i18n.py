"""Pick ru / en / ky for catalog rows and request language."""

from fastapi import Request


SUPPORTED = ("ru", "en", "ky")


def request_lang(request: Request | None = None, lang: str | None = None) -> str:
    if lang in SUPPORTED:
        return lang
    if request is None:
        return "ru"
    q = request.query_params.get("lang")
    if q in SUPPORTED:
        return q
    header = (request.headers.get("accept-language") or "ru").lower()
    for code in SUPPORTED:
        if header.startswith(code):
            return code
    return "ru"


def localized_name(obj, lang: str = "ru") -> str:
    if lang == "en" and getattr(obj, "name_en", None):
        return obj.name_en
    if lang == "ky" and getattr(obj, "name_ky", None):
        return obj.name_ky
    return getattr(obj, "name", "") or ""

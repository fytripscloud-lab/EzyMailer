"""Free consumer email provider domain detection."""

FREE_PROVIDER_DOMAINS: frozenset[str] = frozenset(
    d.lower()
    for d in [
        "gmail.com", "googlemail.com", "yahoo.com", "yahoo.co.uk", "yahoo.co.in",
        "yahoo.fr", "yahoo.de", "yahoo.es", "yahoo.it", "ymail.com", "rocketmail.com",
        "outlook.com", "hotmail.com", "hotmail.co.uk", "hotmail.fr", "hotmail.it",
        "live.com", "live.co.uk", "msn.com", "aol.com", "aim.com", "icloud.com",
        "me.com", "mac.com", "protonmail.com", "proton.me", "pm.me", "zoho.com",
        "mail.com", "gmx.com", "gmx.de", "gmx.net", "gmx.at", "web.de", "t-online.de",
        "yandex.com", "yandex.ru", "mail.ru", "inbox.com", "rediffmail.com",
        "qq.com", "163.com", "126.com", "sina.com", "sina.cn", "naver.com",
        "daum.net", "hanmail.net", "libero.it", "virgilio.it", "tiscali.it",
        "orange.fr", "wanadoo.fr", "laposte.net", "free.fr", "sfr.fr", "bluewin.ch",
        "seznam.cz", "centrum.cz", "fastmail.com", "tutanota.com", "tutanota.de",
        "hushmail.com", "lycos.com", "excite.com", "att.net", "sbcglobal.net",
        "verizon.net", "comcast.net", "bellsouth.net", "cox.net", "earthlink.net",
        "charter.net", "optonline.net", "frontier.com", "windstream.net",
    ]
)


def is_free_provider(domain: str) -> bool:
    return domain.lower() in FREE_PROVIDER_DOMAINS

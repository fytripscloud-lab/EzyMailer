"""Disposable / temporary email provider domain detection.

The list below covers widely-used disposable/temp-mail services. It is not
exhaustive (new disposable domains appear constantly) but catches the vast
majority seen in real-world lists.
"""

DISPOSABLE_DOMAINS: frozenset[str] = frozenset(
    d.lower()
    for d in [
        "mailinator.com", "mailinator.net", "mailinator.org", "sogetthis.com",
        "mailin8r.com", "mailinater.com", "10minutemail.com", "10minutemail.net",
        "10minemail.com", "20minutemail.com", "guerrillamail.com", "guerrillamail.net",
        "guerrillamail.org", "guerrillamail.biz", "guerrillamail.de", "guerrillamailblock.com",
        "sharklasers.com", "grr.la", "spam4.me", "yopmail.com", "yopmail.net",
        "yopmail.fr", "cool.fr.nf", "jetable.fr.nf", "nomail.xl.cx", "courriel.fr.nf",
        "jetable.org", "temp-mail.org", "temp-mail.io", "tempmail.com", "tempmail.net",
        "tempmailo.com", "tempmail.de", "tempinbox.com", "throwawaymail.com",
        "throwaway.email", "trashmail.com", "trashmail.net", "trashmail.me",
        "trash-mail.com", "trashmailgenerator.de", "fakeinbox.com", "fakemailgenerator.com",
        "getnada.com", "getairmail.com", "dispostable.com", "maildrop.cc",
        "mintemail.com", "moakt.com", "mohmal.com", "mytemp.email", "spamgourmet.com",
        "spambox.us", "spamex.com", "mailcatch.com", "mailnesia.com", "mailnull.com",
        "mytrashmail.com", "noclickemail.com", "owlymail.com", "putthisinyourspamdatabase.com",
        "deadaddress.com", "despam.it", "discard.email", "discardmail.com",
        "discardmail.de", "e4ward.com", "emailondeck.com", "emailtemporario.com.br",
        "einrot.com", "fleckens.hu", "incognitomail.com", "instant-mail.de",
        "mailexpire.com", "mailforspam.com", "mailmetrash.com", "mailscrap.com",
        "mailshell.com", "mailtemp.info", "mailzilla.com", "meltmail.com",
        "mt2015.com", "no-spam.ws", "nospam.ze.tc", "nowmymail.com", "objectmail.com",
        "pookmail.com", "quickinbox.com", "rcpt.at", "sneakemail.com", "spamfree24.org",
        "spamfree24.com", "spamfree24.de", "spamhereplease.com", "spamslicer.com",
        "spamspot.com", "superrito.com", "tempemail.net", "tempemail.co.za",
        "tempmailaddress.com", "temporaryemail.net", "temporaryinbox.com",
        "thankyou2010.com", "thisisnotmyrealemail.com", "tradermail.info",
        "tyldd.com", "veryrealemail.com", "wegwerfadresse.de", "wegwerfemail.de",
        "wegwerfmail.de", "wegwerfmail.net", "wegwerfmail.org", "wh4f.org",
        "willselfdestruct.com", "zoemail.org", "burnermail.io", "inboxbear.com",
        "emailfake.com", "fakemail.net", "luxusmail.org", "simplelogin.com",
        "anonaddy.com", "dropmail.me", "mailpoof.com", "33mail.com", "harakirimail.com",
        "mailbox52.ga", "mailbox92.biz", "mailbox62.co", "kurzepost.de", "mailimate.com",
        "tempail.com", "tempmail2.com", "crazymailing.com", "emlpro.com",
    ]
)


def is_disposable(domain: str) -> bool:
    return domain.lower() in DISPOSABLE_DOMAINS

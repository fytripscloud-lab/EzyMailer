import asyncio
import random
import string
from dataclasses import dataclass

import aiosmtplib
import dns.resolver

from app.core.security import is_safe_public_ip

REJECT_CODES = {550, 551, 553, 501, 503}


@dataclass
class SmtpCheckResult:
    status: str  # "accepted" | "rejected" | "unknown"
    code: int | None
    message: str | None


def _resolve_safe_ip_sync(host: str, timeout: float) -> str | None:
    resolver = dns.resolver.Resolver()
    resolver.timeout = timeout
    resolver.lifetime = timeout
    for rtype in ("A", "AAAA"):
        try:
            answers = resolver.resolve(host, rtype)
        except Exception:
            continue
        for r in answers:
            ip = str(r)
            if is_safe_public_ip(ip):
                return ip
    return None


class SmtpChecker:
    """RCPT-TO based mailbox verification. Never sends DATA/QUIT-after-send,
    so no email content is ever transmitted - only the SMTP server's
    accept/reject response to RCPT TO is inspected."""

    def __init__(
        self,
        concurrency: int,
        timeout_seconds: int,
        retries: int,
        helo_domain: str,
        from_address: str,
    ):
        self._sem = asyncio.Semaphore(concurrency)
        self._timeout = float(timeout_seconds)
        self._retries = max(retries, 0)
        self._helo_domain = helo_domain
        self._from_address = from_address

    async def _resolve_safe_ip(self, host: str) -> str | None:
        return await asyncio.to_thread(_resolve_safe_ip_sync, host, self._timeout)

    async def _probe(self, mx_host: str, rcpt_email: str) -> SmtpCheckResult:
        ip = await self._resolve_safe_ip(mx_host)
        if ip is None:
            return SmtpCheckResult("unknown", None, "mx host has no safe public ip")

        last_error: str | None = None
        for _ in range(self._retries + 1):
            try:
                async with self._sem:
                    # start_tls=False: we never send real mail content (no DATA),
                    # so plaintext EHLO/MAIL FROM/RCPT TO needs no encryption.
                    # aiosmtplib's default is opportunistic STARTTLS, which adds
                    # a cert-validation failure mode (misconfigured local CA
                    # store, self-signed certs, etc.) that has nothing to do
                    # with whether the recipient mailbox exists and would
                    # otherwise surface as a false "unknown".
                    smtp = aiosmtplib.SMTP(hostname=ip, port=25, timeout=self._timeout, start_tls=False)
                    await smtp.connect()
                    try:
                        await smtp.ehlo(hostname=self._helo_domain)
                        await smtp.mail(self._from_address)
                        code, message = await smtp.rcpt(rcpt_email)
                    finally:
                        try:
                            await smtp.quit()
                        except Exception:
                            pass
                if code == 250:
                    return SmtpCheckResult("accepted", code, message)
                if code in REJECT_CODES:
                    return SmtpCheckResult("rejected", code, message)
                return SmtpCheckResult("unknown", code, message)
            except (aiosmtplib.SMTPException, OSError, asyncio.TimeoutError) as exc:
                last_error = str(exc)
                continue
        return SmtpCheckResult("unknown", None, last_error or "smtp check failed")

    async def check_mailbox(self, mx_hosts: list[str], email: str) -> SmtpCheckResult:
        if not mx_hosts:
            return SmtpCheckResult("unknown", None, "no mx hosts")
        return await self._probe(mx_hosts[0], email)

    async def check_catch_all(self, mx_hosts: list[str], domain: str) -> str:
        if not mx_hosts:
            return "unknown"
        random_local = "nonexistent-" + "".join(
            random.choices(string.ascii_lowercase + string.digits, k=12)
        )
        result = await self._probe(mx_hosts[0], f"{random_local}@{domain}")
        if result.status == "accepted":
            return "yes"
        if result.status == "rejected":
            return "no"
        return "unknown"

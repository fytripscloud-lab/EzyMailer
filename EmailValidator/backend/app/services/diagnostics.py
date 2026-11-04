import asyncio
import time
from datetime import datetime, timezone
from typing import Any

import aiosmtplib
import dns.exception
import dns.resolver

from app.config import Settings
from app.services.checks.smtp_check import _resolve_safe_ip_sync

_CACHE_TTL_SECONDS = 30.0
_cache: dict[str, tuple[float, dict[str, Any]]] = {}


def _resolve_test_mx_sync(domain: str, timeout: float) -> str | None:
    resolver = dns.resolver.Resolver()
    resolver.timeout = timeout
    resolver.lifetime = timeout
    try:
        answers = resolver.resolve(domain, "MX")
        return str(min(answers, key=lambda r: r.preference).exchange).rstrip(".")
    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.exception.Timeout):
        return None
    except Exception:
        return None


async def _check_dns(settings: Settings) -> tuple[str, str, str | None]:
    domain = settings.diagnostics_test_domain
    mx_host = await asyncio.to_thread(_resolve_test_mx_sync, domain, settings.dns_timeout_seconds)
    if mx_host:
        return "ok", f"resolved MX for {domain} ({mx_host})", mx_host
    return "failed", f"could not resolve an MX record for {domain}", None


async def _check_smtp_port(settings: Settings, mx_host: str | None) -> tuple[str, str]:
    """Attempts a full connect + EHLO handshake, not just a bare TCP connect.

    A bare TCP connect succeeding is not enough to predict whether real
    RCPT TO probes will work: some providers accept the TCP connection but
    then silently stall or drop the SMTP conversation for senders they
    don't recognize, which a plain `open_connection` can't detect.
    """
    if not settings.enable_smtp_check:
        return "disabled", "SMTP mailbox checks are disabled (ENABLE_SMTP_CHECK=false)"
    if not mx_host:
        return "unknown", "could not resolve a test mail server to check connectivity against"

    ip = await asyncio.to_thread(_resolve_safe_ip_sync, mx_host, float(settings.dns_timeout_seconds))
    if ip is None:
        return "unknown", f"{mx_host} did not resolve to a safe public IP"

    timeout = float(settings.smtp_timeout_seconds)
    try:
        # start_tls=False: match the real checker's behavior (see smtp_check.py)
        # so this diagnostic accurately predicts what real validation will see.
        smtp = aiosmtplib.SMTP(hostname=ip, port=25, timeout=timeout, start_tls=False)
        await smtp.connect()
        try:
            await smtp.ehlo(hostname=settings.smtp_helo_domain)
        finally:
            try:
                await smtp.quit()
            except Exception:
                pass
        return "open", f"connected and completed an SMTP handshake with {mx_host} ({ip}) in under {timeout:.0f}s"
    except TimeoutError:
        return (
            "timeout",
            f"connected to {mx_host} ({ip}) but the SMTP conversation did not complete within {timeout:.0f}s — "
            "the TCP port is open but some providers silently stall the handshake for unrecognized senders, "
            "which behaves like Unknown during real validation",
        )
    except (aiosmtplib.SMTPException, OSError) as exc:
        return "blocked", f"could not reach {mx_host} ({ip}) on port 25: {exc}"


async def run_diagnostics(settings: Settings, use_cache: bool = True) -> dict[str, Any]:
    cached = _cache.get("result")
    if use_cache and cached and (time.monotonic() - cached[0]) < _CACHE_TTL_SECONDS:
        return cached[1]

    dns_status, dns_detail, mx_host = await _check_dns(settings)
    smtp_status, smtp_detail = await _check_smtp_port(settings, mx_host)

    result: dict[str, Any] = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "backend": "ok",
        "dns": dns_status,
        "dns_detail": dns_detail,
        "smtp_port_25": smtp_status,
        "smtp_detail": smtp_detail,
        "smtp_check_enabled": settings.enable_smtp_check,
        "catch_all_check_enabled": settings.enable_catch_all_check,
        "smtp_concurrency": settings.smtp_concurrency,
        "dns_concurrency": settings.dns_concurrency,
        "max_upload_size_mb": settings.max_upload_size_mb,
        "max_rows": settings.max_rows,
        "job_retention_hours": settings.job_retention_hours,
    }
    _cache["result"] = (time.monotonic(), result)
    return result

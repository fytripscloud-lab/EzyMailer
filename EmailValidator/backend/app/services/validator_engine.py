import asyncio
from dataclasses import dataclass

from app.config import Settings
from app.services.checks.disposable import is_disposable
from app.services.checks.dns_checks import DnsCache
from app.services.checks.free_provider import is_free_provider
from app.services.checks.role_based import is_role_based
from app.services.checks.smtp_check import SmtpChecker
from app.services.checks.syntax import check_syntax


@dataclass
class EmailCheckResult:
    email: str
    syntax_valid: bool
    domain_valid: bool
    mx_found: bool
    smtp: str  # "accepted" | "rejected" | "unknown"
    disposable: bool
    free_provider: bool
    role_based: bool
    catch_all: str  # "yes" | "no" | "unknown"
    final_status: str  # "valid" | "invalid" | "risky" | "unknown"


class ValidationEngine:
    """Orchestrates the full per-email check pipeline. One instance is
    shared across a whole job (and could be shared across jobs) so its
    DNS/catch-all caches amortize across duplicate domains."""

    def __init__(self, settings: Settings):
        self._settings = settings
        self._dns_cache = DnsCache(
            ttl_seconds=settings.dns_cache_ttl_seconds,
            concurrency=settings.dns_concurrency,
            timeout_seconds=settings.dns_timeout_seconds,
        )
        self._smtp_checker = SmtpChecker(
            concurrency=settings.smtp_concurrency,
            timeout_seconds=settings.smtp_timeout_seconds,
            retries=settings.smtp_retries,
            helo_domain=settings.smtp_helo_domain,
            from_address=settings.smtp_from_address,
        )
        self._catch_all_cache: dict[str, str] = {}
        self._catch_all_locks: dict[str, asyncio.Lock] = {}

    async def _get_catch_all(self, domain: str, mx_hosts: list[str]) -> str:
        cached = self._catch_all_cache.get(domain)
        if cached is not None:
            return cached
        lock = self._catch_all_locks.setdefault(domain, asyncio.Lock())
        async with lock:
            cached = self._catch_all_cache.get(domain)
            if cached is not None:
                return cached
            result = await self._smtp_checker.check_catch_all(mx_hosts, domain)
            self._catch_all_cache[domain] = result
            return result

    @staticmethod
    def _decide_final_status(
        smtp_status: str, disposable: bool, role_based_flag: bool, catch_all: str
    ) -> str:
        # Hard rejects are always invalid, regardless of other signals.
        if smtp_status == "rejected":
            return "invalid"
        # Deliverable-but-risky signals: never silently promoted to "valid".
        if disposable or role_based_flag or catch_all == "yes":
            return "risky"
        if smtp_status == "accepted":
            return "valid"
        # SMTP inconclusive/blocked and no other risk/invalid signal found -
        # per spec, mailbox existence is never assumed from MX alone.
        return "unknown"

    async def validate_one(self, raw_email: str) -> EmailCheckResult:
        syntax = check_syntax(raw_email)
        if not syntax.valid:
            return EmailCheckResult(
                email=raw_email,
                syntax_valid=False,
                domain_valid=False,
                mx_found=False,
                smtp="unknown",
                disposable=False,
                free_provider=False,
                role_based=False,
                catch_all="unknown",
                final_status="invalid",
            )

        domain = syntax.domain or ""
        local_part = syntax.local_part or ""
        disposable = is_disposable(domain)
        free_provider = is_free_provider(domain)
        role_based_flag = is_role_based(local_part)

        dns_result = await self._dns_cache.resolve(domain)
        if not dns_result.domain_exists:
            return EmailCheckResult(
                email=syntax.normalized_email or raw_email,
                syntax_valid=True,
                domain_valid=False,
                mx_found=False,
                smtp="unknown",
                disposable=disposable,
                free_provider=free_provider,
                role_based=role_based_flag,
                catch_all="unknown",
                final_status="invalid",
            )

        if not dns_result.mx_hosts:
            return EmailCheckResult(
                email=syntax.normalized_email or raw_email,
                syntax_valid=True,
                domain_valid=True,
                mx_found=dns_result.mx_found,
                smtp="unknown",
                disposable=disposable,
                free_provider=free_provider,
                role_based=role_based_flag,
                catch_all="unknown",
                final_status="invalid",
            )

        smtp_status = "unknown"
        catch_all = "unknown"
        if self._settings.enable_smtp_check:
            smtp_result = await self._smtp_checker.check_mailbox(
                dns_result.mx_hosts, syntax.normalized_email or raw_email
            )
            smtp_status = smtp_result.status
            if self._settings.enable_catch_all_check:
                catch_all = await self._get_catch_all(domain, dns_result.mx_hosts)

        final_status = self._decide_final_status(smtp_status, disposable, role_based_flag, catch_all)

        return EmailCheckResult(
            email=syntax.normalized_email or raw_email,
            syntax_valid=True,
            domain_valid=True,
            mx_found=dns_result.mx_found,
            smtp=smtp_status,
            disposable=disposable,
            free_provider=free_provider,
            role_based=role_based_flag,
            catch_all=catch_all,
            final_status=final_status,
        )

import asyncio
import time
from dataclasses import dataclass, field

import dns.exception
import dns.resolver


@dataclass
class DnsResult:
    domain_exists: bool
    mx_found: bool
    mx_hosts: list[str] = field(default_factory=list)
    error: str | None = None


class DnsCache:
    """Per-domain cached DNS/MX resolution with bounded concurrency so
    repeated domains (gmail.com, yahoo.com, ...) across a large batch hit
    the cache instead of re-querying DNS, and concurrent lookups for the
    same new domain are coalesced into a single query."""

    def __init__(self, ttl_seconds: int, concurrency: int, timeout_seconds: int):
        self._ttl = ttl_seconds
        self._timeout = float(timeout_seconds)
        self._cache: dict[str, tuple[float, DnsResult]] = {}
        self._locks: dict[str, asyncio.Lock] = {}
        self._sem = asyncio.Semaphore(concurrency)

    def _lock_for(self, domain: str) -> asyncio.Lock:
        lock = self._locks.get(domain)
        if lock is None:
            lock = asyncio.Lock()
            self._locks[domain] = lock
        return lock

    def _cached(self, domain: str) -> DnsResult | None:
        entry = self._cache.get(domain)
        if entry and (time.monotonic() - entry[0]) < self._ttl:
            return entry[1]
        return None

    async def resolve(self, domain: str) -> DnsResult:
        domain = domain.lower()
        cached = self._cached(domain)
        if cached is not None:
            return cached
        async with self._lock_for(domain):
            cached = self._cached(domain)
            if cached is not None:
                return cached
            async with self._sem:
                result = await asyncio.to_thread(self._resolve_sync, domain)
            self._cache[domain] = (time.monotonic(), result)
            return result

    def _resolve_sync(self, domain: str) -> DnsResult:
        resolver = dns.resolver.Resolver()
        resolver.timeout = self._timeout
        resolver.lifetime = self._timeout

        try:
            answers = resolver.resolve(domain, "MX")
            mx_hosts = [str(r.exchange).rstrip(".") for r in sorted(answers, key=lambda r: r.preference)]
            return DnsResult(domain_exists=True, mx_found=True, mx_hosts=mx_hosts)
        except dns.resolver.NoAnswer:
            # No MX record published; RFC 5321 allows falling back to the A/AAAA
            # record of the domain itself as an implicit mail host.
            if self._has_any_record(resolver, domain):
                return DnsResult(domain_exists=True, mx_found=False, mx_hosts=[domain])
            return DnsResult(domain_exists=True, mx_found=False, mx_hosts=[])
        except dns.resolver.NXDOMAIN:
            return DnsResult(domain_exists=False, mx_found=False, error="NXDOMAIN")
        except dns.exception.Timeout:
            return DnsResult(domain_exists=False, mx_found=False, error="dns_timeout")
        except Exception as exc:  # pragma: no cover - defensive
            return DnsResult(domain_exists=False, mx_found=False, error=str(exc))

    @staticmethod
    def _has_any_record(resolver: dns.resolver.Resolver, domain: str) -> bool:
        for rtype in ("A", "AAAA"):
            try:
                resolver.resolve(domain, rtype)
                return True
            except Exception:
                continue
        return False

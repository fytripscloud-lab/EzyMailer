import asyncio

import dns.exception
import dns.resolver
import pytest

from app.services.checks.dns_checks import DnsCache


class FakeMxAnswer:
    def __init__(self, preference: int, exchange: str):
        self.preference = preference
        self.exchange = exchange + "."


@pytest.mark.asyncio
async def test_dns_cache_resolves_mx(monkeypatch):
    def fake_resolve(self, domain, rtype):
        assert rtype == "MX"
        return [FakeMxAnswer(10, "mx1.example.com"), FakeMxAnswer(5, "mx0.example.com")]

    monkeypatch.setattr(dns.resolver.Resolver, "resolve", fake_resolve)

    cache = DnsCache(ttl_seconds=60, concurrency=5, timeout_seconds=2)
    result = await cache.resolve("example.com")

    assert result.domain_exists is True
    assert result.mx_found is True
    assert result.mx_hosts == ["mx0.example.com", "mx1.example.com"]  # sorted by preference


@pytest.mark.asyncio
async def test_dns_cache_nxdomain(monkeypatch):
    def fake_resolve(self, domain, rtype):
        raise dns.resolver.NXDOMAIN()

    monkeypatch.setattr(dns.resolver.Resolver, "resolve", fake_resolve)

    cache = DnsCache(ttl_seconds=60, concurrency=5, timeout_seconds=2)
    result = await cache.resolve("doesnotexist.invalid")

    assert result.domain_exists is False
    assert result.mx_found is False
    assert result.error == "NXDOMAIN"


@pytest.mark.asyncio
async def test_dns_cache_timeout_returns_unknown_domain(monkeypatch):
    def fake_resolve(self, domain, rtype):
        raise dns.exception.Timeout()

    monkeypatch.setattr(dns.resolver.Resolver, "resolve", fake_resolve)

    cache = DnsCache(ttl_seconds=60, concurrency=5, timeout_seconds=2)
    result = await cache.resolve("slow.example")

    assert result.domain_exists is False
    assert result.error == "dns_timeout"


@pytest.mark.asyncio
async def test_dns_cache_deduplicates_concurrent_and_repeated_lookups(monkeypatch):
    call_count = 0

    def fake_resolve(self, domain, rtype):
        nonlocal call_count
        call_count += 1
        return [FakeMxAnswer(10, "mx.example.com")]

    monkeypatch.setattr(dns.resolver.Resolver, "resolve", fake_resolve)

    cache = DnsCache(ttl_seconds=60, concurrency=5, timeout_seconds=2)
    await asyncio.gather(*(cache.resolve("example.com") for _ in range(10)))
    await cache.resolve("example.com")

    assert call_count == 1


@pytest.mark.asyncio
async def test_dns_cache_no_mx_falls_back_to_domain_a_record(monkeypatch):
    def fake_resolve(self, domain, rtype):
        if rtype == "MX":
            raise dns.resolver.NoAnswer()
        return ["1.2.3.4"]

    monkeypatch.setattr(dns.resolver.Resolver, "resolve", fake_resolve)

    cache = DnsCache(ttl_seconds=60, concurrency=5, timeout_seconds=2)
    result = await cache.resolve("example.com")

    assert result.domain_exists is True
    assert result.mx_found is False
    assert result.mx_hosts == ["example.com"]

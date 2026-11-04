import aiosmtplib
import dns.resolver
import pytest

from app.services import diagnostics as diagnostics_module
from app.services.diagnostics import run_diagnostics


class FakeMx:
    def __init__(self, exchange):
        self.preference = 10
        self.exchange = exchange + "."


class FakeSMTP:
    raise_on_connect: Exception | None = None

    def __init__(self, hostname=None, port=None, timeout=None, start_tls=None):
        pass

    async def connect(self):
        if FakeSMTP.raise_on_connect:
            raise FakeSMTP.raise_on_connect

    async def ehlo(self, hostname=None):
        pass

    async def quit(self):
        pass


def _fake_resolve_factory(mx_ok=True):
    def fake_resolve(self, domain, rtype):
        if rtype == "MX":
            if mx_ok:
                return [FakeMx("mx.gmail.com")]
            raise dns.resolver.NXDOMAIN()
        if rtype == "A":
            return ["93.184.216.34"]
        raise dns.resolver.NoAnswer()

    return fake_resolve


@pytest.fixture(autouse=True)
def clear_diagnostics_cache():
    diagnostics_module._cache.clear()
    yield
    diagnostics_module._cache.clear()


@pytest.fixture(autouse=True)
def reset_fake_smtp(monkeypatch):
    FakeSMTP.raise_on_connect = None
    monkeypatch.setattr(diagnostics_module.aiosmtplib, "SMTP", FakeSMTP)
    yield


@pytest.mark.asyncio
async def test_diagnostics_reports_open_port_25(monkeypatch, test_settings):
    test_settings.enable_smtp_check = True
    monkeypatch.setattr(dns.resolver.Resolver, "resolve", _fake_resolve_factory())

    result = await run_diagnostics(test_settings, use_cache=False)

    assert result["dns"] == "ok"
    assert result["smtp_port_25"] == "open"
    assert result["smtp_check_enabled"] is True


@pytest.mark.asyncio
async def test_diagnostics_reports_blocked_port_25(monkeypatch, test_settings):
    test_settings.enable_smtp_check = True
    monkeypatch.setattr(dns.resolver.Resolver, "resolve", _fake_resolve_factory())
    FakeSMTP.raise_on_connect = aiosmtplib.SMTPConnectError("connection refused")

    result = await run_diagnostics(test_settings, use_cache=False)

    assert result["smtp_port_25"] == "blocked"


@pytest.mark.asyncio
async def test_diagnostics_reports_handshake_timeout(monkeypatch, test_settings):
    test_settings.enable_smtp_check = True
    monkeypatch.setattr(dns.resolver.Resolver, "resolve", _fake_resolve_factory())
    FakeSMTP.raise_on_connect = aiosmtplib.SMTPTimeoutError("timed out")

    result = await run_diagnostics(test_settings, use_cache=False)

    assert result["smtp_port_25"] == "timeout"
    assert "silently stall" in result["smtp_detail"]


@pytest.mark.asyncio
async def test_diagnostics_reports_dns_failure(monkeypatch, test_settings):
    test_settings.enable_smtp_check = True
    monkeypatch.setattr(dns.resolver.Resolver, "resolve", _fake_resolve_factory(mx_ok=False))

    result = await run_diagnostics(test_settings, use_cache=False)

    assert result["dns"] == "failed"
    assert result["smtp_port_25"] == "unknown"


@pytest.mark.asyncio
async def test_diagnostics_reports_disabled_when_smtp_check_off(monkeypatch, test_settings):
    test_settings.enable_smtp_check = False
    monkeypatch.setattr(dns.resolver.Resolver, "resolve", _fake_resolve_factory())

    result = await run_diagnostics(test_settings, use_cache=False)

    assert result["smtp_port_25"] == "disabled"


@pytest.mark.asyncio
async def test_diagnostics_result_is_cached(monkeypatch, test_settings):
    calls = {"count": 0}

    def fake_resolve(self, domain, rtype):
        calls["count"] += 1
        raise dns.resolver.NXDOMAIN()

    monkeypatch.setattr(dns.resolver.Resolver, "resolve", fake_resolve)

    await run_diagnostics(test_settings, use_cache=True)
    await run_diagnostics(test_settings, use_cache=True)

    assert calls["count"] == 1


def test_diagnostics_endpoint(client, monkeypatch):
    monkeypatch.setattr(dns.resolver.Resolver, "resolve", _fake_resolve_factory(mx_ok=False))
    diagnostics_module._cache.clear()

    resp = client.get("/api/v1/system/diagnostics")
    assert resp.status_code == 200
    data = resp.json()
    assert data["backend"] == "ok"
    assert data["dns"] == "failed"
    assert "smtp_concurrency" in data

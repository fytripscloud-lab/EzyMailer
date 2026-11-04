import pytest

from app.config import get_settings
from app.services.validator_engine import ValidationEngine


@pytest.fixture
def engine(monkeypatch):
    monkeypatch.setenv("ENABLE_SMTP_CHECK", "false")
    get_settings.cache_clear()
    settings = get_settings()
    yield ValidationEngine(settings)
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_invalid_syntax_short_circuits(engine):
    result = await engine.validate_one("not-an-email")
    assert result.final_status == "invalid"
    assert result.syntax_valid is False


@pytest.mark.asyncio
async def test_nxdomain_is_invalid(engine, monkeypatch):
    import dns.resolver

    def fake_resolve(self, domain, rtype):
        raise dns.resolver.NXDOMAIN()

    monkeypatch.setattr(dns.resolver.Resolver, "resolve", fake_resolve)

    result = await engine.validate_one("user@doesnotexist.invalid")
    assert result.final_status == "invalid"
    assert result.domain_valid is False


@pytest.mark.asyncio
async def test_disposable_domain_is_risky_without_smtp(engine, monkeypatch):
    import dns.resolver

    class FakeMx:
        preference = 10
        exchange = "mx.mailinator.com."

    def fake_resolve(self, domain, rtype):
        return [FakeMx()]

    monkeypatch.setattr(dns.resolver.Resolver, "resolve", fake_resolve)

    result = await engine.validate_one("user@mailinator.com")
    assert result.disposable is True
    # SMTP disabled -> smtp stays "unknown", but disposable alone forces "risky"
    assert result.final_status == "risky"


@pytest.mark.asyncio
async def test_role_based_local_part_detected(engine, monkeypatch):
    import dns.resolver

    class FakeMx:
        preference = 10
        exchange = "mx.example.com."

    monkeypatch.setattr(dns.resolver.Resolver, "resolve", lambda self, d, r: [FakeMx()])

    result = await engine.validate_one("admin@example.com")
    assert result.role_based is True
    assert result.final_status == "risky"


def test_decide_final_status_rules():
    decide = ValidationEngine._decide_final_status
    assert decide("rejected", False, False, "no") == "invalid"
    assert decide("accepted", True, False, "no") == "risky"
    assert decide("accepted", False, True, "no") == "risky"
    assert decide("accepted", False, False, "yes") == "risky"
    assert decide("accepted", False, False, "no") == "valid"
    assert decide("unknown", False, False, "no") == "unknown"
    assert decide("unknown", False, False, "unknown") == "unknown"

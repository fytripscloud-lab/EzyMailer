import asyncio

import aiosmtplib
import dns.resolver
import pytest

from app.services.checks import smtp_check as smtp_check_module
from app.services.checks.smtp_check import SmtpChecker


class FakeSMTP:
    """Stand-in for aiosmtplib.SMTP; records the sequence of calls made so
    tests can assert the probe never calls DATA / sends real mail."""

    responses: dict[str, tuple[int, str]] = {}
    raise_on_connect: Exception | None = None
    calls: list[str] = []

    def __init__(self, hostname=None, port=None, timeout=None, start_tls=None):
        self.hostname = hostname

    async def connect(self):
        FakeSMTP.calls.append("connect")
        if FakeSMTP.raise_on_connect:
            raise FakeSMTP.raise_on_connect

    async def ehlo(self, hostname=None):
        FakeSMTP.calls.append("ehlo")

    async def mail(self, sender):
        FakeSMTP.calls.append("mail")

    async def rcpt(self, recipient):
        FakeSMTP.calls.append("rcpt")
        return FakeSMTP.responses.get(recipient, (250, "OK"))

    async def quit(self):
        FakeSMTP.calls.append("quit")


@pytest.fixture(autouse=True)
def reset_fake_smtp(monkeypatch):
    FakeSMTP.responses = {}
    FakeSMTP.raise_on_connect = None
    FakeSMTP.calls = []
    monkeypatch.setattr(smtp_check_module.aiosmtplib, "SMTP", FakeSMTP)

    def fake_resolve(self, host, rtype):
        if rtype == "A":
            return ["93.184.216.34"]
        raise dns.resolver.NoAnswer()

    monkeypatch.setattr(dns.resolver.Resolver, "resolve", fake_resolve)
    yield


@pytest.mark.asyncio
async def test_check_mailbox_accepted():
    checker = SmtpChecker(concurrency=5, timeout_seconds=2, retries=0, helo_domain="h.example", from_address="v@h.example")
    FakeSMTP.responses["user@example.com"] = (250, "OK")

    result = await checker.check_mailbox(["mx.example.com"], "user@example.com")

    assert result.status == "accepted"
    assert "mail" in FakeSMTP.calls
    assert "rcpt" in FakeSMTP.calls
    assert "data" not in FakeSMTP.calls  # never sends DATA / actual email content


@pytest.mark.asyncio
async def test_check_mailbox_rejected():
    checker = SmtpChecker(concurrency=5, timeout_seconds=2, retries=0, helo_domain="h.example", from_address="v@h.example")
    FakeSMTP.responses["bounced@example.com"] = (550, "No such user")

    result = await checker.check_mailbox(["mx.example.com"], "bounced@example.com")

    assert result.status == "rejected"
    assert result.code == 550


@pytest.mark.asyncio
async def test_check_mailbox_inconclusive_response_is_unknown():
    checker = SmtpChecker(concurrency=5, timeout_seconds=2, retries=0, helo_domain="h.example", from_address="v@h.example")
    FakeSMTP.responses["maybe@example.com"] = (452, "Temporary issue")

    result = await checker.check_mailbox(["mx.example.com"], "maybe@example.com")

    assert result.status == "unknown"


@pytest.mark.asyncio
async def test_check_mailbox_connection_failure_is_unknown():
    checker = SmtpChecker(concurrency=5, timeout_seconds=2, retries=0, helo_domain="h.example", from_address="v@h.example")
    FakeSMTP.raise_on_connect = aiosmtplib.SMTPConnectError("blocked")

    result = await checker.check_mailbox(["mx.example.com"], "user@example.com")

    assert result.status == "unknown"


@pytest.mark.asyncio
async def test_check_mailbox_no_mx_hosts_is_unknown():
    checker = SmtpChecker(concurrency=5, timeout_seconds=2, retries=0, helo_domain="h.example", from_address="v@h.example")

    result = await checker.check_mailbox([], "user@example.com")

    assert result.status == "unknown"


@pytest.mark.asyncio
async def test_catch_all_detection_accepted_means_yes():
    checker = SmtpChecker(concurrency=5, timeout_seconds=2, retries=0, helo_domain="h.example", from_address="v@h.example")

    # Any probe address at this domain is accepted -> catch-all domain.
    original_rcpt = FakeSMTP.rcpt

    async def always_accept(self, recipient):
        FakeSMTP.calls.append("rcpt")
        return (250, "OK")

    FakeSMTP.rcpt = always_accept
    try:
        result = await checker.check_catch_all(["mx.example.com"], "example.com")
    finally:
        FakeSMTP.rcpt = original_rcpt

    assert result == "yes"


@pytest.mark.asyncio
async def test_catch_all_detection_rejected_means_no():
    checker = SmtpChecker(concurrency=5, timeout_seconds=2, retries=0, helo_domain="h.example", from_address="v@h.example")

    original_rcpt = FakeSMTP.rcpt

    async def always_reject(self, recipient):
        FakeSMTP.calls.append("rcpt")
        return (550, "No such user")

    FakeSMTP.rcpt = always_reject
    try:
        result = await checker.check_catch_all(["mx.example.com"], "example.com")
    finally:
        FakeSMTP.rcpt = original_rcpt

    assert result == "no"


@pytest.mark.asyncio
async def test_retries_on_transient_failure(monkeypatch):
    checker = SmtpChecker(concurrency=5, timeout_seconds=2, retries=1, helo_domain="h.example", from_address="v@h.example")

    attempts = {"count": 0}
    original_connect = FakeSMTP.connect

    async def flaky_connect(self):
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise OSError("connection refused")
        FakeSMTP.calls.append("connect")

    FakeSMTP.connect = flaky_connect
    try:
        result = await checker.check_mailbox(["mx.example.com"], "user@example.com")
    finally:
        FakeSMTP.connect = original_connect

    assert attempts["count"] == 2
    assert result.status == "accepted"

from app.services.checks.disposable import is_disposable
from app.services.checks.free_provider import is_free_provider
from app.services.checks.role_based import is_role_based
from app.services.checks.syntax import check_syntax


def test_syntax_valid_email():
    result = check_syntax("User.Name+tag@Example.COM")
    assert result.valid is True
    assert result.domain == "example.com"
    assert result.local_part is not None


def test_syntax_invalid_email():
    result = check_syntax("not-an-email")
    assert result.valid is False
    assert result.error is not None


def test_syntax_empty_email():
    result = check_syntax("   ")
    assert result.valid is False
    assert result.error == "empty"


def test_disposable_domain_detected():
    assert is_disposable("mailinator.com") is True
    assert is_disposable("MAILINATOR.COM") is True
    assert is_disposable("example.com") is False


def test_free_provider_detected():
    assert is_free_provider("gmail.com") is True
    assert is_free_provider("Yahoo.COM") is True
    assert is_free_provider("mycompany.com") is False


def test_role_based_detected():
    assert is_role_based("admin") is True
    assert is_role_based("Support") is True
    assert is_role_based("john.doe") is False

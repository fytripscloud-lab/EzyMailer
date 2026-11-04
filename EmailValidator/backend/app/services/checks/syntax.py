from dataclasses import dataclass

from email_validator import EmailNotValidError, validate_email


@dataclass
class SyntaxResult:
    valid: bool
    normalized_email: str | None
    local_part: str | None
    domain: str | None
    error: str | None


def check_syntax(raw_email: str) -> SyntaxResult:
    raw_email = (raw_email or "").strip()
    if not raw_email:
        return SyntaxResult(False, None, None, None, "empty")
    try:
        result = validate_email(raw_email, check_deliverability=False, allow_smtputf8=True)
    except EmailNotValidError as exc:
        return SyntaxResult(False, None, None, None, str(exc))
    return SyntaxResult(
        valid=True,
        normalized_email=result.normalized,
        local_part=result.local_part,
        domain=result.domain.lower(),
        error=None,
    )

import ipaddress
import re
import uuid

_SAFE_FILENAME_RE = re.compile(r"[^A-Za-z0-9._-]+")


def new_job_id() -> str:
    return uuid.uuid4().hex


def is_valid_job_id(job_id: str) -> bool:
    return bool(re.fullmatch(r"[0-9a-f]{32}", job_id))


def sanitize_filename(filename: str) -> str:
    """Strip any path components and unsafe characters; used only for
    display / Content-Disposition, never for building filesystem paths."""
    name = filename.replace("\\", "/").split("/")[-1]
    name = _SAFE_FILENAME_RE.sub("_", name).strip("._") or "file"
    return name[:255]


def is_safe_public_ip(ip_str: str) -> bool:
    """Reject private/loopback/link-local/reserved ranges to guard against
    SSRF and DNS-rebinding when connecting out to a resolved MX host."""
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return False
    return not (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )

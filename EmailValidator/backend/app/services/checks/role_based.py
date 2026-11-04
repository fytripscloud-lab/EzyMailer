"""Role-based (non-personal) mailbox local-part detection."""

ROLE_BASED_PREFIXES: frozenset[str] = frozenset(
    [
        "admin", "administrator", "webmaster", "hostmaster", "postmaster",
        "info", "contact", "support", "help", "helpdesk", "sales", "marketing",
        "billing", "accounts", "accounting", "noreply", "no-reply", "donotreply",
        "do-not-reply", "newsletter", "news", "press", "media", "jobs", "careers",
        "hr", "recruiting", "recruitment", "office", "general", "enquiries",
        "enquiry", "inquiries", "inquiry", "feedback", "service", "services",
        "team", "staff", "security", "abuse", "legal", "privacy", "compliance",
        "subscribe", "unsubscribe", "mailer", "mail", "root", "operator",
        "system", "sysadmin", "it", "tech", "technical", "customerservice",
        "customercare", "orders", "order", "shop", "store", "returns",
        "shipping", "partners", "partnership", "affiliate", "affiliates",
        "webadmin", "domainadmin", "hostadmin", "ftp", "www", "list",
        "lists", "bounce", "bounces", "notifications", "notification",
        "alerts", "alert", "info-request",
    ]
)


def is_role_based(local_part: str) -> bool:
    return local_part.lower() in ROLE_BASED_PREFIXES

import difflib
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
import dns.resolver

COMMON_EMAIL_DOMAINS = [
    "gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "icloud.com"
]

def validate_real_email(value):
    validate_email(value)
    domain = value.split('@')[-1]

    try:
        dns.resolver.resolve(domain, 'MX')
    except Exception:
        raise ValidationError(f"Domain '{domain}' does not exist or has no mail server.")

    match = difflib.get_close_matches(domain, COMMON_EMAIL_DOMAINS, n=1, cutoff=0.8)
    if match and match[0] != domain:
        raise ValidationError(
            f"Did you mean '{value.split('@')[0]}@{match[0]}'?"
        )


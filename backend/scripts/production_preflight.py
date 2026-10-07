"""Read-only configuration audit. Never prints credential values or calls providers."""
import json
import sys
from pathlib import Path
from urllib.parse import urlsplit
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.config import get_settings

settings = get_settings()
url = urlsplit(settings.public_base_url)
checks = {
    'demo_disabled': not settings.demo_mode,
    'stable_https_origin': url.scheme == 'https' and bool(url.hostname)
        and not url.hostname.endswith(('.app.github.dev', '.github.dev'))
        and not url.username and not url.query and not url.fragment,
    'instagram_app_secret': bool(settings.instagram_app_secret.get_secret_value()),
    'token_encryption_key': bool(settings.token_encryption_key.get_secret_value()),
    'operator_name': bool(settings.operator_name.strip()),
    'support_email': bool(settings.support_email.strip()),
    'smtp_transport': bool(settings.smtp_host and settings.smtp_from and settings.smtp_port in (465, 587)),
    'appwrite_storage_key': settings.media_storage != 'appwrite' or bool(settings.appwrite_api_key.get_secret_value()),
    'live_discovery_configured': settings.has_live_discovery,
    'live_outreach_implemented': settings.outreach_is_live,
}
print(json.dumps({'configuration_checks': checks,
    'not_certification': 'Passing configuration checks does not prove commercial readiness.',
    'external_checks': ['Meta public-user approval and real device OAuth',
                        'Always-on API and durable metadata deployment',
                        'Live email recovery and verification delivery',
                        'Provider consent, quotas and monitoring',
                        'Backup restore and Appwrite retention',
                        'Operator-specific policy review and signed Android release']}, indent=2))
sys.exit(0 if all(checks.values()) else 1)

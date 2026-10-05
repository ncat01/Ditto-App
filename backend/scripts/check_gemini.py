"""Run inside Codespaces. Prints no key, token or generated message."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.providers.gemini import generate_draft, ProviderUnavailable
try:
    generate_draft({'title': 'Generated sample clip', 'recipient': '@sample',
        'action': 'attribution_request', 'tone': 'professional', 'sandbox': True})
except ProviderUnavailable as exc:
    raise SystemExit('Gemini check failed: ' + str(exc))
print('Gemini connected: a valid sample draft was generated. No message was sent.')

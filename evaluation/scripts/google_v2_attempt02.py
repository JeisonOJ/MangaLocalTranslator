"""One consent-gated, text-only Cloud Translation Basic v2 request. Default: dry run."""
import argparse
import hashlib
import html
import json
import os
from pathlib import Path
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'evaluation/results/google-cloud-v2'
OUT = SOURCE / 'attempt-02'
EXPECTED = 'b9b2343405a16df4da719fcb07fc677d0116a7605ba5a1e1ac17d586cd016fbb'
ENDPOINT = 'https://translation.googleapis.com/language/translate/v2'
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--send', action='store_true')
parser.add_argument('--authorize-billable', action='store_true')
args = parser.parse_args()
body = (SOURCE / 'request-preview.json').read_bytes()
if hashlib.sha256(body).hexdigest() != EXPECTED:
    raise SystemExit('Payload changed; fresh review and authorization required.')
payload = json.loads(body)
characters = sum(len(s) for s in payload['q'])
if characters > 100 or len(payload['q']) != 3 or payload != {
        'q': payload['q'], 'source': 'ja', 'target': 'es', 'format': 'text', 'model': 'nmt'}:
    raise SystemExit('Request exceeds reviewed scope.')
plan = {'requests_maximum': 1, 'requests_sent': 0, 'input_code_points': characters,
        'character_budget': 100, 'request_bytes': len(body), 'payload_sha256': EXPECTED,
        'source': 'ja', 'target': 'es', 'format': 'text', 'model': 'nmt',
        'endpoint': ENDPOINT, 'automatic_retries': 0}
if not args.send:
    print(json.dumps(plan, indent=2))
    raise SystemExit(0)
if not args.authorize_billable:
    raise SystemExit('Explicit user authorization is required before sending.')
# Do not inspect credentials until the send/authorization gates have passed.
key = os.environ.get('MANGA_GOOGLE_TRANSLATE_API_KEY', '')
if not key.strip():
    raise SystemExit('Set MANGA_GOOGLE_TRANSLATE_API_KEY securely in this process environment.')
OUT.mkdir(exist_ok=True)
ledger = OUT / 'request-ledger.json'
plan['attempt_number'] = 2
plan['previous_ledger_sha256'] = '9fa728a0bb070b1e396f1ad0bbf8e153f1597aa59867483bc83dae2258d5823a'
plan.update(status='reserved_before_dispatch', request_attempts=1,
            characters_reserved=characters, started_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()))
# Exclusive reservation prevents an accidental second run/retry of this test.
with ledger.open('x', encoding='utf-8') as stream:
    json.dump(plan, stream, indent=2)

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None

request = urllib.request.Request(ENDPOINT, data=body, method='POST', headers={
    'Content-Type': 'application/json; charset=utf-8', 'X-Goog-Api-Key': key})
# No proxy discovery, redirects, retries, ADC discovery, or other endpoints.
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
started = time.perf_counter()
try:
    plan['requests_sent'] = 1  # Attempted; billability cannot be inferred on timeout.
    with opener.open(request, timeout=30) as response:
        raw = response.read()
        plan['http_status'] = response.status
    (OUT / 'response-raw.json').write_bytes(raw)
    data = json.loads(raw)
    translations = data['data']['translations']
    if len(translations) != len(payload['q']):
        raise ValueError('Unexpected response count')
    inputs = json.loads((SOURCE / 'inputs.json').read_text(encoding='utf-8'))
    results = [{**row, 'google_translatedText_exact': translated['translatedText'],
                'google_html_unescaped_display': html.unescape(translated['translatedText'])}
               for row, translated in zip(inputs, translations)]
    (OUT / 'translations.json').write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
    plan['status'] = 'success'
    plan['characters_in_successful_response'] = characters
except urllib.error.HTTPError as exc:
    plan.update(status='http_error_no_retry', http_status=exc.code)
    # Whitelist machine-readable error reasons only; never retain messages/metadata.
    try:
        import re
        error = json.loads(exc.read(65536)).get('error', {})
        reasons = [e.get('reason', '') for e in error.get('errors', [])]
        reasons += [e.get('reason', '') for e in error.get('details', [])]
        plan['google_reasons'] = sorted({s for s in reasons if isinstance(s, str) and re.fullmatch(r'[A-Za-z_]{1,80}', s) and s != key})
        status = error.get('status', '')
        if isinstance(status, str) and re.fullmatch(r'[A-Z_]{1,80}', status) and status != key:
            plan['google_status'] = status
    except Exception:
        pass
except Exception as exc:
    # Never log exception text, request headers, credentials, or server error body.
    plan.update(status='error_no_retry', error_type=type(exc).__name__)
finally:
    plan['elapsed_seconds'] = time.perf_counter() - started
    ledger.write_text(json.dumps(plan, indent=2), encoding='utf-8')
print(json.dumps({'status': plan['status'], 'attempted_requests': 1,
                  'input_code_points': characters}))

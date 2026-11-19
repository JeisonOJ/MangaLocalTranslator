"""Text-only Google Basic v2 client and deterministic offline fixture."""
import html
import json
import urllib.error
import urllib.request


class TranslationError(Exception):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def translate(regions, key, audit, persist):
    texts = [r['japanese'] for r in regions]
    audit['characters'] = sum(map(len, texts))
    if key is None:
        audit['status'] = 'mock_no_request'
        return ['Texto de prueba.' for _ in texts]

    payload = {'q': texts, 'source': 'ja', 'target': 'es', 'format': 'text', 'model': 'nmt'}
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    request = urllib.request.Request(
        'https://translation.googleapis.com/language/translate/v2',
        data=json.dumps(payload, ensure_ascii=False).encode('utf-8'), method='POST',
        headers={'Content-Type': 'application/json; charset=utf-8', 'X-Goog-Api-Key': key},
    )
    audit.update(status='reserved_before_dispatch', attempted_requests=1)
    persist()
    try:
        with opener.open(request, timeout=30) as response:
            audit['http_status'] = response.status
            entries = json.load(response)['data']['translations']
        if len(entries) != len(texts):
            raise ValueError('response count mismatch')
        raw = [entry['translatedText'] for entry in entries]
        if any(not isinstance(value, str) for value in raw):
            raise ValueError('invalid translatedText field')
    except urllib.error.HTTPError as exc:
        audit.update(status='http_error_no_retry', http_status=exc.code)
        raise TranslationError(f'Google HTTP {exc.code}') from None
    except Exception as exc:
        audit.update(status='error_no_retry', error_type=type(exc).__name__)
        raise TranslationError(f'Google request failed ({type(exc).__name__})') from None
    audit.update(status='success', exact_responses=raw)
    persist()
    return [html.unescape(value) for value in raw]

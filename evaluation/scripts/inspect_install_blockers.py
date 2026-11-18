import json
from pathlib import Path
import re
import urllib.parse
import urllib.request

OUT = Path(__file__).resolve().parents[1] / 'dependency-plan'
results = {}


def read(url):
    with urllib.request.urlopen(url, timeout=30) as response:
        return response.read().decode('utf-8')


for filename in ['setup.py', 'pyproject.toml']:
    url = 'https://raw.githubusercontent.com/zyddnys/pydensecrf/fix/python313-cython3/' + filename
    try:
        body = read(url)
        (OUT / ('pydensecrf-' + filename)).write_text(body, encoding='utf-8')
        results[filename] = {'url': url, 'content': body}
        print(filename, body[:7000])
    except Exception as exc:
        results[filename] = {'error': str(exc)}

for cuda in ['cu130', 'cu128']:
    index_url = f'https://download.pytorch.org/whl/{cuda}/torch/'
    try:
        body = read(index_url)
        links = re.findall(r'href="([^"]+)"', body)
        matching = [urllib.parse.urljoin(index_url, x) for x in links
                    if 'torch-2.14.1' in urllib.parse.unquote(x)
                    and 'cp312-cp312-win_amd64.whl' in x]
        results[cuda] = {'index': index_url, 'matches': []}
        for url in matching:
            url = url.split('#')[0]
            request = urllib.request.Request(url, method='HEAD')
            with urllib.request.urlopen(request, timeout=30) as response:
                info = {'url': url, 'size': response.headers.get('Content-Length')}
            results[cuda]['matches'].append(info)
        print(cuda, results[cuda])
    except Exception as exc:
        results[cuda] = {'error': str(exc)}
        print(cuda, str(exc))
(OUT / 'install-blockers.json').write_text(json.dumps(results, indent=2), encoding='utf-8')

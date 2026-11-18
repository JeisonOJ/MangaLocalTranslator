"""Inspect package metadata only; never install or download wheel bodies."""
import concurrent.futures
import json
from pathlib import Path
import urllib.request
from pip._vendor.packaging.requirements import Requirement
from pip._vendor.packaging.version import Version
from pip._vendor.packaging.tags import cpython_tags, compatible_tags
from pip._vendor.packaging.utils import parse_wheel_filename

BASE = Path(__file__).resolve().parents[2]
OUT = BASE / 'evaluation' / 'dependency-plan'
OUT.mkdir(exist_ok=True)


def get_json(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'MangaLocalTranslator-install-audit'})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def inspect(line):
    req = Requirement(line)
    ver = next((s.version for s in req.specifier if s.operator == '=='), None)
    url = f'https://pypi.org/pypi/{req.name}/' + (f'{ver}/json' if ver else 'json')
    try:
        data = get_json(url)
        files = data.get('urls', [])
        result = {'requirement': line, 'version': data['info']['version'],
                  'requires_python': data['info'].get('requires_python'),
                  'requires_dist': data['info'].get('requires_dist', []), 'wheels': {}}
        for py in ['312', '314']:
            pyver = (3, int(py[1:]))
            supported = set(cpython_tags(pyver, abis=['cp' + py], platforms=['win_amd64']))
            supported.update(compatible_tags(pyver, interpreter='cp' + py, platforms=['win_amd64']))
            candidates = []
            for f in files:
                n = f['filename']
                if not n.endswith('.whl') or f.get('yanked'):
                    continue
                if parse_wheel_filename(n)[3] & supported:
                    candidates.append(f)
            if candidates:
                f = min(candidates, key=lambda f: f['size'])
                result['wheels'][py] = {k: f[k] for k in ['filename', 'size', 'url']}
            else:
                result['wheels'][py] = None
        return req.name, result
    except Exception as exc:
        return req.name, {'requirement': line, 'error': str(exc)}


lines = []
for line in (BASE / 'upstream/requirements.txt').read_text().splitlines():
    line = line.split(' #')[0].strip()
    if line and not line.startswith(('#', '--')) and 'git+' not in line:
        lines.append(line)
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
    packages = dict(pool.map(inspect, lines))
(OUT / 'direct-package-metadata.json').write_text(json.dumps(packages, indent=2), encoding='utf-8')
for py in ['312', '314']:
    available = [v['wheels'][py] for v in packages.values() if v.get('wheels', {}).get(py)]
    missing = [k for k, v in packages.items() if not v.get('wheels', {}).get(py)]
    print('Python', py, 'direct wheels', len(available), 'download bytes', sum(f['size'] for f in available))
    print('No matching wheel or metadata error:', ', '.join(missing))
for k, v in packages.items():
    if 'error' in v:
        print('METADATA ERROR', k, v['error'])
print('Direct-only subtotal: excludes transitive dependencies, CUDA wheel substitution, and source builds.')

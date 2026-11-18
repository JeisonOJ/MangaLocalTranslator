"""Read dependency metadata/source only. No packages installed or binaries fetched."""
import concurrent.futures
import json
from pathlib import Path
import urllib.request

OUT = Path(__file__).resolve().parents[1] / 'crf-investigation'
OUT.mkdir(exist_ok=True)
URLS = {
    'pypi-original': 'https://pypi.org/pypi/pydensecrf/json',
    'pypi-maintained': 'https://pypi.org/pypi/pydensecrf2/json',
    'wheel-releases': 'https://api.github.com/repos/hgmzhn/pydensecrf/releases',
    'wheel-repo': 'https://api.github.com/repos/hgmzhn/pydensecrf',
    'wheel-tree': 'https://api.github.com/repos/hgmzhn/pydensecrf/git/trees/master?recursive=1',
    'pinned-tree': 'https://api.github.com/repos/zyddnys/pydensecrf/git/trees/fix/python313-cython3?recursive=1',
    'pinned-releases': 'https://api.github.com/repos/zyddnys/pydensecrf/releases',
    'conda-forge': 'https://api.anaconda.org/package/conda-forge/pydensecrf',
}


def fetch(item):
    name, url = item
    try:
        request = urllib.request.Request(url, headers={'User-Agent': 'MangaLocalTranslator-dependency-audit'})
        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.load(response)
        (OUT / (name + '.json')).write_text(json.dumps(data, indent=2), encoding='utf-8')
        if name.startswith('pypi'):
            print(name, data['info']['version'], data['info'].get('project_urls'))
            print([(f['filename'], f['size'], f['upload_time']) for f in data['urls']])
        elif name.endswith('releases'):
            print(name, [(r['tag_name'], r['target_commitish'], [(a['name'], a['size'], a.get('digest')) for a in r['assets']]) for r in data])
        elif name == 'conda-forge':
            print(name, 'platforms', sorted(set(f.get('attrs', {}).get('subdir', '') for f in data.get('files', []))))
            print('win64', [(f.get('basename'), f.get('size'), f.get('attrs', {}).get('depends')) for f in data.get('files', []) if f.get('attrs', {}).get('subdir') == 'win-64'][-10:])
        elif name.endswith('tree'):
            print(name, data.get('sha'), [(f['path'], f['sha']) for f in data.get('tree', []) if 'workflow' in f['path']])
        else:
            print(name, 'pushed', data.get('pushed_at'), 'archived', data.get('archived'))
        return name, data
    except Exception as exc:
        print(name, 'ERROR', str(exc))
        return name, {'error': str(exc)}


with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
    results = dict(pool.map(fetch, URLS.items()))
if 'tree' in results.get('wheel-tree', {}) and 'tree' in results.get('pinned-tree', {}):
    a = {f['path']: f['sha'] for f in results['wheel-tree']['tree'] if f['type'] == 'blob'}
    b = {f['path']: f['sha'] for f in results['pinned-tree']['tree'] if f['type'] == 'blob'}
    changed = [k for k in sorted(a.keys() | b.keys()) if a.get(k) != b.get(k)]
    (OUT / 'tree-comparison.json').write_text(json.dumps({'different_paths': changed}, indent=2))
    print('Different dependency source paths:', changed)

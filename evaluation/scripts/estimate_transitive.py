"""Approximate dependency closure from metadata; not a pip resolution or install."""
import concurrent.futures
import json
from pathlib import Path
import urllib.request
from pip._vendor.packaging.requirements import Requirement
from pip._vendor.packaging.markers import default_environment
from pip._vendor.packaging.specifiers import SpecifierSet
from pip._vendor.packaging.tags import cpython_tags, compatible_tags
from pip._vendor.packaging.utils import canonicalize_name, parse_wheel_filename
from pip._vendor.packaging.version import Version

OUT = Path(__file__).resolve().parents[1] / 'dependency-plan'
roots = json.loads((OUT / 'direct-package-metadata.json').read_text())
metadata = {canonicalize_name(k): v for k, v in roots.items()}
env = default_environment()
env.update(python_version='3.12', python_full_version='3.12.0', sys_platform='win32',
           platform_system='Windows', platform_machine='AMD64', os_name='nt')
tags = set(cpython_tags((3, 12), abis=['cp312'], platforms=['win_amd64']))
tags.update(compatible_tags((3, 12), interpreter='cp312', platforms=['win_amd64']))
extras = {}
for v in roots.values():
    r = Requirement(v['requirement'])
    extras[canonicalize_name(r.name)] = set(r.extras)
constraints = {}
conflicts = set()


def fetch(item):
    name, specs = item
    def get(url):
        with urllib.request.urlopen(url, timeout=30) as response:
            return json.load(response)
    try:
        d = get(f'https://pypi.org/pypi/{name}/json')
        spec = SpecifierSet(','.join(sorted(specs)))
        if not spec.contains(d['info']['version']):
            versions = [Version(v) for v in d['releases'] if not Version(v).is_prerelease and spec.contains(v)]
            d = get(f'https://pypi.org/pypi/{name}/{max(versions)}/json')
        wheels = [f for f in d.get('urls', []) if f['filename'].endswith('.whl')
                  and not f.get('yanked') and parse_wheel_filename(f['filename'])[3] & tags]
        chosen = min(wheels, key=lambda f: f['size']) if wheels else None
        return name, {'version': d['info']['version'], 'requires_dist': d['info'].get('requires_dist') or [],
                      'requires_python': d['info'].get('requires_python'),
                      'wheel': {k: chosen[k] for k in ['filename', 'size', 'url']} if chosen else None,
                      'sdist_bytes': min((f['size'] for f in d.get('urls', []) if f['filename'].endswith('.tar.gz')), default=None)}
    except Exception as exc:
        return name, {'error': str(exc)}


for iteration in range(12):
    requested = {}
    for name, v in list(metadata.items()):
        for raw in v.get('requires_dist') or []:
            r = Requirement(raw)
            contexts = [''] + list(extras.get(name, set()))
            if r.marker and not any(r.marker.evaluate({**env, 'extra': e}) for e in contexts):
                continue
            key = canonicalize_name(r.name)
            extras.setdefault(key, set()).update(r.extras)
            constraints.setdefault(key, set()).add(str(r.specifier))
            if key not in metadata:
                requested[key] = constraints[key]
            elif 'version' in metadata[key] and not r.specifier.contains(metadata[key]['version']):
                conflicts.add(f"{name} requires {r}; selected {metadata[key]['version']}")
    if not requested:
        break
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        metadata.update(dict(pool.map(fetch, requested.items())))

root_names = {canonicalize_name(k) for k in roots}
transitive = {k: v for k, v in metadata.items() if k not in root_names}
wheel_bytes = sum(v['wheel']['size'] for v in transitive.values() if v.get('wheel'))
result = {'method': 'metadata closure, latest satisfying versions when first encountered; not a resolver',
          'target': 'CPython 3.12 Windows AMD64', 'transitive': transitive,
          'transitive_wheel_bytes': wheel_bytes, 'conflicts': sorted(conflicts),
          'missing_transitive_wheels': [k for k, v in transitive.items() if not v.get('wheel')]}
(OUT / 'transitive-estimate.json').write_text(json.dumps(result, indent=2))
print('Additional transitive packages:', len(transitive), 'available wheel bytes:', wheel_bytes)
print('Missing transitive wheels:', result['missing_transitive_wheels'])
print('Constraint conflicts (requires a real resolver):', len(conflicts))
for conflict in sorted(conflicts):
    print(conflict)

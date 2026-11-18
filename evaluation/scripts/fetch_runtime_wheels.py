"""Fetch only the reviewed, size-bounded dependency plan; verify every wheel SHA256."""
import concurrent.futures
import hashlib
import json
from pathlib import Path
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'evaluation/runtime-install'
plan = json.loads((OUT / 'size-plan.json').read_text(encoding='utf-8'))
if plan['errors'] or plan['total_dependency_payload_bytes'] > 3_000_000_000:
    raise RuntimeError('Unresolved metadata or approved download budget exceeded')
if plan['wheel_unpacked_bytes'] + 400_000_000 > 9_000_000_000:
    raise RuntimeError('Approved installed-space budget exceeded')


def fetch(row):
    url = row['url']
    filename = urllib.parse.unquote(url.rsplit('/', 1)[-1])
    dest = OUT / 'wheelhouse' / filename
    if url.startswith('file:'):
        return filename
    if dest.exists() and hashlib.sha256(dest.read_bytes()).hexdigest() == row['sha256']:
        return filename
    temp = dest.with_suffix(dest.suffix + '.part')
    digest = hashlib.sha256()
    count = 0
    if row['download_bytes'] > 100_000_000:
        print('Downloading', filename, row['download_bytes'], 'bytes', flush=True)
    with urllib.request.urlopen(url, timeout=90) as response, temp.open('wb') as stream:
        while chunk := response.read(4 * 1024 * 1024):
            count += len(chunk)
            if count > row['wheel_bytes']:
                raise RuntimeError('Unexpected file size: ' + filename)
            digest.update(chunk)
            stream.write(chunk)
    if count != row['wheel_bytes'] or digest.hexdigest() != row['sha256']:
        raise RuntimeError('Download size/hash mismatch: ' + filename)
    temp.replace(dest)
    if count > 100_000_000:
        print('Verified', filename, flush=True)
    return filename


with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
    names = list(pool.map(fetch, plan['packages']))
lines = ['# Exact resolved runtime additions. Install offline into evaluation/envs/crf312.']
lines += [f"{r['name']}=={r['version']} --hash=sha256:{r['sha256']}" for r in plan['packages']]
(OUT / 'requirements-resolved.lock').write_text('\n'.join(lines) + '\n', encoding='utf-8')
print('Verified', len(names), 'wheels. Wrote hash-locked requirements.', flush=True)

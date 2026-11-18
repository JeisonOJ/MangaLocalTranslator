"""Verify conda-forge source/patch provenance and compare algorithm source to pinned fork."""
import hashlib
import io
import json
from pathlib import Path
import tarfile
import urllib.request
import zipfile
from compression import zstd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'crf-binary-audit'
OLD = ROOT / 'crf-investigation'


def get(url):
    with urllib.request.urlopen(url, timeout=30) as response:
        return response.read()


data = json.loads((OLD / 'pypi-original.json').read_text())
f = next(x for x in data['urls'] if x['filename'] == 'pydensecrf-1.0rc3.tar.gz')
blob = get(f['url'])
assert hashlib.sha256(blob).hexdigest() == '08be1603af2bede05c7697b6018e8e3059de7cc181e4e784b334889dcc749aa5'
(OUT / f['filename']).write_bytes(blob)
tree = json.loads((OLD / 'pinned-tree.json').read_text())
expected = {x['path']: x['sha'] for x in tree['tree'] if x['type'] == 'blob'}
same, different = [], []
with tarfile.open(fileobj=io.BytesIO(blob), mode='r:gz') as archive:
    for member in archive.getmembers():
        if not member.isfile():
            continue
        path = member.name.split('/', 1)[-1]
        if path.startswith('pydensecrf/densecrf/src/') or path.endswith(('.pyx', '.pxd', 'utils.py')):
            contents = archive.extractfile(member).read()
            gitsha = hashlib.sha1(b'blob ' + str(len(contents)).encode() + b'\0' + contents).hexdigest()
            (same if gitsha == expected.get(path) else different).append(path)
with zipfile.ZipFile(OUT / 'pydensecrf-1.0rc3-py312h72972c8_6.conda') as archive:
    info = next(x for x in archive.namelist() if x.startswith('info-') and x.endswith('.tar.zst'))
    with tarfile.open(fileobj=io.BytesIO(zstd.decompress(archive.read(info))), mode='r:') as tar:
        patch = tar.extractfile('info/recipe/backport_108.patch').read().decode()
remote_patch = get('https://raw.githubusercontent.com/conda-forge/pydensecrf-feedstock/921f40e2b0b7dc11621522c9df94ac6e61967a03/recipe/backport_108.patch').decode()
patch_paths = [line.split(' b/', 1)[1] for line in patch.splitlines() if line.startswith('diff --git ')]
report = {'source_sha256': hashlib.sha256(blob).hexdigest(), 'matching_source_paths': same,
          'differing_source_paths': different,
          'embedded_patch_matches_recorded_feedstock_commit': patch.replace('\r\n', '\n') == remote_patch.replace('\r\n', '\n'),
          'patch_paths_count': len(patch_paths),
          'patch_only_changes_eigen': all(x.startswith('pydensecrf/densecrf/include/Eigen/') for x in patch_paths)}
(OUT / 'source-comparison.json').write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))

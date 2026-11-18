"""Size resolved wheels using HTTP headers and ZIP central directories only."""
import concurrent.futures
import io
import json
from pathlib import Path
import urllib.parse
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'evaluation/runtime-install'
resolution = json.loads((OUT / 'pip-resolution.json').read_text(encoding='utf-8'))


class RemoteZip(io.RawIOBase):
    def __init__(self, url, length):
        self.url, self.length, self.pos = url, length, 0
    def seekable(self): return True
    def readable(self): return True
    def tell(self): return self.pos
    def seek(self, offset, whence=0):
        self.pos = offset if whence == 0 else (self.pos + offset if whence == 1 else self.length + offset)
        return self.pos
    def read(self, count=-1):
        count = min(count if count >= 0 else self.length - self.pos, self.length - self.pos)
        if count <= 0: return b''
        if count > 16_000_000: raise ValueError('Refusing excessive metadata range')
        request = urllib.request.Request(self.url, headers={'Range': f'bytes={self.pos}-{self.pos+count-1}'})
        with urllib.request.urlopen(request, timeout=35) as response:
            if response.status != 206: raise ValueError('Range not honored; refusing wheel body')
            data = response.read(count)
        self.pos += len(data)
        return data


def inspect(package):
    info = package['download_info']
    if not info.get('archive_info', {}).get('hashes', {}).get('sha256'):
        # Some ancillary PyTorch-index entries lack hashes; use the same version's
        # official PyPI wheel instead, with its publisher-supplied digest.
        name, version = package['metadata']['name'], package['metadata']['version']
        with urllib.request.urlopen(f'https://pypi.org/pypi/{name}/{version}/json', timeout=35) as response:
            metadata = json.load(response)
        filename = urllib.parse.unquote(info['url'].rsplit('/', 1)[-1])
        wheel = next(f for f in metadata['urls'] if f['filename'].lower() == filename.lower())
        info = {'url': wheel['url'], 'archive_info': {'hashes': wheel['digests']}}
    url = info['url']
    row = {'name': package['metadata']['name'], 'version': package['metadata']['version'],
           'url': url, 'sha256': info['archive_info']['hashes']['sha256']}
    try:
        if url.startswith('file:'):
            path = Path(urllib.request.url2pathname(urllib.parse.urlparse(url).path))
            row['download_bytes'] = 0
            row['wheel_bytes'] = path.stat().st_size
            archive = zipfile.ZipFile(path)
        else:
            request = urllib.request.Request(url, method='HEAD')
            with urllib.request.urlopen(request, timeout=35) as response:
                row['wheel_bytes'] = row['download_bytes'] = int(response.headers['Content-Length'])
            archive = zipfile.ZipFile(RemoteZip(url, row['wheel_bytes']))
        with archive:
            row['unpacked_bytes'] = sum(f.file_size for f in archive.infolist())
    except Exception as exc:
        row['error'] = str(exc)
    return row


with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
    rows = list(pool.map(inspect, resolution['install']))
report = {'packages': rows,
          'new_wheel_download_bytes': sum(r.get('download_bytes', 0) for r in rows),
          'wheel_unpacked_bytes': sum(r.get('unpacked_bytes', 0) for r in rows),
          'errors': [r for r in rows if r.get('error')]}
source_bytes = sum(json.loads((OUT / (name + '-source-metadata.json')).read_text())['file']['size'] for name in ['langdetect', 'unidic-lite'])
report['source_archives_already_downloaded_bytes'] = source_bytes
report['total_dependency_payload_bytes'] = report['new_wheel_download_bytes'] + source_bytes
(OUT / 'size-plan.json').write_text(json.dumps(report, indent=2))
print(json.dumps({k: v for k, v in report.items() if k != 'packages'}, indent=2))
print('Packages:', len(rows))

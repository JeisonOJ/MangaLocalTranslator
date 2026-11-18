"""Download <1 MB of CRF archives for passive inspection; execute no package code."""
import hashlib
import io
import json
from pathlib import Path
import struct
import tarfile
import urllib.request
import zipfile
from compression import zstd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'crf-binary-audit'
OUT.mkdir(exist_ok=True)
ARTIFACTS = {
 'conda': ('https://conda.anaconda.org/conda-forge/win-64/pydensecrf-1.0rc3-py312h72972c8_6.conda',
           'aa79604cb4b5513f7dd72c36b29ca5764e2dc7b933027823ea3d0f6b139d9908'),
 'wheel': ('https://github.com/hgmzhn/manga-translator-ui/releases/download/v1.7.6/pydensecrf-1.0-cp312-cp312-win_amd64.whl',
           '8f839df67182fe4d6ae2bf16ad3af9af11723166282014dc691580887a5287c6'),
}


def pe_info(data):
    offset = struct.unpack_from('<I', data, 0x3c)[0]
    machine, sections = struct.unpack_from('<HH', data, offset + 4)
    opt_size = struct.unpack_from('<H', data, offset + 20)[0]
    opt = offset + 24
    magic = struct.unpack_from('<H', data, opt)[0]
    table = opt + (112 if magic == 0x20b else 96)
    sec = opt + opt_size
    def file_offset(rva):
        for i in range(sections):
            s = sec + 40 * i
            size, addr, raw_size, raw = struct.unpack_from('<IIII', data, s + 8)
            if addr <= rva < addr + max(size, raw_size):
                return raw + rva - addr
        raise ValueError(f'Unmapped RVA {rva}')
    def string_at(rva):
        p = file_offset(rva)
        return data[p:data.index(b'\0', p)].decode('ascii', errors='replace')
    imports = []
    rva, size = struct.unpack_from('<II', data, table + 8)
    if rva:
        p = file_offset(rva)
        for _ in range(200):
            values = struct.unpack_from('<IIIII', data, p)
            if not any(values):
                break
            imports.append(string_at(values[3]))
            p += 20
    names = ['DenseCRF2D', 'setUnaryEnergy', 'addPairwiseGaussian', 'addPairwiseBilateral',
             'inference', 'DIAG_KERNEL', 'NO_NORMALIZATION', 'PyArray_API', '_ARRAY_API']
    return {'machine_hex': hex(machine), 'pe32_plus': magic == 0x20b,
            'imported_dlls': imports,
            'string_presence_not_proof_of_exports': {s: s.encode() in data for s in names}}


report = {}
for name, (url, expected) in ARTIFACTS.items():
    request = urllib.request.Request(url, headers={'User-Agent': 'MangaLocalTranslator-passive-audit'})
    with urllib.request.urlopen(request, timeout=45) as response:
        blob = response.read(2_000_000)
    digest = hashlib.sha256(blob).hexdigest()
    if digest != expected:
        raise RuntimeError(f'{name} SHA256 mismatch; stopping')
    archive_name = url.rsplit('/', 1)[-1]
    (OUT / archive_name).write_bytes(blob)
    files = {}
    with zipfile.ZipFile(io.BytesIO(blob)) as archive:
        if name == 'wheel':
            files = {n: archive.read(n) for n in archive.namelist() if not n.endswith('/')}
        else:
            for n in archive.namelist():
                if n.endswith('.tar.zst'):
                    with tarfile.open(fileobj=io.BytesIO(zstd.decompress(archive.read(n))), mode='r:') as tar:
                        for member in tar.getmembers():
                            if member.isfile():
                                files[member.name] = tar.extractfile(member).read()
    entry = {'url': url, 'sha256': digest, 'download_bytes': len(blob),
             'unpacked_file_bytes': sum(map(len, files.values())),
             'files': [{'name': k, 'bytes': len(v), 'sha256': hashlib.sha256(v).hexdigest()} for k, v in files.items()],
             'pe': {k: pe_info(v) for k, v in files.items() if k.endswith(('.pyd', '.dll'))}}
    textdir = OUT / (name + '-texts')
    textdir.mkdir(exist_ok=True)
    for path, data in files.items():
        if path.endswith(('.py', '.yaml', '.json', '.bat', '.patch', 'METADATA', 'WHEEL', 'RECORD')):
            # Save as .txt so neither source nor build hooks are imported or run.
            dest = textdir / (path.replace('/', '__').replace('\\', '__') + '.txt')
            dest.write_text(data.decode('utf-8', errors='replace'), encoding='utf-8')
    report[name] = entry
    print(name, 'hash verified;', len(files), 'files;', entry['unpacked_file_bytes'], 'unpacked bytes')
    print(json.dumps(entry['pe'], indent=2))
(OUT / 'archive-audit.json').write_text(json.dumps(report, indent=2), encoding='utf-8')

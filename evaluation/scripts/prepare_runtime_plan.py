"""Prepare minimal import-compatible upstream requirements and metadata-only size plan."""
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'evaluation/runtime-install'
omit = {
 'imagehash': 'No selected/eager upstream import',
 'kornia': 'Only unselected inpainting_lama.py imports it; selected lama_large uses lama_mpe module',
 'nest-asyncio': 'No selected/eager upstream import',
 'aioshutil': 'Websocket mode only',
 'aiofiles': 'Websocket mode only',
 'torch-summary': 'Unused architecture/debug summary; not selected LaMa implementation',
 'cryptography': 'No direct selected/eager import; allow resolver if required transitively',
 'backports.cached-property': 'No selected/eager import established',
 'tensorboardx': 'Training/logging optional dependency',
 'open-clip-torch': 'Lazy Stable Diffusion encoder, not selected',
 'marshmallow': 'No selected/eager import established',
 'cython': 'Build tool; CRF already binary-installed',
 'accelerate': 'Optional model placement/training; basic NLLB .to(device) does not require it',
 'bitsandbytes': 'Optional quantization for unselected backends',
 'uvicorn': 'Web server, not local evaluation',
 'fastapi': 'Web server, not local evaluation',
 'python-multipart': 'Web upload support, not local evaluation',
}
rows = []
for raw in (ROOT / 'upstream/requirements.txt').read_text().splitlines():
    line = raw.split(' #')[0].strip()
    if not line or line.startswith(('#', '--')):
        continue
    name = line.split('==')[0].lower().replace('_', '-')
    if name.startswith('pydensecrf '):
        continue
    if name in ('torch', 'torchvision'):
        line = line + '+cu130'
    if name not in omit:
        rows.append(line)
rows += ['psutil']  # Upstream local mode imports this but does not list it explicitly.
(OUT / 'requirements-runtime.txt').write_text('\n'.join(rows) + '\n')
(OUT / 'omitted-optionals.json').write_text(json.dumps(omit, indent=2))
(OUT / 'constraints.txt').write_text('numpy==2.5.4\npydensecrf==1.0rc3\ntorch==2.14.1+cu130\ntorchvision==0.29.1+cu130\n')
print('Prepared', len(rows), 'root requirements; CRF remains conda-managed.')

"""Offline import and CUDA availability checks only. No model construction/loading."""
import importlib
import importlib.metadata
import json
import os
from pathlib import Path
import socket
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'evaluation/runtime-install'
for key, value in {
    'HF_HOME': str(ROOT / 'evaluation/cache/huggingface'),
    'HF_HUB_OFFLINE': '1', 'TRANSFORMERS_OFFLINE': '1',
    'TORCH_HOME': str(ROOT / 'evaluation/cache/torch'),
    'PYTHONUTF8': '1', 'DO_NOT_TRACK': '1', 'HF_HUB_DISABLE_TELEMETRY': '1',
}.items():
    os.environ[key] = value
sys.path.insert(0, str(ROOT / 'upstream'))
attempts = []
def deny_network(*args, **kwargs):
    attempts.append(str(args[1:])[:150])
    raise RuntimeError('Network disabled during runtime validation')
socket.socket.connect = deny_network
socket.socket.connect_ex = deny_network
socket.create_connection = deny_network
socket.getaddrinfo = deny_network

report = {'python': sys.version, 'executable': sys.executable,
          'checks': [], 'network_attempts': attempts, 'model_loading': False}
def record():
    (OUT / 'runtime-verification.json').write_text(json.dumps(report, indent=2), encoding='utf-8')

import torch
import torchvision
report['torch'] = torch.__version__
report['torchvision'] = torchvision.__version__
report['torch_cuda_runtime'] = torch.version.cuda
report['cuda_available'] = torch.cuda.is_available()
report['compiled_cuda_architectures'] = torch.cuda.get_arch_list()
if report['cuda_available']:
    properties = torch.cuda.get_device_properties(0)
    report['gpu'] = {'name': properties.name, 'vram_bytes': properties.total_memory,
                     'capability': [properties.major, properties.minor]}
    # Four-byte allocation verifies context/runtime initialization; no model/kernel inference.
    probe = torch.empty(1, device='cuda')
    report['cuda_allocation_succeeded'] = probe.device.type == 'cuda'
    del probe
    torch.cuda.empty_cache()
record()
print('CUDA:', report.get('gpu'), torch.__version__, flush=True)

checks = [
    ('manga_translator', ['MangaTranslator', 'Config']),
    ('manga_translator.detection.default', ['DefaultDetector']),
    ('manga_translator.ocr.model_48px', ['Model48pxOCR']),
    ('manga_translator.translators.nllb', ['NLLBTranslator']),
    ('manga_translator.inpainting.inpainting_lama_mpe', ['LamaLargeInpainter']),
    ('manga_translator.rendering.text_render', ['put_char_horizontal']),
    ('manga_translator.mode.local', ['MangaTranslatorLocal']),
    ('transformers', ['AutoTokenizer', 'AutoModelForSeq2SeqLM']),
    ('transformers.models.m2m_100.modeling_m2m_100', ['M2M100ForConditionalGeneration']),
]
for name, symbols in checks:
    started = time.time()
    try:
        module = importlib.import_module(name)
        for symbol in symbols:
            getattr(module, symbol)
        report['checks'].append({'module': name, 'symbols': symbols, 'passed': True,
                                 'seconds': round(time.time() - started, 3)})
        print('Import passed:', name, flush=True)
    except Exception as exc:
        report['checks'].append({'module': name, 'passed': False, 'error': repr(exc)})
        record()
        raise
    record()
from manga_translator.config import Config
config = Config(**json.loads((ROOT / 'evaluation/configs/local.json').read_text(encoding='utf-8')))
report['selected_config'] = config.model_dump(mode='json')
report['passed'] = report['cuda_available'] and all(x['passed'] for x in report['checks']) and not attempts
record()
print('Runtime checks passed:', report['passed'], flush=True)

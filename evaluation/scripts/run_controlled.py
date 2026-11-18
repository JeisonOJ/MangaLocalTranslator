"""Small evaluation harness for the unmodified upstream pipeline. No downloads."""
import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
EVAL = ROOT / 'evaluation'
os.environ['HF_HOME'] = str(EVAL / 'cache' / 'huggingface')
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'
os.environ['PYTHONUTF8'] = '1'
sys.path.insert(0, str(ROOT / 'upstream'))


def save(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


async def main(args):
    # Imports intentionally occur after argument parsing: --help needs no ML packages.
    import numpy as np
    from PIL import Image
    from manga_translator.utils import ModelWrapper
    from manga_translator.config import Config, Detector, Ocr
    from manga_translator.detection import dispatch as detect
    from manga_translator.ocr import dispatch as recognize
    from manga_translator.translators import get_translator

    ModelWrapper._MODEL_DIR = str(EVAL / 'models')

    async def no_download(self, *a, **kw):
        # Existing files can still load. Missing files fail instead of fetching weights.
        if not self._check_downloaded():
            raise RuntimeError('Missing model files. Downloads require separate approval.')

    ModelWrapper.download = no_download
    out = Path(args.output).resolve()
    out.mkdir(parents=True, exist_ok=False)  # Preserve previous runs.
    started = time.time()
    save(out / 'run.json', {'stage': args.stage, 'device': args.device,
                            'input': str(Path(args.input).resolve()),
                            'sha256': hashlib.sha256(Path(args.input).read_bytes()).hexdigest(),
                            'upstream_commit': '36fed8528d851f8e4cce8e35255e080f4138a8d3'})

    if args.stage == 'A':
        image = np.array(Image.open(args.input).convert('RGB'))
        lines, raw_mask, mask = await detect(
            Detector.default, image, 1536, 0.5, 0.7, 2.3,
            False, False, False, device=args.device)
        # Save detector results before OCR can filter or alter them.
        save(out / 'detected.json', [{'id': i, 'polygon': q.pts.tolist(),
                                      'probability': float(q.prob)} for i, q in enumerate(lines)])
        if raw_mask is not None:
            Image.fromarray(np.clip(raw_mask, 0, 255).astype('uint8')).save(out / 'detector-mask.png')
        lines = await recognize(Ocr.ocr48px, image, lines, device=args.device)
        save(out / 'ocr.json', [{'id': i, 'polygon': q.pts.tolist(), 'text': q.text,
                                 'probability': float(q.prob)} for i, q in enumerate(lines)])
    else:
        # A deliberately local directory, populated separately after download approval.
        model = EVAL / 'models' / 'nllb-600m'
        if not (model / 'config.json').exists():
            raise RuntimeError(f'Missing approved local NLLB snapshot: {model}')
        translator = get_translator('nllb')
        translator._TRANSLATOR_MODEL = str(model)
        translator._check_downloaded = lambda: (model / 'config.json').exists() and any(
            (model / name).exists() for name in ('pytorch_model.bin', 'model.safetensors'))
        translator._downloaded = translator._check_downloaded()
        if args.stage == 'B':
            rows = json.loads(Path(args.input).read_text(encoding='utf-8'))
            await translator.load('JPN', 'ESP', args.device)
            results = []
            for row in rows:
                translated = await translator.translate('JPN', 'ESP', [row['japanese']])
                if len(translated) != 1 or not translated[0].strip():
                    raise RuntimeError(f"Empty or mismatched translation: {row['id']}")
                results.append({**row, 'spanish_machine': translated[0]})
                save(out / 'translations.json', results)
            await translator.unload(args.device)
        else:
            from manga_translator import MangaTranslator
            cfg = Config(**json.loads((EVAL / 'configs' / 'local.json').read_text()))
            pipeline = MangaTranslator({'use_gpu_limited': args.device == 'cuda',
                                        'kernel_size': 3, 'model_dir': str(EVAL / 'models'),
                                        'font_path': str(ROOT / 'upstream/fonts/Arial-Unicode-Regular.ttf'),
                                        'verbose': True})
            ctx = await pipeline.translate(Image.open(args.input).convert('RGB'), cfg)
            save(out / 'regions.json', [{'id': i, 'polygon': r.lines.tolist(),
                                         'japanese_ocr': r.text, 'spanish_machine': r.translation}
                                        for i, r in enumerate(ctx.text_regions)])
            if ctx.result is None:
                raise RuntimeError('Pipeline returned no image')
            ctx.result.save(out / 'translated.png')
    save(out / 'timing.json', {'seconds': time.time() - started})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=['A', 'B', 'C'])
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--device', choices=['cpu', 'cuda'], default='cpu')
    asyncio.run(main(parser.parse_args()))

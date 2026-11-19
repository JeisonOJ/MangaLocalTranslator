"""Page processing using the pinned local Manga Image Translator modules."""
import gc
import os
from pathlib import Path
import re
import sys

from PIL import Image

from .layout import layout
from .translation import TranslationError, translate

ROOT = Path(__file__).resolve().parents[1]
UPSTREAM = ROOT / 'upstream'
MODELS = ROOT / 'evaluation/models'
FONT = UPSTREAM / 'fonts/Arial-Unicode-Regular.ttf'
ASSETS = [FONT, MODELS / 'detection/detect-20241225.ckpt', MODELS / 'ocr/ocr_ar_48px.ckpt',
          MODELS / 'ocr/alphabet-all-v7.txt', MODELS / 'inpainting/lama_large_512px.ckpt']
JAPANESE = re.compile(r'[\u3040-\u30ff\u3400-\u9fff\uff66-\uff9f]')
SFX = re.compile(r'(?:ド{2,}|ゴ{2,}|バキ|ガシャン|ドカン|ドーン)[ッー…!！]*')


def classify(text, outside_balloon):
    if not JAPANESE.search(text):
        return 'no_japanese_recognized'
    if outside_balloon and SFX.fullmatch(''.join(text.split())):
        return 'apparent_artwork_sfx'
    return 'translate'


class RuntimeErrorFatal(Exception):
    pass


class Cancelled(Exception):
    pass


def load_runtime():
    missing = [str(path) for path in ASSETS if not path.is_file()]
    if missing:
        raise RuntimeErrorFatal('Missing local assets: ' + ', '.join(missing))
    os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1')
    sys.path.insert(0, str(UPSTREAM))
    import torch
    from manga_translator.utils import ModelWrapper

    ModelWrapper._MODEL_DIR = str(MODELS)

    async def no_download(self, *args, **kwargs):
        if not self._check_downloaded():
            raise RuntimeErrorFatal('A required local model is missing.')

    ModelWrapper.download = no_download
    if not torch.cuda.is_available():
        raise RuntimeErrorFatal('CUDA is unavailable in the chapter worker.')
    torch.cuda.reset_peak_memory_stats()
    return torch


async def process_page(source, detail, key, persist, stage):
    import cv2
    import numpy as np
    import torch
    from manga_translator import detection, ocr
    from manga_translator.detection import default as detection_default
    from manga_translator.config import Detector, InpainterConfig, Ocr, OcrConfig
    from manga_translator.inpainting.inpainting_lama_mpe import LamaLargeInpainter
    from manga_translator.mask_refinement import dispatch as refine
    from manga_translator.textline_merge import dispatch as merge

    def release():
        gc.collect()
        torch.cuda.empty_cache()

    with Image.open(source) as original:
        rgb = np.array(original.convert('RGB'))
    height, width = rgb.shape[:2]
    stage('Detecting text')
    try:
        lines, raw_mask, _ = await detection.dispatch(
            Detector.default, rgb, 1536, .5, .7, 2.3, False, False, False, device='cuda')
    finally:
        await detection.unload(Detector.default)
        detection_default.MODEL = None
        release()
    detected = [np.asarray(line.pts).copy() for line in lines]
    stage('Recognizing Japanese')
    try:
        lines = await ocr.dispatch(Ocr.ocr48px, rgb, lines,
                                   OcrConfig(ocr='48px', min_text_length=0, ignore_bubble=0), device='cuda')
    finally:
        await ocr.unload(Ocr.ocr48px)
        release()
    blocks = await merge(lines, width, height)
    records = detail['regions']
    warnings = detail['warnings']
    detail['detected_lines'] = len(detected)
    detail['recognized_lines'] = len(lines)
    if len(detected) > len(lines):
        warnings.append('Some detected lines had no usable OCR. Review untranslated marks.')
    eligible = []
    for index, block in enumerate(blocks):
        polygon = np.asarray(block.lines, dtype=np.int32)
        points = polygon.reshape(-1, 2)
        x1, y1 = map(int, np.clip(points.min(axis=0), (0, 0), (width, height)))
        x2, y2 = map(int, np.clip(points.max(axis=0) + 1, (0, 0), (width, height)))
        inset = rgb[y1:y2, x1:x2]
        artwork = bool(inset.size and np.mean(np.min(inset, axis=2) >= 225) < .72)
        kind = classify(block.text, artwork)
        row = {'id': index + 1, 'japanese': block.text, 'polygons': polygon.tolist(), 'status': kind}
        records.append(row)
        if kind != 'translate':
            if kind == 'apparent_artwork_sfx':
                warnings.append(f'Region {row["id"]}: apparent artwork sound effect preserved.')
            continue
        if artwork:
            warnings.append(f'Region {row["id"]}: text over textured/dark background. Review artwork and text.')
        pad_x = min(max(8, (y2 - y1) // 4), 12 if artwork else 40)
        pad_y = min(max(4, (x2 - x1) // 8), 18)
        box = (max(0, x1 - pad_x), max(0, y1 - pad_y), min(width, x2 + pad_x), min(height, y2 + pad_y))
        eligible.append((row, block, polygon, box))

    page = Image.fromarray(rgb)
    if not eligible:
        warnings.append('No Japanese regions eligible for translation. Original appearance preserved.')
        return page
    stage('Translating text (mock)' if key is None else 'Translating Japanese text')
    try:
        spanish = translate([item[0] for item in eligible], key, detail['translation'], persist)
    except TranslationError:
        for row, *_ in eligible:
            row['status'] = 'translation_failed'
        raise
    stage('Preparing Spanish layout and removal masks')
    ready = []
    for (row, block, polygon, box), text in zip(eligible, spanish, strict=True):
        row['spanish'] = text
        try:
            fitted = layout(page, text, box, FONT)
        except (MemoryError, OSError):
            raise
        except Exception as exc:
            row['status'] = 'layout_failed'
            warnings.append(f'Region {row["id"]}: layout failed ({type(exc).__name__}). Source text retained.')
            continue
        if fitted is None:
            row['status'] = 'empty_or_whole_word_fit_failed'
            warnings.append(f'Region {row["id"]}: empty response or text cannot fit. Source text retained.')
            continue
        ready.append((row, block, polygon, box, fitted))
    if not ready:
        return page

    # Restrict removal to OCR geometry, excluding every known untranslated region.
    support = np.zeros((height, width), np.uint8)
    for _, _, polygons, _, _ in ready:
        cv2.fillPoly(support, list(polygons), 255)
    support = cv2.dilate(support, np.ones((7, 7), np.uint8))
    protected = np.zeros_like(support)
    ready_ids = {item[0]['id'] for item in ready}
    for row in records:
        if row['id'] not in ready_ids:
            cv2.fillPoly(protected, [np.asarray(p, np.int32) for p in row['polygons']], 255)
    recognized = {tuple(np.asarray(line.pts).ravel()) for line in lines}
    for poly in detected:
        if tuple(poly.ravel()) not in recognized:
            cv2.fillPoly(protected, [poly.astype(np.int32)], 255)
    protected = cv2.dilate(protected, np.ones((5, 5), np.uint8))
    support[protected != 0] = 0
    try:
        if raw_mask is None:
            raise ValueError('Missing detector mask')
        mask = await refine([item[1] for item in ready], rgb, raw_mask, method='fit_text',
                            dilation_offset=20, ignore_bubble=0, kernel_size=3)
        mask = cv2.bitwise_and(mask, support)
        if not np.any(mask):
            warnings.append('Removal mask was empty. Spanish will overlay the original image.')
        else:
            stage('Inpainting on CUDA')
            model = LamaLargeInpainter()
            try:
                await model._load('cuda')
                cleaned = await model._infer(rgb, mask, InpainterConfig(
                    inpainter='lama_large', inpainting_size=1024, inpainting_precision='fp32'), 1024, False)
                if cleaned.shape != rgb.shape:
                    raise ValueError('Inpainting changed image dimensions')
                cleaned[mask == 0] = rgb[mask == 0]
                page = Image.fromarray(cleaned.astype(np.uint8))
            finally:
                await model._unload()
                del model
                release()
    except (Cancelled, torch.cuda.OutOfMemoryError, RuntimeErrorFatal, MemoryError, OSError):
        raise
    except Exception as exc:
        warnings.append(f'Removal failed ({type(exc).__name__}). Spanish will overlay the original image.')

    stage('Rendering Spanish')
    for row, _, _, box, (ink, size) in ready:
        x1, y1, _, _ = box
        region = np.array(page.crop(box))
        pixels = np.asarray(ink) != 0
        if np.any((np.min(region, axis=2) < 230) & pixels):
            warnings.append(f'Region {row["id"]}: Spanish crosses nonwhite pixels. Review legibility.')
        if size < 14:
            warnings.append(f'Region {row["id"]}: small Spanish text ({size} px).')
        # Preserve detected untranslated regions even if a derived text box crosses them.
        area = protected[y1:box[3], x1:box[2]] != 0
        if np.any(pixels & area):
            ink_pixels = np.array(ink)
            ink_pixels[area] = 0
            ink = Image.fromarray(ink_pixels)
            warnings.append(f'Region {row["id"]}: Spanish ink clipped where it crosses preserved text.')
        page.paste((0, 0, 0), box, ink)
        row.update(status='rendered', font_size=size, box=list(box))
    return page

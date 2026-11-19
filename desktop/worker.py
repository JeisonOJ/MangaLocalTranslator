"""Sequential chapter runner used by both QProcess and the command line."""
import argparse
import asyncio
import errno
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
import threading
import uuid

from PIL import Image, UnidentifiedImageError
import psutil

from .pipeline import Cancelled, RuntimeErrorFatal, load_runtime, process_page
from .translation import TranslationError
from .messages import LOW_MEMORY

FORMATS = {'.jpg': 'JPEG', '.jpeg': 'JPEG', '.png': 'PNG', '.webp': 'WEBP'}
RAM_FLOOR = 500 * 1024**2


def natural_key(path):
    parts = re.split(r'(\d+)', path.name.casefold())
    return tuple((1, int(part)) if part.isdecimal() else (0, part) for part in parts), path.name


def chapter_paths(source, output):
    source = source.resolve(strict=True)
    output = output.resolve()
    if not source.is_dir():
        raise RuntimeErrorFatal('Input must be a chapter folder.')
    if output == source or output.is_relative_to(source) or source.is_relative_to(output):
        raise RuntimeErrorFatal('Choose separate input and output folders that do not contain one another.')
    pages = sorted((p for p in source.iterdir() if p.is_file() and p.suffix.lower() in FORMATS),
                   key=natural_key)
    if not pages:
        raise RuntimeErrorFatal('No JPG, PNG or WebP pages found in the input folder.')
    output.mkdir(parents=True, exist_ok=True)
    return pages, output


def write_page(image, dest):
    # Temporary output is completed and reopened before publishing the final name.
    with tempfile.NamedTemporaryFile(dir=dest.parent, suffix='.tmp', delete=False) as stream:
        temporary = Path(stream.name)
    try:
        image.save(temporary, format=FORMATS[dest.suffix.lower()])
        with Image.open(temporary) as check:
            check.load()
            if check.size != image.size or check.format != FORMATS[dest.suffix.lower()]:
                raise RuntimeErrorFatal('Output image integrity check failed.')
        if os.name == 'nt':
            temporary.rename(dest)  # Windows rename fails if destination already exists.
        else:
            os.link(temporary, dest)
    finally:
        temporary.unlink(missing_ok=True)


def emit(**event):
    print('MANGA_EVENT ' + json.dumps(event, ensure_ascii=True), flush=True)


async def run_chapter(source, output, key, stopped, processor=process_page, event=emit):
    pages, output = chapter_paths(source, output)
    report_path = output / f'.manga-review-{uuid.uuid4().hex}.json'
    report = {'mode': 'google' if key else 'mock', 'pages': [], 'status': 'running', 'total': len(pages)}

    def persist():
        temporary = report_path.with_suffix('.tmp')
        temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        temporary.replace(report_path)

    def check_stop():
        if stopped():
            raise Cancelled()

    persist()
    event(stage='Preparing chapter', total=len(pages), report=str(report_path))
    try:
        for index, source_page in enumerate(pages, 1):
            check_stop()
            detail = {'file': source_page.name, 'status': 'processing', 'regions': [], 'warnings': [],
                      'translation': {'status': 'not_requested', 'attempted_requests': 0, 'characters': 0}}
            report['pages'].append(detail)
            dest = output / source_page.name

            def stage(label):
                check_stop()
                event(stage=label, page=source_page.name, index=index, total=len(pages))

            try:
                if dest.exists() or dest.is_symlink():
                    raise FileExistsError(dest.name)
                if shutil.disk_usage(output).free < max(64 * 1024**2, source_page.stat().st_size * 3):
                    raise RuntimeErrorFatal('Insufficient free space in the output folder.')
                stage('Opening page')
                with Image.open(source_page) as original:
                    original_size = original.size
                translated = await processor(source_page, detail, key, persist, stage)
                if translated.size != original_size:
                    raise RuntimeError('Processor changed page dimensions.')
                stage('Saving page')
                write_page(translated, dest)
                detail['status'] = 'saved_with_review' if detail['warnings'] else 'saved'
            except Cancelled:
                detail['status'] = 'cancelled'
                raise
            except FileExistsError:
                detail.update(status='existing_output', error='Destination already exists; kept as-is.')
            except TranslationError as exc:
                detail.update(status='page_error', error=str(exc))
                if detail['translation'].get('http_status') in (401, 403):
                    raise RuntimeErrorFatal('Google rejected authentication or access. Check the key and project.')
            except (MemoryError, RuntimeErrorFatal) as exc:
                detail.update(status='fatal', error=str(exc) if isinstance(exc, RuntimeErrorFatal) else LOW_MEMORY)
                raise
            except OSError as exc:
                if isinstance(exc, UnidentifiedImageError) or exc.errno is None:
                    detail.update(status='page_error', error=f'Image or I/O error ({type(exc).__name__}).')
                elif exc.errno in (errno.ENOSPC, errno.EACCES, errno.EROFS):
                    detail.update(status='fatal', error=f'Output I/O failure (errno {exc.errno}).')
                    raise
                else:
                    detail.update(status='page_error', error=f'I/O error ({type(exc).__name__}).')
            except Exception as exc:
                if 'OutOfMemory' in type(exc).__name__ or isinstance(exc, (ImportError, ModuleNotFoundError)):
                    message = LOW_MEMORY if 'OutOfMemory' in type(exc).__name__ else f'Runtime failure ({type(exc).__name__}).'
                    detail.update(status='fatal', error=message)
                    raise RuntimeErrorFatal(message) from None
                detail.update(status='page_error', error=f'Processing error ({type(exc).__name__}).')
            finally:
                persist()
                event(stage=detail['status'], page=source_page.name, index=index, total=len(pages),
                      completed=index if detail['status'] not in ('cancelled', 'fatal') else index - 1,
                      warning_count=len(detail['warnings']), error=detail.get('error', ''))
        report['status'] = 'finished'
    except Cancelled:
        report['status'] = 'stopped'
    except Exception:
        report['status'] = 'fatal'
        raise
    finally:
        persist()
    event(stage=report['status'], total=len(pages), report=str(report_path))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--google', action='store_true', help='Authorize text-only billable Google requests for this run')
    parser.add_argument('--stop-file', type=Path)
    args = parser.parse_args()
    key = None
    if args.google:
        key = os.environ.get('MANGA_GOOGLE_TRANSLATE_API_KEY', '').strip()
        if not key:
            emit(stage='fatal', error='MANGA_GOOGLE_TRANSLATE_API_KEY is missing from the process environment.')
            return 1
    else:
        def offline(event, values):
            if event == 'socket.connect':
                address = values[1]
                if isinstance(address, tuple) and address[0] in ('127.0.0.1', '::1'):
                    return
                raise RuntimeErrorFatal('External network access is disabled in mock mode.')

        sys.addaudithook(offline)

    def monitor():
        while not finished.wait(.1):
            if psutil.virtual_memory().available < RAM_FLOOR:
                emit(stage='fatal', error=LOW_MEMORY)
                os._exit(70)

    finished = threading.Event()
    threading.Thread(target=monitor, daemon=True).start()
    try:
        torch = load_runtime()
        asyncio.run(run_chapter(args.input, args.output, key,
                                lambda: args.stop_file is not None and args.stop_file.exists()))
        emit(peak_gpu_reserved_mib=round(torch.cuda.max_memory_reserved() / 1024**2, 1))
    except Exception as exc:
        message = LOW_MEMORY if isinstance(exc, MemoryError) or 'OutOfMemory' in type(exc).__name__ else str(exc) if isinstance(exc, RuntimeErrorFatal) else type(exc).__name__
        emit(stage='fatal', error=message)
        return 1
    finally:
        finished.set()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

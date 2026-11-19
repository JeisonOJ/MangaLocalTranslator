import asyncio
from io import BytesIO
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
from urllib.error import HTTPError

from PIL import Image

from desktop.pipeline import RuntimeErrorFatal, classify
from desktop.translation import TranslationError, translate
from desktop.worker import chapter_paths, run_chapter


class ChapterTest(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.source = self.root / 'chapter'
        self.source.mkdir()
        self.output = self.root / 'spanish'
        for filename in ('10.jpg', '2.webp', '1.png'):
            Image.new('RGB', (80, 120), 'white').save(self.source / filename)

    async def process(self, path, detail, key, persist, stage):
        stage('mock rendering')
        if path.name == '2.webp':
            detail['warnings'].append('Inspect artwork.')
        return Image.new('RGB', (80, 120), 'black')

    def run_job(self, processor=None, stop=lambda: False, event=lambda **_: None):
        return asyncio.run(run_chapter(self.source, self.output, None, stop,
                                       processor or self.process, event))

    def test_order_formats_and_sources_preserved(self):
        originals = {p.name: p.read_bytes() for p in self.source.iterdir()}
        result = self.run_job()
        self.assertEqual([p['file'] for p in result['pages']], ['1.png', '2.webp', '10.jpg'])
        self.assertEqual(result['pages'][1]['status'], 'saved_with_review')
        for name, expected in [('1.png', 'PNG'), ('2.webp', 'WEBP'), ('10.jpg', 'JPEG')]:
            with Image.open(self.output / name) as image:
                image.load()
                self.assertEqual((image.format, image.size), (expected, (80, 120)))
            self.assertEqual((self.source / name).read_bytes(), originals[name])

    def test_reject_overlapping_folders(self):
        for output in (self.source, self.source / 'nested', self.source.parent):
            with self.subTest(output=output), self.assertRaises(RuntimeErrorFatal):
                chapter_paths(self.source, output)
        self.assertFalse((self.source / 'nested').exists())

    def test_existing_output_and_recoverable_corrupt_page(self):
        self.output.mkdir()
        existing = self.output / '1.png'
        existing.write_bytes(b'existing')
        (self.source / '2.webp').write_bytes(b'invalid')
        result = self.run_job()
        self.assertEqual([p['status'] for p in result['pages']], ['existing_output', 'page_error', 'saved'])
        self.assertEqual(existing.read_bytes(), b'existing')
        self.assertFalse((self.output / '2.webp').exists())

    def test_cooperative_stop_preserves_completed_page(self):
        stop = False

        def event(**data):
            nonlocal stop
            if data.get('stage') == 'mock rendering' and data.get('index') == 2:
                stop = True

        result = self.run_job(stop=lambda: stop, event=event)
        self.assertEqual(result['status'], 'stopped')
        self.assertEqual([p['status'] for p in result['pages']], ['saved', 'cancelled'])
        self.assertTrue((self.output / '1.png').is_file())
        self.assertFalse((self.output / '2.webp').exists())

    def test_fatal_disk_space_stops_without_processing_pages(self):
        with patch('desktop.worker.shutil.disk_usage', return_value=Mock(free=0)):
            with self.assertRaisesRegex(RuntimeErrorFatal, 'free space'):
                self.run_job()
        report = json.loads(next(self.output.glob('*.json')).read_text(encoding='utf-8'))
        self.assertEqual(report['status'], 'fatal')
        self.assertEqual(len(report['pages']), 1)

    def test_wrong_dimensions_never_publish(self):
        async def invalid(*args):
            return Image.new('RGB', (12, 12))

        result = self.run_job(processor=invalid)
        self.assertTrue(all(p['status'] == 'page_error' for p in result['pages']))
        self.assertFalse(any(self.output.glob('*.png')))


class TranslationTest(unittest.TestCase):
    regions = [{'id': 2, 'japanese': '日本語', 'polygons': [[1, 2]]},
               {'id': 5, 'japanese': 'こんにちは', 'polygons': [[3, 4]]}]

    def test_mock_does_not_open_network(self):
        with patch('desktop.translation.urllib.request.build_opener') as opener:
            audit = {}
            self.assertEqual(len(translate(self.regions, None, audit, Mock())), 2)
            opener.assert_not_called()
            self.assertEqual(audit, {'status': 'mock_no_request', 'characters': 8})

    def test_google_body_is_text_only_and_response_order_is_retained(self):
        response = BytesIO(b'{"data":{"translations":[{"translatedText":"uno"},{"translatedText":"dos &amp; tres"}]}}')
        response.status = 200
        with patch('desktop.translation.urllib.request.build_opener') as factory:
            opener = factory.return_value
            opener.open.return_value = response
            audit, checkpoint = {}, []
            self.assertEqual(translate(self.regions, 'test-key', audit, lambda: checkpoint.append(audit.copy())),
                             ['uno', 'dos & tres'])
            request = opener.open.call_args.args[0]
            self.assertEqual(json.loads(request.data), {'q': ['日本語', 'こんにちは'], 'source': 'ja',
                                                       'target': 'es', 'format': 'text', 'model': 'nmt'})
            self.assertEqual(checkpoint[0]['status'], 'reserved_before_dispatch')
            self.assertEqual(audit['exact_responses'], ['uno', 'dos &amp; tres'])

    def test_ambiguous_failure_is_never_retried(self):
        for error in (TimeoutError('private'), HTTPError('https://example.invalid', 403, 'private', {}, None)):
            with self.subTest(error=type(error).__name__), patch('desktop.translation.urllib.request.build_opener') as factory:
                factory.return_value.open.side_effect = error
                audit = {}
                with self.assertRaises(TranslationError) as raised:
                    translate(self.regions, 'test-key', audit, Mock())
                factory.return_value.open.assert_called_once()
                self.assertEqual(audit['attempted_requests'], 1)
                self.assertNotIn('private', str(raised.exception))

    def test_artwork_and_shouts_are_not_rejected_by_background_alone(self):
        self.assertEqual(classify('背景の文章', True), 'translate')
        self.assertEqual(classify('うおおっ', True), 'translate')
        self.assertEqual(classify('ドドド', True), 'apparent_artwork_sfx')
        self.assertEqual(classify('ドドド', False), 'translate')

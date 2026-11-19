import asyncio
import ctypes
import json
import os
from pathlib import Path
import runpy
import tempfile
import unittest
from unittest.mock import Mock, patch

from PIL import Image
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtWidgets import QApplication
from desktop import credentials
from desktop.gui import Window
from desktop.messages import LOW_MEMORY
from desktop.paths import output_chapter
from desktop.worker import run_chapter


class WindowsWorkflowTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'Mangas' / 'nue no onmyouji' / 'Capítulo 01'
        self.source.mkdir(parents=True)
        Image.new('RGB', (40, 60)).save(self.source / '0001.png')
        self.base = self.root / 'Mangas' / 'Mangas Español'

    def test_construct_and_reuse_folders_preserve_case(self):
        expected = self.base / 'nue no onmyouji' / 'Capítulo 01'
        self.assertEqual(output_chapter(self.source, self.base), expected)
        self.assertFalse(expected.exists())
        expected.mkdir(parents=True)
        existing = expected / '0001.png'
        existing.write_bytes(b'completed')

        async def must_not_run(*args):
            self.fail('Existing page should be retained')

        report = asyncio.run(run_chapter(self.source, output_chapter(self.source, self.base), None,
                                         lambda: False, must_not_run, lambda **_: None))
        self.assertEqual(existing.read_bytes(), b'completed')
        self.assertEqual(report['pages'][0]['status'], 'existing_output')

    def test_unsafe_paths(self):
        for base in (self.source, self.source / 'output', self.source.parent.parent):
            with self.subTest(base=base), self.assertRaises(ValueError):
                output_chapter(self.source, base)
        self.assertEqual(output_chapter(self.source.parent, self.base),
                         self.base / 'Mangas' / 'nue no onmyouji')
        base_file = self.root / 'file'
        base_file.touch()
        with self.assertRaises(ValueError):
            output_chapter(self.source, base_file)
        with self.assertRaises(ValueError):
            output_chapter(base_file, self.base)
        with self.assertRaises(OSError):
            output_chapter(self.root / 'missing', self.base)

    def test_ordinary_and_unconventional_names_create_and_reuse_folders(self):
        for name in ('Capítulo 01', 'bonus', '番外編', 'Finale - RAW (Extra)', 'no numbers here', 'MiXeD Case & accents á'):
            with self.subTest(name=name):
                source = self.root / 'Title As Selected á' / name
                source.mkdir(parents=True)
                Image.new('RGB', (40, 60)).save(source / '0001.png')
                expected = self.base / source.parent.name / name
                expected.parent.mkdir(parents=True, exist_ok=True)
                self.assertEqual(output_chapter(source, self.base), expected)

                async def processor(*args):
                    return Image.new('RGB', (40, 60), 'white')

                asyncio.run(run_chapter(source, expected, None, lambda: False,
                                        processor, lambda **_: None))
                self.assertTrue((expected / '0001.png').is_file())
                original_output = (expected / '0001.png').read_bytes()
                result = asyncio.run(run_chapter(source, expected, None, lambda: False,
                                                 processor, lambda **_: None))
                self.assertEqual(result['pages'][0]['status'], 'existing_output')
                self.assertEqual((expected / '0001.png').read_bytes(), original_output)

    def test_gui_preview_and_low_memory_message(self):
        with patch('desktop.gui.credentials.available_key', return_value='mock-secret'):
            window = Window()
        self.addCleanup(window.close)
        window.source.setText(str(self.source))
        window.output.setText(str(self.base))
        self.assertEqual(window.resolved.text(), str(output_chapter(self.source, self.base)))
        with patch.object(window.process, 'start') as launch:
            window.start()
            self.assertEqual(launch.call_args.args[1][5], str(output_chapter(self.source, self.base)))
        window.saved = 1
        window.finished(70, None)
        self.assertEqual(window.stage.text(), LOW_MEMORY)
        self.assertIn('Close memory-heavy applications', window.summary.toPlainText())
        self.assertIn('1 saved', window.summary.toPlainText())
        self.assertNotIn('mock-secret', window.key_status.text())
        self.assertFalse(window.google.isChecked())

    def test_memory_failure_keeps_completed_page(self):
        Image.new('RGB', (40, 60)).save(self.source / '0002.png')

        async def processor(path, *args):
            if path.stem == '0002':
                raise MemoryError()
            return Image.new('RGB', (40, 60))

        output = output_chapter(self.source, self.base)
        with self.assertRaises(MemoryError):
            asyncio.run(run_chapter(self.source, output, None, lambda: False, processor, lambda **_: None))
        self.assertTrue((output / '0001.png').exists())
        self.assertFalse((output / '0002.png').exists())
        report = json.loads(next(output.glob('*.json')).read_text(encoding='utf-8'))
        self.assertEqual(report['pages'][1]['error'], LOW_MEMORY)

    def test_launcher_resolves_its_own_root_from_other_directory(self):
        launcher = Path(__file__).resolve().parents[1] / 'launch.pyw'
        previous = Path.cwd()
        try:
            os.chdir(self.root)
            namespace = runpy.run_path(str(launcher))
            self.assertEqual(namespace['ROOT'], launcher.parents[1])
            with patch('desktop.gui.main', return_value=0) as entry:
                self.assertEqual(namespace['main'](), 0)
                entry.assert_called_once()
        finally:
            os.chdir(previous)
        script = (launcher.parents[1] / 'MangaLocalTranslator.vbs').read_text()
        self.assertIn('WScript.ScriptFullName', script)
        self.assertIn('pythonw.exe', script)
        self.assertIn('shell.CurrentDirectory = root', script)
        self.assertIn('entry & Chr(34), 1, False', script)
        self.assertNotIn('entry & Chr(34), 0, False', script)
        self.assertNotIn('mock-secret', script)


class CredentialTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_native_write_read_delete_using_mock_storage(self):
        dll = Mock()
        stored = {}

        def write(pointer, flags):
            item = ctypes.cast(pointer, ctypes.POINTER(credentials.Credential)).contents
            stored['value'] = ctypes.string_at(item.CredentialBlob, item.CredentialBlobSize)
            self.assertEqual(item.TargetName, credentials.TARGET)
            self.assertEqual(item.Persist, 2)
            return True

        buffer = (ctypes.c_ubyte * len('dummy-key'.encode('utf-16-le'))).from_buffer_copy('dummy-key'.encode('utf-16-le'))
        item = credentials.Credential(CredentialBlob=buffer, CredentialBlobSize=len(buffer))

        def read(target, kind, flags, destination):
            ctypes.cast(destination, ctypes.POINTER(ctypes.POINTER(credentials.Credential)))[0] = ctypes.pointer(item)
            return True

        dll.CredWriteW.side_effect = write
        dll.CredReadW.side_effect = read
        with patch('desktop.credentials.api', return_value=dll):
            credentials.write_key('dummy-key')
            self.assertEqual(stored['value'].decode('utf-16-le'), 'dummy-key')
            self.assertEqual(credentials.read_key(), 'dummy-key')
            dll.CredFree.assert_called_once()
            credentials.delete_key()
            dll.CredDeleteW.assert_called_once_with(credentials.TARGET, 1, 0)
            credentials.write_key('replacement')
            self.assertEqual(stored['value'].decode('utf-16-le'), 'replacement')

    def test_environment_precedence_and_missing_credentials(self):
        with patch.dict(os.environ, {'MANGA_GOOGLE_TRANSLATE_API_KEY': 'environment-key'}), patch('desktop.credentials.read_key') as read:
            self.assertEqual(credentials.available_key(), 'environment-key')
            read.assert_not_called()
        with patch.dict(os.environ, {'MANGA_GOOGLE_TRANSLATE_API_KEY': ''}), patch('desktop.credentials.read_key', return_value='saved-key'):
            self.assertEqual(credentials.available_key(), 'saved-key')
        dll = Mock()
        dll.CredReadW.return_value = False
        dll.CredDeleteW.return_value = False
        with patch('desktop.credentials.api', return_value=dll), patch('ctypes.get_last_error', return_value=1168):
            self.assertEqual(credentials.read_key(), '')
            credentials.delete_key()

    def test_configuration_cancel_delete_and_replace_without_showing_key(self):
        with patch('desktop.gui.credentials.available_key', return_value='dummy'):
            window = Window()
        try:
            with patch('desktop.gui.QInputDialog.getItem', return_value=('', False)), patch('desktop.gui.credentials.write_key') as write:
                window.configure_key()
                write.assert_not_called()
            with patch('desktop.gui.QInputDialog.getItem', return_value=('Enter or replace saved key', True)), patch('desktop.gui.QInputDialog.getText', return_value=('replacement', True)), patch('desktop.gui.credentials.write_key') as write, patch('desktop.gui.credentials.available_key', return_value='replacement'):
                window.configure_key()
                write.assert_called_once_with('replacement')
                self.assertNotIn('replacement', window.key_status.text())
            with patch('desktop.gui.QInputDialog.getItem', return_value=('Delete saved key', True)), patch('desktop.gui.credentials.delete_key') as delete, patch('desktop.gui.credentials.available_key', return_value=''):
                window.configure_key()
                delete.assert_called_once()
                self.assertEqual(window.api_key, '')
        finally:
            window.close()

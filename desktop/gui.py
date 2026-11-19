"""One PySide6 Widgets window supervising the existing Python runtime."""
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from .paths import output_chapter
from .messages import LOW_MEMORY
from . import credentials

from PySide6.QtCore import QProcess, QProcessEnvironment, Qt
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QFileDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit,
    QPlainTextEdit, QProgressBar, QPushButton, QVBoxLayout, QWidget, QInputDialog,
)

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / 'evaluation/envs/crf312/python.exe'


class Window(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('MangaLocalTranslator')
        self.resize(670, 390)
        self.process = QProcess(self)
        self.process.setWorkingDirectory(str(ROOT))
        self.process.readyReadStandardOutput.connect(self.read_events)
        self.process.readyReadStandardError.connect(self.process.readAllStandardError)
        self.process.finished.connect(self.finished)
        self.process.errorOccurred.connect(self.process_error)
        self.buffer = bytearray()
        self.temp = None
        self.saved = self.errors = self.review = 0
        self.memory_failed = False
        self.api_key = ''
        self.credential_error = ''
        try:
            self.api_key = credentials.available_key()
        except OSError as exc:
            self.credential_error = str(exc)

        form = QFormLayout()
        self.source = self.folder_row(form, 'Input chapter folder')
        self.output = self.folder_row(form, 'Output base folder')
        self.resolved = QLabel('Select input chapter and output base folders.')
        self.resolved.setWordWrap(True)
        self.resolved.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        form.addRow('Output chapter', self.resolved)
        self.source.textChanged.connect(self.update_destination)
        self.output.textChanged.connect(self.update_destination)
        self.google = QCheckBox('Use Google Cloud Translation (billable, sends Japanese text)')
        self.key_button = QPushButton('Configure Google API Key')
        self.key_button.clicked.connect(self.configure_key)
        self.key_status = QLabel()
        self.update_key_status()
        self.progress = QProgressBar()
        self.stage = QLabel('Ready. Mock mode uses Spanish test text.')
        self.stage.setWordWrap(True)
        self.summary = QPlainTextEdit(readOnly=True)
        self.summary.setMaximumBlockCount(100)
        self.start_button = QPushButton('Start')
        self.stop_button = QPushButton('Stop', enabled=False)
        self.start_button.clicked.connect(self.start)
        self.stop_button.clicked.connect(self.stop)
        buttons = QHBoxLayout()
        buttons.addWidget(self.start_button)
        buttons.addWidget(self.stop_button)
        body = QVBoxLayout(self)
        body.addLayout(form)
        body.addWidget(self.google)
        body.addWidget(self.key_button)
        body.addWidget(self.key_status)
        body.addLayout(buttons)
        body.addWidget(self.progress)
        body.addWidget(self.stage)
        body.addWidget(self.summary)

    def update_key_status(self):
        self.key_status.setText(self.credential_error or ('Google API key available.' if self.api_key else 'Google API key has not been configured.'))

    def configure_key(self):
        action, accepted = QInputDialog.getItem(self, 'Google API Key', 'Action',
                                               ['Enter or replace saved key', 'Delete saved key'], 0, False)
        if not accepted:
            return
        try:
            if action == 'Delete saved key':
                credentials.delete_key()
            else:
                value, accepted = QInputDialog.getText(self, 'Google API Key', 'New key', QLineEdit.EchoMode.Password)
                if not accepted:
                    return
                credentials.write_key(value)
                value = ''
            self.api_key = credentials.available_key()
            self.credential_error = ''
        except (OSError, ValueError) as exc:
            self.credential_error = str(exc)
        self.update_key_status()

    def folder_row(self, form, label):
        field = QLineEdit()
        button = QPushButton('Browse…')

        def choose():
            path = QFileDialog.getExistingDirectory(self, label, field.text())
            if path:
                field.setText(path)

        button.clicked.connect(choose)
        row = QHBoxLayout()
        row.addWidget(field)
        row.addWidget(button)
        form.addRow(label, row)
        return field

    def update_destination(self):
        if not self.source.text().strip() or not self.output.text().strip():
            self.resolved.setText('Select input chapter and output base folders.')
            return
        try:
            self.resolved.setText(str(output_chapter(self.source.text().strip(), self.output.text().strip())))
        except (OSError, ValueError) as exc:
            self.resolved.setText(str(exc))

    def start(self):
        if self.process.state() != QProcess.ProcessState.NotRunning:
            return
        source, output = self.source.text().strip(), self.output.text().strip()
        if not source or not output:
            self.stage.setText('Select an input chapter folder and output base folder.')
            return
        try:
            output = str(output_chapter(source, output))
        except (OSError, ValueError) as exc:
            self.stage.setText(str(exc))
            return
        if not RUNTIME.is_file():
            self.stage.setText('The project-local Python ML runtime is missing.')
            return
        environment = QProcessEnvironment.systemEnvironment()
        live = self.google.isChecked()
        if live and not self.api_key:
            self.stage.setText('Configure a Google API key before starting a Google job.')
            return
        if live:
            environment.insert('MANGA_GOOGLE_TRANSLATE_API_KEY', self.api_key)
        if not live:
            environment.remove('MANGA_GOOGLE_TRANSLATE_API_KEY')
        self.process.setProcessEnvironment(environment)
        self.temp = TemporaryDirectory(prefix='manga-stop-')
        self.stop_file = Path(self.temp.name) / 'stop'
        args = ['-B', '-u', '-m', 'desktop.worker', source, output, '--stop-file', str(self.stop_file)]
        if live:
            args.append('--google')
        self.summary.clear()
        self.buffer.clear()
        self.saved = self.errors = self.review = 0
        self.memory_failed = False
        self.progress.setRange(0, 0)
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.google.setEnabled(False)
        self.key_button.setEnabled(False)
        self.stage.setText('Starting Google chapter job…' if live else 'Starting offline mock chapter job…')
        self.process.start(str(RUNTIME), args)

    def stop(self):
        if self.temp is not None:
            try:
                self.stop_file.touch()
            except OSError:
                self.summary.appendPlainText('Could not signal the worker to stop.')
                return
            self.stop_button.setEnabled(False)
            self.stage.setText('Stopping at the next processing checkpoint…')

    def read_events(self):
        self.buffer.extend(bytes(self.process.readAllStandardOutput()))
        while b'\n' in self.buffer:
            line, _, tail = self.buffer.partition(b'\n')
            self.buffer = tail
            if not line.startswith(b'MANGA_EVENT '):
                continue
            try:
                data = json.loads(line[len(b'MANGA_EVENT '):])
            except ValueError:
                continue
            total, index = data.get('total'), data.get('index')
            if total:
                self.progress.setRange(0, total)
            if 'completed' in data:
                self.progress.setValue(data['completed'])
            stage = data.get('stage')
            if stage:
                prefix = f'{index}/{total} · {data["page"]} · ' if index else ''
                self.stage.setText(prefix + stage.replace('_', ' '))
            if data.get('error'):
                if data['error'] == LOW_MEMORY:
                    self.memory_failed = True
                self.errors += 1
                self.summary.appendPlainText(f'{data.get("page", "Worker")}: {data["error"]}')
            if data.get('warning_count'):
                self.review += 1
                self.summary.appendPlainText(f'{data["page"]}: {data["warning_count"]} review flags')
            if stage in ('saved', 'saved_with_review'):
                self.saved += 1
            if data.get('report'):
                self.summary.appendPlainText(f'Review report: {data["report"]}')

    def finished(self, code, _exit_status):
        self.read_events()
        self.summary.appendPlainText(f'{self.saved} saved · {self.review} pages flagged · {self.errors} errors/skips')
        if code == 70 or self.memory_failed:
            self.stage.setText(LOW_MEMORY)
            self.summary.appendPlainText(LOW_MEMORY)
        elif code:
            self.stage.setText(f'Worker stopped with exit code {code}. See summary.')
        if self.progress.maximum() == 0:
            self.progress.setRange(0, 1)
        if self.temp is not None:
            self.temp.cleanup()
            self.temp = None
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.google.setEnabled(True)
        self.key_button.setEnabled(True)

    def process_error(self, error):
        if error == QProcess.ProcessError.FailedToStart:
            self.finished(1, None)
            self.summary.appendPlainText('Could not start the project-local Python worker.')

    def closeEvent(self, event):
        if self.process.state() != QProcess.ProcessState.NotRunning:
            self.stop()
            event.ignore()
        else:
            event.accept()


def main():
    app = QApplication(sys.argv)
    window = Window()
    window.show()
    return app.exec()


if __name__ == '__main__':
    raise SystemExit(main())

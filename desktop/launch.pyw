"""Entry point used by the console-free Windows launcher."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    sys.path.insert(0, str(ROOT))
    from desktop.gui import main as run_gui
    return run_gui()


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as exc:
        import ctypes
        import traceback
        # Show location metadata only, excluding exception values, source and locals.
        locations = '\n'.join(f'{Path(frame.filename).name}, line {frame.lineno}, {frame.name}'
                              for frame in traceback.extract_tb(exc.__traceback__)[-4:])
        ctypes.windll.user32.MessageBoxW(
            None, f'MangaLocalTranslator could not start ({type(exc).__name__}).\n'
            f'Python: {sys.executable}\nProject: {ROOT}\n{locations}\n'
            'Try the project-local Python command from the launch guide to diagnose the failure.',
            'MangaLocalTranslator', 16)

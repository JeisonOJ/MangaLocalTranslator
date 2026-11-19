# Windows chapter translator

Run from the project root in PowerShell.

```powershell
& .\evaluation\envs\crf312\python.exe -B -m desktop.gui
```

The project-local environment uses PySide6 Essentials and Shiboken 6.10.1 for Qt Widgets. The worker uses the existing CUDA Python environment, detector, OCR, alphabet, LaMa Large checkpoint and upstream font. A missing model is reported instead of downloaded. The GUI runs one worker through QProcess.

Select the folder containing a chapter's JPG, PNG or WebP images. Select an output **base** folder, such as `Mangas Español`. The GUI derives `<base>\<manga folder>\<chapter folder>` from the selected chapter and its parent, and previews the resolved destination before Start. For example, input `nue no onmyouji\Capítulo 01` produces `Mangas Español\nue no onmyouji\Capítulo 01`. The worker reads input images in place in natural filename order. It saves pages under the original names and formats. Existing destinations are skipped and recorded. Output folders inside the input directory, containing the input directory, or pointing to the same directory are rejected. Page files are decoded and checked before publication. JPEG and WebP are re-encoded. Transparent and animated inputs are flattened to a single RGB page.

Start with the Google checkbox cleared. Mock mode runs the real local image stages and uses `Texto de prueba.` to exercise layout. The output is a reconstruction preview. It cannot evaluate translation quality. Stop waits for the active stage to finish or fail before stopping at a checkpoint. Completed pages remain saved. A per-run `.manga-review-*.json` in the output folder records OCR, region mappings, responses, review flags and page status.

## Double-click launch and desktop shortcut

Double-click `C:\Dev\Codex\MangaLocalTranslator\MangaLocalTranslator.vbs`. It resolves its own project directory and starts `evaluation\envs\crf312\pythonw.exe` with `desktop\launch.pyw`. The GUI opens without a persistent console. Keep the VBS file in the project root. The launcher reads its location independently of the current working directory.

For a desktop shortcut, right-click the Desktop, choose New → Shortcut, and enter the following target (including quotes):

```
wscript.exe "C:\Dev\Codex\MangaLocalTranslator\MangaLocalTranslator.vbs"
```

Name the shortcut **MangaLocalTranslator**. No Start in directory is required. The shortcut references the existing runtime and models in place. If Windows policy disables VBScript/Windows Script Host, create a shortcut with this target instead:

```
"C:\Dev\Codex\MangaLocalTranslator\evaluation\envs\crf312\pythonw.exe" -B "C:\Dev\Codex\MangaLocalTranslator\desktop\launch.pyw"
```

## One-time Google API key setup

Open **Configure Google API Key**, choose **Enter or replace saved key**, and enter the key in the masked prompt. The application stores it with the native Windows Credential Manager API in the current Windows user's generic credentials under `MangaLocalTranslator/GoogleCloudTranslation`. Loading the key on future launches is local. The saved key is never filled into the prompt or displayed in full.

The same action offers **Delete saved key**. A nonempty inherited `MANGA_GOOGLE_TRANSLATE_API_KEY` takes precedence over the saved credential. Deleting the saved credential leaves that environment override available, and replacing a saved key takes effect when the environment override is absent. The VBS and shortcut contain only paths. A shell-only environment variable is available to programs launched from that shell; the Credential Manager setup supports normal desktop launching across sessions.

Choose the input chapter and output base, verify the displayed resolved path, check **Use Google Cloud Translation**, and click Start to explicitly authorize a real job. Mock mode remains the default. Key configuration itself performs no Google request. Use a fresh output base for real results if you previously generated mock previews, since existing output pages are kept.

The selected input directory is the chapter folder, and its immediate parent supplies the manga folder name. Any folder naming convention is accepted. Names and capitalization are retained. Existing manga/chapter folders are reused; missing folders are created by the worker after validation. Overlapping source/output paths and output junctions escaping the selected base are rejected.

Insufficient-memory messages advise closing memory-heavy applications and starting again when memory is available. Completed pages are kept, and the 500 MiB available-RAM guard remains active. Cancellation and memory stops do not automatically retry requests or pages.

The worker attempts every OCR region containing Japanese, including artwork text, with no OCR confidence threshold. A narrow sound-effect rule preserves a small set of recognizable isolated effects over textured backgrounds. This rule and the detector can miss stylized effects or confuse them with other text. Derived text boxes can cross balloon borders or adjacent artwork. Inpainting can leave halos, furigana, Japanese glyphs or damaged screentone. Review flags capture some geometric and background issues. They do not identify every visual or semantic defect. Failed Google pages have no fabricated output. A failed region layout leaves its source text visible.

## Local validation

```powershell
& .\evaluation\envs\crf312\python.exe -B -m unittest discover -s desktop/tests -v
```

Eighteen automated tests cover launch-path resolution, automatic chapter paths, mocked Credential Manager operations, low-memory reporting, and natural order, output separation, file preservation, existing outputs, cancellation, recoverable and fatal failures, output decoding and dimensions, region order and text-only payloads, mock isolation and review flags. An offscreen Qt run exercised the GUI and real CUDA worker with the preserved page-5 and page-11 inputs. Both JPEGs were written at 1403 × 2048 and reviewed. Page 5 rendered six regions with one flag. Page 11 rendered five regions with seven flags. Japanese remnants and localized artwork defects remain visible. A full-chapter live Google test is pending.

### W3.1 launcher visibility correction

The VBS launcher now uses normal window style (1) for pythonw.exe. Window style 0 asked Windows to hide the GUI process's initial window. pythonw.exe itself provides console-free startup. The launcher also sets the project root as the working directory, matching the working PowerShell command. The existing desktop/launch.pyw entry imports and calls desktop.gui.main.

Startup errors display the exception type, Python executable, project path and traceback location metadata. Exception values, source lines, local variables and API keys are excluded. Windows process-start failures display a numeric error code.

After updating, close the previous hidden application instance if it is still running, then double-click the project-root VBS file or the shortcut pointing to it. Confirm that the window appears on the desktop, check folder controls, close it, and repeat from a desktop shortcut with an unrelated Start in directory. GUI visibility through Windows Script Host still needs this manual validation. The offline tests verify launcher command construction and the GUI entry point from another working directory.

# Phase 1 evaluation — inspection complete, execution pending approval

**ML runtime installed:** [ML-RUNTIME-STATUS.md](ML-RUNTIME-STATUS.md) records successful selected-pipeline imports, CUDA detection/allocation, and preservation of CRF/NumPy. All selected model weights remain deferred. Earlier sections describe the initial inspection.

**Latest:** [COMPILER-FREE-RESULT.md](COMPILER-FREE-RESULT.md) records a successful small Python 3.12/NumPy/CRF binary validation. No compiler or upstream modification was needed. The rest of the ML stack and all model weights remain uninstalled; earlier status paragraphs below describe the initial inspection.

**Update after download approval:** see [INSTALLATION-STATUS.md](INSTALLATION-STATUS.md). Models are approved, but installation is paused at the confirmed native C++ build requirement under the user's explicit stop condition. No weights or project dependencies have been installed. The dependency download estimate is approximately 2.6–3.0 GB, separate from the selected models.

Inspected 2026-11-15. No translation-quality verdict is possible yet: no user manga samples, model weights, or ML dependencies have been installed. No upstream files were changed, and no commits or pushes were made. The evaluation harness is test tooling, not an application.

## Upstream provenance and structure

- Official origin: https://github.com/zyddnys/manga-image-translator.git
- Exact commit: `36fed8528d851f8e4cce8e35255e080f4138a8d3`
- Commit date: 2026-11-10, message: `fix(docker): restore release image builds`
- Full clone in `../upstream`, with 2,045 reachable commits; no shallow clone.
- Main pipeline: `manga_translator/manga_translator.py`; configuration and CLI: `config.py`, `args.py`, `__main__.py`.
- Separate `detection`, `ocr`, `translators`, `mask_refinement`, `inpainting`, `rendering`, `upscaling`, and `colorization` packages.
- `mode/local.py` provides batch operation. `server`, `front`, and `MangaStudio*` are outside this evaluation.
- `fonts`, `examples`, `test`, `training`, and `devscripts` contain supporting assets/code. Upstream sample images are not treated as an authorized evaluation corpus.

## Component selection: capability versus evidence

First candidate: **default detector + 48px OCR + NLLB distilled 600M + LaMa Large + default horizontal renderer**. Configuration is in `configs/local.json`. This selection balances a direct Japanese-to-Spanish route with modest model size; it is not a demonstrated quality ranking.

Confirmed in the inspected source:

- OCR keys: `32px`, `48px`, `48px_ctc`, `mocr`. README recommends 48px for Japanese. Start there, without extra Manga OCR downloads.
- `mocr` uses `kha-white/manga-ocr-base` in addition to the 48px checkpoint. It is a later OCR comparison candidate, not part of the first download.
- NLLB maps `JPN` to `jpn_Jpan` and `ESP` to `spa_Latn`; uses beam search with 5 beams, truncation at 512 input tokens, and a 512 output-token limit. It can return empty strings after caught inference errors. Treat those as failures.
- `nllb_big` is the 1.3B alternative. It is deferred until the 600M text-only test shows whether this family is useful.
- `m2m100_hf` (418M) and its 1.2B variant support Japanese and Spanish via PyTorch. CTranslate2 M2M100 variants are also present but add runtime-library compatibility considerations.
- Sugoi and JParaCrawl expose Japanese/English pairs, not direct Spanish. An English pivot adds another error source, so it is not the first test.
- `offline` is an automatic selector that can choose the larger M2M100 model. Avoid it to keep downloads predictable.
- MBart50 is another local implementation. Qwen backends are not selected or evaluated.
- `--use-gpu-limited` puts offline translation on CPU while image stages use GPU. It is **not** proof that every model is sequentially unloaded.
- LaMa Large is a roughly 205 MB checkpoint. Start at 1024 inpainting size and FP32; assess detail loss before raising resolution. Stable Diffusion, upscaling, and colorization are unnecessary for the initial test.

Unconfirmed: Japanese manga OCR accuracy, colloquial Spanish quality, complete balloon/SFX coverage, peak RAM/VRAM, CUDA execution, and artifact-free typesetting on this PC. Short Japanese fragments can be misclassified by the end-to-end translator's automatic language detection; the text-only test explicitly forces Japanese.

## Actual machine findings

See `environment.json` for the recorded snapshot.

| Item | Observed |
|---|---|
| OS | Windows 11, build 26200, 64 bit |
| CPU | AMD Ryzen 5 5600X, 12 logical processors |
| RAM | 15.91 GiB usable physical; only 4.95 GiB available at inspection |
| GPU | NVIDIA RTX 3050, 8,192 MiB VRAM; 1,460 MiB already used |
| Driver | NVIDIA 621.14; NVIDIA-SMI reports CUDA UMD 13.5 |
| Python found | CPython 3.14.7, 64 bit, per-user installation |
| Python launcher | `py` absent from PATH |
| Tools | Git 2.51.0.windows.1; no `uv`, `conda`, `nvcc`, `cmake`, or `cl` found on PATH |
| Build tools | `vswhere.exe` not found at the standard Installer path; a compiler elsewhere is not ruled out |
| C: free | approximately 346.5 GiB at environment snapshot |

NVIDIA-SMI's CUDA number describes driver support; it does not establish that the CUDA toolkit, cuDNN, or a CUDA-enabled PyTorch is installed. None has been functionally verified. PyTorch wheels supply much of their runtime; do not install a system CUDA toolkit preemptively.

The models look plausible for this GPU when separated by stage. NLLB FP32 weights alone are about 2.3 GiB; generation, activations, loading copies, Python, and image processing require more. With only 4.95 GiB RAM free, CPU translation is currently a material memory risk. Close other memory-heavy programs before testing. CPU offloading trades VRAM use for RAM use. One page and one translation segment per call should be the initial workload. No fit or throughput guarantee is established.

## Environment and dependency status

Created `.venv-probe` at the workspace root using existing Python 3.14.7. Its Python and pip execute successfully. It contains only the venv bootstrap pip; **no project dependencies installed**. Global Python/CUDA/driver installations are unchanged.

Upstream requires Python >=3.12 and warns that newest Python may be incompatible. PyPI metadata confirms a CPython 3.14 Windows wheel exists for pinned torch 2.14.1; this alone does not validate the complete stack or CUDA. Transformers 5.19.0 metadata was also checked. Metadata is saved in `metadata.json`; no weights were retrieved.

Installation pause reasons:

1. Mandatory `pydensecrf` is imported by mask refinement and pinned to a Git source branch; README requires Microsoft C++ Build Tools on Windows. No usable compiler was established. Installing Build Tools would be a significant system change and is not authorized yet.
2. The Python package eagerly imports the full pipeline, including unselected backend modules. A tiny hand-selected install cannot be assumed to work. Upstream requirements include many API clients, server libraries and optional models; installing the entire list would exceed a minimal first evaluation. API-client imports do not authorize any remote translation calls.
3. CLI local mode imports `psutil` directly, but it is not explicitly listed in requirements; transitive availability is not assured.
4. NLLB `_download` uses a backend cache directory, while `_load` calls `from_pretrained` without that cache directory. Snapshot download exclusions also do not explicitly prevent multiple weight formats. A bare upstream run could fetch into two caches. The test harness instead selects a single prepopulated local model directory and enables HF offline mode, without modifying upstream.

Recommended next step, after approval: resolve wheels/compiler support first, using an isolated Python 3.13 environment if needed. Prefer a workspace-local runtime over changing global Python. Produce a dependency resolution and download-size plan before fetching the CUDA stack. Do not silently bypass CRF, downgrade pins, or switch commits: those would change what is being evaluated.

## Downloads: proposed, not performed

Sizes below come from official upstream release metadata / model repository file metadata, stored in `metadata.json`. Decimal MB/GB are used. Tokenizers/configs are additional.

| Selected asset | Bytes | Approximate size | Purpose |
|---|---:|---:|---|
| `detect-20241225.ckpt` | 308,380,176 | 308 MB | Find text polygons |
| `ocr_ar_48px.ckpt` | 204,290,192 | 204 MB | Japanese OCR |
| `alphabet-all-v7.txt` | 186,651 | 0.19 MB | OCR alphabet |
| NLLB `pytorch_model.bin` | 2,460,457,927 | 2.46 GB | Direct local Japanese-to-Spanish |
| NLLB tokenizer/config files | about 22,188,377 | 22 MB | Required model/tokenizer metadata |
| `lama_large_512px.ckpt` | 204,544,673 | 205 MB | Text erasure/inpainting |
| **Selected total** | **about 3.20 billion** | **3.20 GB / 2.98 GiB** | Excludes dependencies and caches |

Download origins are the exact URLs in upstream `_MODEL_MAPPING` for detector/OCR/LaMa, and `facebook/nllb-200-distilled-600M` on Hugging Face. Preserve upstream SHA256 checks for release checkpoints. Pin NLLB snapshot revision `f8d333a098d19b4fd9a8b18f94170487ad3f821d` and download only required config/tokenizer files plus one weight format into `evaluation/models/nllb-600m`.

LaMa model metadata revision: `2953a4e935bf01ad1471f6cbfd26ab81abeeb92d`.

Not approved or selected: Manga OCR additional weights 444 MB; M2M100 HF 418M weights 1.94 GB; NLLB 1.3B, larger M2M100, and any generative/VL model. No need to fetch all alternatives.

Allow a provisional **10–15 GB working-space budget** for one CUDA stack, models, environment, and temporary package files; this is a planning allowance, not a measured dependency download size. The exact CUDA-wheel plan remains unresolved. No large package installation should proceed before that is reported.

## Controlled tests and exact commands

Request 3–5 user-authorized pages, ideally with vertical dialogue, small text/furigana, stylized text/SFX, negation, pronouns, names, and patterned backgrounds. Place originals in `evaluation/samples/originals`. Do not alter originals. No suitable user samples existed in this initially empty workspace.

Create a manually checked manifest for each page: image SHA256, balloon/line IDs, reading order, reference polygons in original-image pixels, exact Japanese transcription, acceptable Spanish meaning, and uncertain readings. Keep dialogue, captions, SFX, and furigana categories separate. The five authored sentences in `known-japanese.json` are sanity fixtures, not manga-quality evidence or exhaustive references.

**Commands below are prepared for after dependency/model approval and setup. They are not currently runnable inference tests.** The harness only passed syntax compilation and `--help`; its ML paths remain unexecuted.

From PowerShell:

```powershell
Set-Location C:\Dev\Codex\MangaLocalTranslator
# Confirm provenance before each evaluation series.
git -C upstream rev-parse HEAD
# Replace this path with the approved runtime environment if it changes.
$evalPython = 'C:\Dev\Codex\MangaLocalTranslator\.venv-probe\Scripts\python.exe'

# A: detection and OCR only; no translation/inpainting weights needed.
& $evalPython evaluation\scripts\run_controlled.py A --input evaluation\samples\originals\page01.png --output evaluation\results\A-page01-run01 --device cuda

# B: translation only, with correct Japanese and forced JPN -> ESP; no images/OCR.
& $evalPython evaluation\scripts\run_controlled.py B --input evaluation\known-japanese.json --output evaluation\results\B-smoke-run01 --device cpu
# Repeat B with manually verified page transcriptions in the same JSON schema.
& $evalPython evaluation\scripts\run_controlled.py B --input evaluation\samples\page01-text.json --output evaluation\results\B-page01-run01 --device cpu

# C: upstream end-to-end pipeline; GPU image stages and CPU translation.
& $evalPython evaluation\scripts\run_controlled.py C --input evaluation\samples\originals\page01.png --output evaluation\results\C-page01-run01 --device cuda
```

The runner enables offline HF loading, redirects the model to a local directory, and refuses model downloads through ModelWrapper. It is not an OS-level network sandbox: test the fully populated setup with outbound network blocked/disconnected to establish offline operation. Upstream dotenv loading and eagerly imported modules remain present. Do not configure API credentials or remote translators. Save raw exceptions/logs and `pip freeze` alongside each validated run. Partial output directories indicate an interrupted/failed test and must not be counted as successes.

Evaluation rules:

- **A:** `detected.json` captures polygons before OCR filtering; `ocr.json` captures text and remaining polygons. Manually match these to ground truth. Report detection precision/recall at polygon IoU >=0.5, missed balloons, false positives, split/merged regions, reading-order errors, and Japanese character error rate (CER). Report raw CER and a separately declared whitespace-only normalized CER; do not normalize away kanji, punctuation, numbers, or negation. Unmatched ground-truth text counts as missing in page completeness. Add a manual-crop OCR follow-up if A fails: it distinguishes detector/crop failure from recognition failure.
- **B:** A competent Japanese/Spanish reviewer grades each segment for meaning, omissions/additions, negation, entities/numbers, speaker reference, tone, and fluency. Use a declared 0–4 adequacy scale (0 wrong/missing; 4 complete and faithful), with separate critical-error flags. References permit valid alternatives. Inspect individual cases; neither similarity metrics nor average scores alone prove quality. The harness uses one segment per call to reduce padding/memory pressure. It preserves Japanese inputs and produced Spanish side by side.
- **C:** Compare `regions.json` against both A and B, retaining source/translation alignment. Examine the translated image, verbose masks/intermediates, text coverage, original-art damage, residual Japanese, clipping/overflow, reading order, and Spanish diacritics (`áéíóúüñ¿¡`). If B passes but C fails, identify the earliest differing OCR/segmentation input before attributing failure to translation. To isolate reconstruction further, rerun upstream rendering/inpainting with manually verified region text after the first outputs establish region correspondence; this control remains to be validated, not silently automated.
- Provisional acceptance gate to agree before scoring: all dialogue balloons found; no critical negation/entity/number reversal or invented clause; most segments adequate (>=3/4); all failures explicitly counted. A tiny sample cannot establish broad reliability. Repeat failures on a second page set before a proceed/stop decision.

Do not use upstream `--save-text` as an OCR ground-truth export: at this commit it saves translated sentences and exits with `-1`, rather than exporting raw OCR plus geometry. The harness supplies those records separately.

## License implications from local upstream texts and model metadata

Upstream `pyproject.toml` declares **GPL-3.0-only**; `LICENSE` contains GPLv3. Private local evaluation/modification does not itself require publishing code. If a derivative is conveyed to others, GPL obligations include preserving applicable notices and providing Corresponding Source under GPL for the covered work, with the license and required installation information where applicable. Distribution/combined-work boundaries need review before adapting or shipping a final product. GPLv3 itself does not impose AGPL-style source disclosure solely for network use.

Model/data/font licenses are separate. NLLB metadata declares **CC-BY-NC-4.0**, so this proposed evaluation model is not a clean choice for future commercial use. M2M100 HF metadata declares MIT, Manga OCR Apache-2.0, and the official LaMa code repository Apache-2.0 (the fine-tuned checkpoint card separately declares MIT); these labels do not replace checking individual downloaded artifacts and bundled assets. No final application's licensing suitability has been decided.

## Disk use and readiness

Measured logical file sizes before this report: upstream including `.git` **193,837,866 bytes (184.86 MiB)**; `.venv-probe` **12,351,808 bytes (11.78 MiB)**; evaluation metadata/tooling about 0.2 MiB before this report. Final totals are recorded separately in `disk-usage.json`. Filesystem allocation and preexisting system Python are not included. Model download use: **0 bytes**. Project dependency installation use: **0 bytes**, excluding bundled venv pip.

Ready to receive samples and manual references: **yes**. Ready to execute local manga evaluation: **no**. Awaiting approval for the approximately 3.20 GB selected models plus a separately resolved dependency/runtime plan, and resolution of the Windows compiler/Python compatibility question. Translation fidelity and complete offline operation remain untested.

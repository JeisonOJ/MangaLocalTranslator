# Local ML runtime installed — ready for selected model installation

Date: 2026-11-15. Upstream remains unchanged at `36fed8528d851f8e4cce8e35255e080f4138a8d3`.

The runtime required to import the selected default detector, 48px OCR, NLLB translator, LaMa Large inpainter and horizontal renderer is installed in the existing project-local Python 3.12 environment. CUDA detection and a minimal allocation passed on the RTX 3050. CRF and NumPy compatibility survived installation.

No selected model weights were downloaded, instantiated or loaded. No manga inference or translation was run. No compiler, global Python, system CUDA, NVIDIA driver, persistent PATH or Windows registry changes were made. No upstream source edits, commits or pushes.

## Environment and exact versions

Interpreter:

```text
C:\Dev\Codex\MangaLocalTranslator\evaluation\envs\crf312\python.exe
Python 3.12.16, conda-forge, 64 bit
```

| Component | Installed version |
|---|---|
| PyTorch | 2.14.1+cu130 |
| torchvision | 0.29.1+cu130 |
| Bundled CUDA runtime | 13.0 |
| NumPy | 2.5.4, existing conda-forge installation preserved |
| PyDenseCRF | 1.0rc3, conda-forge build py312h72972c8_6 preserved |
| transformers | 5.19.0 |
| huggingface_hub | 2.2.0 |
| sentencepiece | 0.2.2 |
| safetensors | 0.8.0 |
| OpenCV | 5.0.0.93 |
| Pillow | 13.0.0 |
| scikit-image | 0.26.0 |
| SciPy | 1.18.1 |
| timm | 1.0.30 |
| onnxruntime | 1.31.0 |
| PyHyphen | 4.0.4 |
| freetype-py | 2.5.1 |
| psutil | 7.2.2 |

There are **118 installed Python distributions**, including the existing environment's Python packages. This turn added **112 resolved distributions**. Exact versions are in `runtime-install/installed-packages.json` and `installed-freeze.txt`. Exact artifact URLs, hashes and wheel contents are in `size-plan.json`; the offline installation requirements are in `requirements-resolved.lock`.

## Dependency selection and provenance

The input overlay, `runtime-install/requirements-runtime.txt`, retains the applicable upstream pins and adds `psutil`, imported by upstream local mode but not explicitly listed upstream. A constraints file preserves NumPy 2.5.4 and CRF 1.0rc3, and selects CUDA-specific torch/torchvision versions. Upstream's CRF Git requirement was not installed.

PyTorch/torchvision came from the official CUDA 13.0 PyTorch wheel index. Other artifacts came from PyPI or ancillary official PyTorch-index entries. An ancillary Jinja2 index entry lacked a published hash, so its identical-version PyPI artifact was selected and hash-verified instead. No extra Rust wheel index was needed: the pinned native package is published on PyPI.

Unrelated training/server/quantization dependencies were omitted, including TensorBoardX, torch-summary, Cython, bitsandbytes, accelerate, open-clip-torch, FastAPI, uvicorn and multipart uploads. Additional omitted entries and reasons are recorded in `omitted-optionals.json`. Some libraries for unselected backends remain necessary because upstream imports their modules eagerly; these include Manga OCR, Rust detector support, CTranslate2, pandas/ONNX Runtime, and translation SDKs. These dependencies were installed for import compatibility. No remote translator was configured or called.

Two dependencies are published only as source archives: `langdetect==1.0.9` and `unidic-lite==1.0.8`. Their official PyPI archive hashes and setup files were inspected. Both were built locally as pure Python/data wheels, without build isolation, additional build packages, or a native compiler. Their hashes are in the final lock. UniDic Lite is dictionary data required by the eagerly imported Manga OCR package's declared dependencies; no Manga OCR recognition model was obtained or initialized.

All 112 wheels passed SHA256 checks before installation. Installation ran offline from the workspace wheelhouse with hashes enforced, source builds disallowed, and bytecode precompilation disabled. Build temporary files and pip caches were redirected into the project.

## Estimated versus actual space

Before installation, pip resolved the complete package set. Artifact HTTP headers and ZIP central-directory byte ranges provided download and unpacked-size measurements without prematurely downloading the large wheels.

| Quantity | Size |
|---|---:|
| Remaining wheel downloads | 2,409,109,341 bytes |
| Two source archives obtained for local wheel builds | 48,338,220 bytes |
| Total dependency payload this turn, excluding small metadata/range requests | **2,457,447,561 bytes / 2.46 GB** |
| Uncompressed contents of resolved wheels | 4,267,307,478 bytes |
| Pre-install installed-environment estimate | 4.5–5.5 GB |
| Actual complete environment after checks | **4,579,519,313 bytes / 4.58 GB / 4.27 GiB** |
| Runtime wheelhouse, source archives, pip cache and records | 2,573,924,569 bytes / 2.57 GB |
| Existing conda package/index cache | 267,889,731 bytes / 0.27 GB |
| Entire workspace including clone, previous probe/audits and caches | **7,655,740,474 bytes / 7.66 GB / 7.13 GiB** |
| C: free after installation | approximately 337.7 GiB |

Logical file sizes are reported; filesystem allocation differs. Small report additions follow this snapshot. The download and installed environment sizes were below the previously approved upper bounds of 3.0 GB and 9 GB. Retaining the wheelhouse allows offline reproduction and accounts for most non-environment disk use. No cleanup was required to fit the allowance. Details: `runtime-install/disk-usage-final.json`.

## Verification completed

`runtime-install/runtime-verification.json` records successful checks with HF offline settings, project cache paths, and Python socket connections/DNS blocked. There were **zero attempted Python-network connections**. No model preparation/download methods or constructors were called. This was an import/CUDA check, not an end-to-end offline inference certification.

Passed imports:

- Main `manga_translator` package and configuration class.
- Default detector and 48px OCR implementation classes.
- NLLB translator, `AutoTokenizer`, `AutoModelForSeq2SeqLM`, and `M2M100ForConditionalGeneration` class used by the NLLB model family.
- LaMa Large implementation.
- Default text renderer and local batch mode.
- Selected JSON configuration parsed successfully: Spanish target `ESP`, NLLB, horizontal rendering, 1024-pixel FP32 LaMa inpainting, no upscaling/colorization.

CUDA findings:

- RTX 3050 detected, compute capability **8.6**.
- Driver **621.14**, unchanged.
- PyTorch's bundled CUDA runtime is **13.0**; compiled architecture list includes **sm_86**.
- CUDA context initialization and a four-byte allocation succeeded; the allocation was released.
- Driver reports 8,192 MiB total VRAM and about 6,504 MiB free after verification. PyTorch reports 8,589,279,232 available physical bytes for the device; these interfaces round/report memory differently.
- No model execution or numerical CUDA-kernel benchmark was performed.

Integrity/consistency findings:

- `pip check`: **No broken requirements found**.
- CRF native module SHA256s exactly match their pre-install hashes.
- NumPy remains **2.5.4**.
- The existing synthetic CRF API test passed again with the same output hash. No renewed CRF provenance investigation was needed.
- `git status --porcelain` is empty. Import-created ignored Python bytecode caches are generated files, not upstream source edits.

## Warnings and limits

Upstream emits an experimental-Python-version warning recommending its Rust rewrite. This is recorded in `runtime-install/verify.log`; this evaluation remains on the requested pinned Python pipeline. The first full package import took about 62 seconds on this machine, although subsequent component imports in the same process were immediate. This is import timing, not page-processing speed.

Pip warned that console scripts are outside PATH. No PATH change is needed: invoke the environment's full `python.exe` path and `python -m ...`.

The selected model checkpoint/tokenizer loading paths have not yet been exercised. Runtime import success does not establish translation accuracy, checkpoint loading success, mask reconstruction quality, or model peak memory use.

For future memory planning, start with one page and one translation segment, image stages on GPU, and offline translation on CPU using upstream's `use_gpu_limited` behavior. This keeps approximately 2.4 GB of NLLB FP32 parameters off the GPU, at the cost of system RAM. Image checkpoint sizes total roughly 0.7 GB; activations and page resolution can require substantially more memory. With the prior roughly 5 GiB free system RAM snapshot, close memory-heavy programs before loading models. These are planning estimates, not measured model footprints. Sequential unloading remains to be validated in the actual evaluation harness; `use_gpu_limited` does not guarantee it.

## Reproducible commands and next step

To repeat only runtime/CRF checks, without loading models:

```powershell
Set-Location C:\Dev\Codex\MangaLocalTranslator
.\evaluation\envs\crf312\python.exe -I -m pip check
.\evaluation\envs\crf312\python.exe -I evaluation\scripts\validate_crf_api.py
.\evaluation\envs\crf312\python.exe -I evaluation\scripts\verify_ml_runtime.py
```

For future reproduction, first recreate the frozen conda base as documented in `COMPILER-FREE-RESULT.md`, then install the additions offline into that prefix:

```powershell
# Use the target recreated environment's python.exe path if it differs.
.\evaluation\envs\crf312\python.exe -I -m pip --isolated --disable-pip-version-check install --no-index --no-cache-dir --no-compile --only-binary=:all: --find-links evaluation\runtime-install\wheelhouse --require-hashes -c evaluation\runtime-install\constraints.txt -r evaluation\runtime-install\requirements-resolved.lock
```

**No current runtime blocker remains for proceeding to selected model installation.** Next, obtain explicit permission to resume the deferred approximately 3.20 GB model download, retain the previously selected revision/hashes and local model paths, then check model loading one stage at a time. Continue to defer manga inference/translation until user samples are provided and the user authorizes testing. The current task stops here without downloading model weights.

# Controlled installation status — 2026-11-15

**Current runtime status:** [ML-RUNTIME-STATUS.md](ML-RUNTIME-STATUS.md). The remaining selected ML runtime is installed, CUDA checks passed, and no model weights were downloaded. Older pause details below are historical.

**Latest result:** [COMPILER-FREE-RESULT.md](COMPILER-FREE-RESULT.md). A small project-local Python 3.12/NumPy 2.5.4/conda-forge CRF environment is now installed and passed a synthetic API compatibility check. No models or large ML dependencies are installed. Earlier pause details below describe the prior state.

**Follow-up investigation:** [CRF-FINDINGS.md](CRF-FINDINGS.md) distinguishes the import blocker from CRF's actual mask-refinement role and identifies prebuilt alternatives. Build Tools are a source-build route, not the only possible evaluation route. No changes or installations have been made.

**Paused before package installation or model downloads because the unchanged upstream requires a native C++ build.** The user approved the selected model downloads, but explicitly required stopping if a compiler installation is necessary. No inference was run, including the authored sentence fixtures.

## Dependency size audit

Inspected metadata and HTTP headers only. No wheel bodies, model weights, compiler installers, or additional Python runtime were downloaded. Audit scripts and responses are in `dependency-plan/`.

Target for a conservative continuation: **project-local Python 3.12 x64**, separate from global Python 3.14. The existing 3.14 probe venv remains unchanged. A standalone 3.12 runtime would still have to be selected and sized before obtaining it.

| Item | Approximate download |
|---|---:|
| 60 available direct upstream dependency wheels for CPython 3.12, using PyPI torch/torchvision | 519.89 MB |
| Replace PyPI torch (124.11 MB) with official `torch-2.14.1+cu130` Windows wheel (1,990.61 MB) | +1,866.49 MB |
| Replace PyPI torchvision (1.38 MB) with matching official `torchvision-0.29.1+cu130` wheel (6.57 MB) | +5.19 MB |
| Available wheels for 77 additional transitive packages | 83.76 MB |
| `unidic-lite` source archive (Japanese dictionary; no wheel) | 47.36 MB |
| **Metadata-based subtotal** | **2.523 GB** |

This is a planning estimate for the broad upstream requirement set, not an instruction to install every optional component. Eager pipeline imports prevent assuming that only selected backend dependencies suffice. A real resolver/import check could reduce or alter the set. This metadata traversal found no version-specifier conflicts, but it is not equivalent to a pip resolver: it does not validate native builds, all Python-version restrictions, dynamic build dependencies, or runtime ABI compatibility.

The subtotal excludes the CRF Git source, source-build tools/dependencies, `langdetect` source archive, standalone Python, and additional installer overhead. Allow approximately **2.6–3.0 GB of dependency/runtime downloads** and **6–9 GB installed dependency/runtime space** as an intentionally conservative, unmeasured expansion allowance. Installing directly from a retained project wheelhouse would require approximately **9–12 GB temporary dependency/runtime space**. Compiler/Windows SDK installations are separate and have not been sized or authorized.

Together with the already approved selected models (about **3.20 GB**), allow about **9–12 GB persistent project space**, or **12–16 GB while retaining installation archives**. Available disk capacity is sufficient based on the earlier roughly 346 GiB free snapshot. These estimates do not justify silently adding unrelated optional model weights.

## Confirmed blocking dependency

Upstream pins:

```text
pydensecrf @ git+https://github.com/zyddnys/pydensecrf.git@fix/python313-cython3
```

The source dependency's `setup.py` invokes Cython on `pydensecrf/eigen.pyx` and `pydensecrf/densecrf.pyx` to create native extensions. Its `pyproject.toml` requires setuptools, wheel, and Cython >=3.1,<4 for the build. Source text is saved in `dependency-plan/pydensecrf-setup.py` and `pydensecrf-pyproject.toml`.

`manga_translator/mask_refinement/text_mask_utils.py` imports both `pydensecrf.utils` and `pydensecrf.densecrf`. The pipeline imports mask refinement eagerly. This cannot conservatively be skipped while claiming an evaluation of the unmodified pipeline. A wheel from another fork/version would be a dependency substitution requiring explicit discussion and validation, not a transparent equivalent of the pinned Git source.

No `cl`, `clang`, `clang-cl`, `gcc`, `g++`, or `cmake` was found on PATH, no active Visual Studio build environment was found, and neither standard Visual Studio installation directory was present. An installation at a nonstandard location cannot be ruled out. Upstream's documented Windows path is Microsoft C++ Build Tools. No attempt was made to install it or trigger a known-to-fail source build.

Python 3.14 also has no matching wheel for pinned `editdistance==0.8.1`; Python 3.12 does. Both targets lack a wheel for `langdetect==1.0.9`; lack of a wheel alone does not establish a native compiler requirement. Switching to 3.12 would reduce compatibility risk but **would not remove the CRF C++ build**.

## GPU findings

- NVIDIA RTX 3050, driver 621.14, 8,192 MiB total VRAM.
- Latest status snapshot: 1,507 MiB used, 6,536 MiB free.
- Official CUDA 13.0 Windows CPython 3.12 wheels exist for the exact torch/torchvision versions pinned by upstream; their URLs and sizes are saved in `dependency-plan/`.
- The installed driver reports CUDA UMD 13.5. That makes a CUDA 13.0 wheel a plausible candidate; it is not proof of execution compatibility.
- No CUDA-enabled torch import, GPU allocation, or model execution was performed. No system CUDA toolkit/driver changes are proposed.
- Only about 5 GiB system RAM was free in the earlier snapshot. Close memory-heavy programs before future evaluation. CPU translation saves VRAM but consumes RAM; it is not automatically safe on the current memory snapshot.
- Sequential stage execution/unloading remains required work for the evaluation harness once installation is possible. The current C runner uses upstream `use_gpu_limited` (CPU translation, GPU image stages), which does not guarantee stage-by-stage unloading. Do not describe it as an implemented sequential execution strategy.

## Installed components and actual disk usage

No new runtime, project package, model, compiler, CUDA toolkit, or driver was installed this turn. The only isolated environment is the existing `.venv-probe`, created with global Python 3.14.7, containing only **pip 26.2.1**. Global Python packages were not modified.

Measured logical file size immediately before this status report:

| Directory | Bytes | MiB |
|---|---:|---:|
| `upstream` including `.git` | 193,837,866 | 184.86 |
| `.venv-probe` | 12,351,808 | 11.78 |
| `evaluation` audit files and tooling | approximately 375,000 | 0.36 |

Final measured totals are in `dependency-plan/disk-usage-final.json`; logical sizes exclude filesystem allocation overhead. Newly downloaded **model weights: 0 bytes**. Newly installed **project dependencies: 0 bytes**. Network transfers this turn were package/model-installation planning metadata and source build instructions only.

## Model destinations after the blocker is resolved

These are intended paths, not existing downloaded files:

```text
C:\Dev\Codex\MangaLocalTranslator\evaluation\models\detection\detect-20241225.ckpt
C:\Dev\Codex\MangaLocalTranslator\evaluation\models\ocr\ocr_ar_48px.ckpt
C:\Dev\Codex\MangaLocalTranslator\evaluation\models\ocr\alphabet-all-v7.txt
C:\Dev\Codex\MangaLocalTranslator\evaluation\models\inpainting\lama_large_512px.ckpt
C:\Dev\Codex\MangaLocalTranslator\evaluation\models\nllb-600m\
```

The selected manifest and NLLB revision remain as recorded in `README.md`. No alternate OCR/translation/inpainting model was added. User approval covers approximately 3.20 GB for this selection; a budget check must precede downloads, including tokenizer/config files. A single model snapshot and one weight format should be retained.

## Next decision

The compiler requirement prevents a complete conservative installation of the unchanged upstream. Separate permission is needed for a system-level Microsoft C++ Build Tools installation, with its minimal component selection and download/disk estimate reviewed before installation. No compiler installation is authorized by the existing model/dependency approval.

Upstream remains unchanged at `36fed8528d851f8e4cce8e35255e080f4138a8d3`; no commits or pushes. Ready to receive user samples: yes. Ready for inference: no. Even after installation, wait for the user's manga samples before any inference.

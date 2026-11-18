# Is pydensecrf necessary for this evaluation?

Investigation date: 2026-11-15. Upstream examined: `36fed8528d851f8e4cce8e35255e080f4138a8d3`.

**Recommendation: do not install Microsoft C++ Build Tools yet.** CRF is required for the selected end-to-end pipeline's normal mask refinement, but not for detection/OCR or Japanese-to-Spanish translation computations. Omitting it from the current unmodified Python environment nevertheless breaks imports. A small import-only change could unblock A/B without changing those computations; a compatible binary could preserve CRF for C without a local compiler. Neither approach has been implemented or validated here.

The previous installation report overstated the conclusion if read as saying that Build Tools are the only viable route. They are needed for the specified native source-build route on this PC, not inherently for OCR/translation or for using a precompiled CRF implementation.

No compilers, dependencies, runtimes, or models installed. No binaries downloaded, no inference, no upstream edits, no commits or pushes. Investigation writes are confined to this project's evaluation directory. The only external application-repository item inspected was metadata for a CRF dependency wheel hosted as a release asset; no other application's source code or local files were inspected.

## 1. Exact imports and runtime use

AST inventory of upstream Python files found exactly two direct imports, both in `manga_translator/mask_refinement/text_mask_utils.py`:

| Lines | Code/use |
|---|---|
| 68 | `from pydensecrf.utils import compute_unary, unary_from_softmax` |
| 69 | `import pydensecrf.densecrf as dcrf` |
| 71–93 | `refine_mask`: construct two-class unary potentials, DenseCRF2D, Gaussian and color-sensitive bilateral pairwise terms; run five CRF iterations; convert labels to an erasure mask |
| 78 | `unary_from_softmax` is used |
| 81–91 | `DenseCRF2D`, `DIAG_KERNEL`, `NO_NORMALIZATION`, `setUnaryEnergy`, `addPairwiseGaussian`, `addPairwiseBilateral`, `inference(5)` are used |
| 184 | `complete_mask` calls `refine_mask` on each nonempty candidate crop before dilation |

`compute_unary` is imported but unused in this repository. Removing only that unused name does not solve the dependency requirement.

Import chain:

```text
import manga_translator[.any_submodule]
 -> manga_translator/__init__.py:7 imports .manga_translator
 -> manga_translator.py:34 imports .mask_refinement.dispatch
 -> mask_refinement/__init__.py:5 imports .text_mask_utils
 -> text_mask_utils.py:68–69 imports pydensecrf
```

Consequently, normal submodule imports also fail if the dependency is absent. The existing evaluation runner imports this package and currently encounters the same issue. Omitting the requirements line alone will not make A/B runnable.

Normal selected end-to-end call path:

```text
default detector -> (textlines, raw_mask, None)
OCR -> region merge -> translation
ctx.mask is None
 -> manga_translator.py:565 mask-generation branch
 -> _run_mask_refinement at 1356–1358, hardcoded method 'fit_text'
 -> mask_refinement.dispatch at __init__.py:24
 -> complete_mask
 -> refine_mask at text_mask_utils.py:184
 -> pydensecrf
 -> refined mask -> LaMa -> Spanish rendering
```

The default detector explicitly returns `None` as its third return value (`detection/default.py:103`), so its raw mask is normally refined here. A second batch-processing path at `manga_translator.py:2507` has the same `ctx.mask is None` gate and calls the same refinement method. CRF is skipped for crops with no valid connected components, pages with no text, or other early exits; those are not a basis for declaring the dependency optional for representative pages.

Other repository occurrences: the Git source requirement at `requirements.txt:52`, English/Chinese installation README notes, and a legacy Kaggle notebook's alternative source-install command. The similarly named functions in `detection/ctd_utils/textmask.py` use OpenCV; they are not calls to pydensecrf. CTD is not our selected detector.

## 2. Impact on each selected component

| Component | Direct CRF computation? | Can the selected workflow simply omit it? |
|---|---|---|
| Default detector | No | Algorithm independent, but package import currently requires CRF. Its raw mask needs downstream refinement for the selected C baseline. |
| 48px Japanese OCR | No | Recognition independent; same import blocker. |
| NLLB-600M JPN→ESP | No | Tokenization/generation independent; same import blocker. |
| LaMa Large | No | Model consumes image + mask; upstream's selected mask-generation path uses CRF. |
| Default Spanish renderer | No | Glyph layout is independent, but it composites onto the inpainted image whose result depends on the mask. |

CRF executes after OCR and translation; its removal does not directly alter the Japanese recognized or Spanish generated from identical inputs. It can change which original pixels are erased and which art is reconstructed. That affects residual Japanese, line art/screentone damage, apparent text completeness, and final visual quality. These effects must not be presented as an unchanged end-to-end evaluation.

There is no selected-config switch that removes these imports or turns off this mask operation while retaining the same detector/normal pipeline. `ignore_errors` is not a solution: the import fails before runtime fallback, and raw-mask fallback after a runtime exception changes reconstruction. `inpainter=none`/`renderer=none` do not remove module imports and do not constitute our intended C evaluation.

## 3. Binary and maintained alternatives

All compatibility statements below distinguish published platform tags from verified execution. No binary was downloaded, imported, or executed.

**Official pinned fork:** the `zyddnys/pydensecrf` branch resolved to `3ca3d8f0cbd9701f4a765f97fbad43f9b2fe80a6` during investigation. Its releases API returned no releases. No maintainer-published Windows wheel matching this exact source was established. The branch is mutable; a future source build should record/pin its resolved commit.

**Original PyPI package:** `pydensecrf==1.0rc3`, released 2018-04-01, publishes only a 1,036,569-byte source archive. No current Windows wheel in that release. See [PyPI](https://pypi.org/project/pydensecrf/).

**Maintained fork, PyDenseCRF2:** `pydensecrf2==1.1` is maintained for CellSeg3D and exports the `pydensecrf` import namespace. Its published files are a CPython 3.9 macOS wheel and a 1,468,587-byte source archive; no matching Windows 3.12/3.14 wheel. Latest release and repository push observed: December 2024. It is a plausible API-family alternative, but does not solve this Windows compiler problem from currently published binaries. See [PyPI](https://pypi.org/project/pydensecrf2/) and [maintainer repository](https://github.com/AdaptiveMotorControlLab/pydensecrf).

**Third-party Windows CPython 3.12 wheel:** release metadata confirms:

```text
pydensecrf-1.0-cp312-cp312-win_amd64.whl
Size: 194,521 bytes
SHA256: 8f839df67182fe4d6ae2bf16ad3af9af11723166282014dc691580887a5287c6
Published as asset: 2025-10-30
Host: hgmzhn/manga-translator-ui, release v1.7.6
```

[Release containing the dependency asset](https://github.com/hgmzhn/manga-translator-ui/releases/tag/v1.7.6). The repository hosting a binary is not proof of its build provenance. The associated [CRF source fork](https://github.com/hgmzhn/pydensecrf) has a distinct source version (`1.0`, versus pinned fork `1.0.post1`). Its current tree has Linux/macOS build workflows, and does not establish a Windows workflow/source-commit association for this older asset. GitHub's digest verifies artifact integrity, not equivalence to upstream's selected source.

The examined source fork pins Cython 0.29.36 for building; the pinned upstream dependency uses Cython >=3.1 and explicitly restores module-level enum constants used by Manga Image Translator. Old Cython builds may already expose those constants; the difference is a required check, not proof that the wheel is broken. Python 3.12 x64 tags are appropriate; Python 3.14 is incompatible with these tags. NumPy 2.5.4 ABI support, native DLL dependencies, exported API, installed size, and numerical equivalence remain unverified. Installing the wheel would require replacing the Git source requirement in an evaluation-only requirements file; editing upstream source would not inherently be necessary.

**Conda-forge Windows binary:** an existing CPython 3.12 artifact is:

```text
win-64/pydensecrf-1.0rc3-py312h72972c8_6.conda
Size: 730,728 bytes
SHA256: aa79604cb4b5513f7dd72c36b29ca5764e2dc7b933027823ea3d0f6b139d9908
Published: 2024-05-21
```

Its declared constraints include Python >=3.12,<3.13, NumPy >=1.19,<3, UCRT, and VC14 runtime packages. Those NumPy bounds admit the pinned NumPy 2.5.4, but metadata alone does not prove native ABI compatibility. The preceding build requires NumPy <2 and must not be substituted accidentally. This is a conda package, not a pip wheel. Use a properly solved isolated conda/micromamba prefix if investigating it, not a hand-copied `.pyd` in the existing venv. The [package listing](https://anaconda.org/conda-forge/pydensecrf/files) confirms Windows/Python 3.12 availability. The [feedstock](https://github.com/conda-forge/pydensecrf-feedstock) is archived, so this is not an actively maintained long-term answer.

## 4. Exact bypass changes, proposed only

**Import-only change for A/B:** in `mask_refinement/text_mask_utils.py`, remove the two module-level imports at lines 68–69 and place the used imports inside `refine_mask`:

```diff
-from pydensecrf.utils import compute_unary, unary_from_softmax
-import pydensecrf.densecrf as dcrf
 def refine_mask(rgbimg, rawmask):
+    from pydensecrf.utils import unary_from_softmax
+    import pydensecrf.densecrf as dcrf
     # Existing function body unchanged.
```

Create a separate evaluation requirements file excluding the CRF Git requirement; do not edit upstream requirements. That file would also document all other necessary dependency selections. This is only a proposed diff, **not applied**.

Expected impact: module imports and A/B no longer require CRF; detection/OCR/translation computations are unchanged by this import move. Stage C still requires CRF and should fail explicitly at the actual refinement call if it is absent. The change would require syntax/import checks and later sample tests. Other dependencies could still block imports. It does not prove the whole environment works. A temporary patch or separate evaluation checkout must be recorded against the pinned commit; modifying the shared upstream clone requires user permission first.

**Removing CRF computation for C:** additionally omit the call at line 184 (leave the connected-component mask unchanged), or replace `refine_mask` with another mask algorithm. Removing the imports alone would produce a NameError/ModuleNotFoundError at runtime. A no-op/fake `pydensecrf` package would conceal the algorithm change and is not recommended. Raw/morphological masks preserve neither the exact algorithm nor guaranteed reconstruction quality. This would be a separately labelled ablation, not our upstream C baseline.

**Alternative detector with a precomputed mask:** could avoid the runtime refinement branch, but would still require import deferral, change our detector/model selection, and require another quality comparison. Not recommended as a workaround for the first controlled test.

## 5. Options compared

Sizes here are incremental CRF/toolchain overhead, not the previously estimated common ML stack/model downloads. Where installed sizes have not been measured, they are explicitly described as planning allowances.

| Option | Compatibility and fidelity | Download / installed overhead | Maintenance burden | Assessment |
|---|---|---|---|---|
| Omit CRF with no changes | Ordinary package import fails | None | None | Not viable |
| Lazy imports; run only A/B | No change to selected OCR/translation algorithms; C remains unavailable | Essentially no CRF overhead | Small explicit source patch to rebase/review | Safest low-cost partial evaluation if the user permits a patch |
| Validate third-party CP312 wheel | Appropriate platform tags; API/ABI/provenance unverified; preserves CRF intent if validated | 0.195 MB artifact; allow a few MB installed plus any missing runtime, not measured | Pin URL/hash and record dependency deviation | Smallest candidate for C, but not verified equivalent |
| Conda-forge CP312 binary in local prefix | Published matching build; older code, declared NumPy compatibility; archived recipe | 0.731 MB CRF artifact; manager/Python/runtimes add overhead; provisional 0.1–0.3 GB download / 0.3–0.8 GB prefix before shared ML stack, not solved | Conda/pip coordination and older binary support | More established packaging provenance than an untraced wheel; still a substitution |
| PyDenseCRF2 from source | Same import family; changes source package and still needs compiler | 1.47 MB source plus native build tools | Fork/version validation | No compiler-size advantage on Windows |
| Build pinned source locally | Highest fidelity to selected dependency; build success still untested | See minimal toolchain budget below | Toolchain servicing; retain built wheel for reuse | Preferred fallback when exact-source C is required |
| Remove/replace CRF algorithm | Changes masks and therefore reconstruction | Small code change | Own altered algorithm and quality validation | Not suitable as the normal upstream C evaluation |
| Trusted wheel built elsewhere from exact pinned source | Could preserve source fidelity without local compiler | Wheel likely small, but no such verified release found | Require source commit/build provenance and runtime checks | Best conceptual compiler-free route, currently unavailable |

## 6. If a source build becomes necessary

For **exact pinned-source end-to-end fidelity on this PC**, a local C++ toolchain is currently the established route. This is conditional, not a conclusion that all evaluation must wait for a compiler.

Minimal proposed toolchain:

- Visual Studio Build Tools base/installer and required build infrastructure.
- MSVC v143 C++ x64/x86 compiler/tools for VS 2022 (or a supported newer MSVC toolset compatible with the selected CPython).
- One Windows 10/11 SDK containing headers, libraries, and UCRT (for example Windows 11 SDK 10.0.26100).
- Python-side setuptools, wheel, and Cython confined to the project/build-isolation environment; Eigen/native CRF source is part of the dependency source, not a separate system installation.

No Visual Studio IDE, CUDA toolkit, NVIDIA driver update, ATL/MFC, CMake, Clang, profiling, tests, or game-development workloads are needed by this setup.py path. Use individual components/required dependencies instead of adding all recommended/optional workload items. Microsoft documents the [component IDs](https://learn.microsoft.com/en-us/visualstudio/install/workload-component-id-vs-build-tools?view=visualstudio) and [MSVC tool acquisition](https://learn.microsoft.com/en-us/cpp/overview/acquire-msvc).

Provisional planning estimate for that limited toolchain: **2–4 GB download and 6–10 GB installed**, with more temporary/cache space potentially needed. These are estimates, not figures reported by an installer on this machine. Exact totals depend on toolset/SDK revisions and shared components. Microsoft's general Visual Studio disk figures are not an exact quote for this minimal set. Before any approval request to actually install it, capture the selected component IDs and installer-calculated totals; if that cannot be obtained without running a bootstrapper, obtain separate permission for that inspection step. No installer was downloaded or launched here.

## Recommended decision

1. Do not approve/install Build Tools solely to begin OCR and translation-quality assessment. If a minimal source change is acceptable, the documented lazy-import patch enables the logical A/B separation without changing their algorithms. It would not be an unmodified checkout and should be labelled accordingly.
2. If preserving an unchanged upstream checkout is the priority, investigate a project-local Python 3.12 binary-based CRF environment first. Explicitly approve and record the dependency substitution before installing it. Validate native imports, enum constants, NumPy ABI, and DLL dependencies before any sample inference; later compare mask behavior before claiming equivalent C results.
3. If neither a small import patch nor a validated binary substitution is acceptable, a toolchain/source build is justified for the exact selected C pipeline. Review actual component sizes first. This investigation does not request or grant compiler installation approval.

No approach has yet established translation quality, model fit, or reconstruction quality. The current environment remains unready for inference.

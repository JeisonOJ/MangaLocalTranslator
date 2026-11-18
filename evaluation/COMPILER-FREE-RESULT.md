# Compiler-free CRF validation: successful for the API used by upstream

Date: 2026-11-15. Upstream unchanged at `36fed8528d851f8e4cce8e35255e080f4138a8d3`.

**A compiler-free project-local Python 3.12 installation is feasible and has passed a targeted runtime compatibility check.** Recommended CRF source: conda-forge, **pydensecrf 1.0rc3, build py312h72972c8_6**. This is a documented dependency substitution for upstream's pinned Git source, not a byte-identical build of that source. No upstream source change or import bypass is needed with this binary present.

The full manga environment is not installed. No OCR/translation model or manga inference was run. The only CRF computation was a tiny synthetic API/ABI test, with no image/model downloads. No compiler, CUDA toolkit, driver, global Python, system PATH, or Windows registry was modified. No commits or pushes.

## Candidates and trust assessment

| Candidate | Passive checks | Execution decision |
|---|---|---|
| conda-forge `pydensecrf-1.0rc3-py312h72972c8_6.conda` | Published SHA256 verified; embedded source archive hash, recipe commit, CI run, NumPy build version and Eigen patch checked against the recorded feedstock commit; native x64/Python 3.12 headers verified | Accepted from established conda-forge distribution; installed and tested in local prefix |
| `pydensecrf-1.0-cp312-cp312-win_amd64.whl`, hosted in hgmzhn release v1.7.6 | Published SHA256 verified; internal wheel tag and PE x64/Python 3.12 headers verified; contains expected API names, but no verified Windows build/source-commit association | Not installed, imported, or executed |
| Original PyPI `pydensecrf` / maintained `pydensecrf2` | No suitable published Windows Python 3.12 wheel established | No source build attempted |

The two CRF candidate archives total **925,249 bytes**. They were inspected passively with Python's standard ZIP/TAR/Zstandard support. Their Python files, scripts and native extensions were not executed during archive inspection. The unverified wheel remains only an archive under `crf-binary-audit/`.

Package source: [conda-forge package listing](https://anaconda.org/conda-forge/pydensecrf/files). Exact artifact:

```text
https://conda.anaconda.org/conda-forge/win-64/pydensecrf-1.0rc3-py312h72972c8_6.conda
SHA256 aa79604cb4b5513f7dd72c36b29ca5764e2dc7b933027823ea3d0f6b139d9908
Download 730,728 bytes
```

This establishes distribution integrity and a credible source/build trail, not cryptographic proof that the binary is a reproducible build of the listed source. No independently verified build attestation was established. Standard trust in conda-forge's package infrastructure remains necessary.

## Provenance and comparison with upstream's pinned dependency

Conda artifact metadata records:

- Source `pydensecrf-1.0rc3.tar.gz`, SHA256 `08be1603af2bede05c7697b6018e8e3059de7cc181e4e784b334889dcc749aa5`; the downloaded source archive matched.
- Feedstock commit `921f40e2b0b7dc11621522c9df94ac6e61967a03`, build `azure_20240521.2.1`.
- Build Python 3.12.3, Cython 0.29.37, **NumPy 2.0.0rc2**, MSVC 2019.
- One source patch, `backport_108.patch`, whose 299 modified paths are confined to bundled Eigen headers. Its embedded content matches the patch at the recorded feedstock commit after newline normalization.
- Declared runtime bounds: CPython 3.12, NumPy >=1.19,<3, UCRT and VC runtime packages. Those runtime DLLs are installed within the local prefix, not by a system redistributable installer.

Compared the original source and conda patch scope with pinned dependency commit `3ca3d8f0cbd9701f4a765f97fbad43f9b2fe80a6`:

- CRF C++ algorithm files under `pydensecrf/densecrf/src/`, `utils.py`, `eigen.pyx`, and `eigen.pxd` have matching Git blob hashes.
- Wrapper differences identified in `densecrf.pyx` and `densecrf.pxd`: explicit/relative Eigen imports, plus module-level enum restoration for Cython 3.1+ in the pinned fork.
- The tested older-Cython binary exposes those module-level constants correctly; the pinned fork's Cython compatibility shim is not needed by this build.

This supports functional compatibility for the selected API. Different source packaging, bundled Eigen changes, compiler/Cython versions, and build flags prevent a claim of bit-for-bit or universal numerical equivalence to a fresh pinned-source build.

## Python, native DLL and NumPy compatibility results

Both CRF archives declare `cp312`/Windows x64 in their native filenames; the wheel also declares `cp312-cp312-win_amd64` in `WHEEL`. PE headers confirm AMD64 (`0x8664`) and PE32+. They import `python312.dll`, MSVC runtime DLLs and Windows/UCRT DLLs. No CUDA dependency appears in these native import tables.

The tested environment is:

```text
C:\Dev\Codex\MangaLocalTranslator\evaluation\envs\crf312
Python 3.12.16, 64 bit
NumPy 2.5.4, conda-forge
pydensecrf 1.0rc3, py312h72972c8_6
OpenBLAS 0.3.34
pip 26.2.2
27 total solved packages, including local Python/DLL runtime dependencies
```

The initially considered MKL solve required 178.60 MB. Selecting OpenBLAS reduced the solved package download to **47,643,735 bytes**, without changing the CRF API. Exact packages, URLs and SHA256s are in `crf-binary-audit/installed-packages.json` and `crf312-explicit-lock.txt`.

Runtime checks completed successfully using the prefix's `python.exe` directly, without shell activation or persistent PATH edits:

- Import `pydensecrf.densecrf` and `compute_unary` / `unary_from_softmax`.
- Access `DIAG_KERNEL` and `NO_NORMALIZATION` as module attributes.
- Construct `DenseCRF2D`; set float32 unary potentials; add Gaussian and RGB bilateral terms with upstream's exact parameters; run five iterations on synthetic 8×8 arrays.
- Verify finite, normalized probabilities and an 8×8 uint8 mask containing both background and foreground; repeated result is deterministic in this test.
- `python -I -m pip check`: no broken requirements found.

Actual result: `crf-binary-audit/compatibility-result.json`. Test: `scripts/validate_crf_api.py`. This verifies the selected CRF/NumPy interface on this PC. It does not validate all exported APIs, all numerical inputs, GPU execution, complete mask refinement, or the full manga pipeline. An initial attempt to invoke the upstream function in isolation exposed its OpenCV dependency; the final CRF-only test uses NumPy's bytewise complement to construct the same synthetic inputs, avoiding another 44 MB OpenCV download. Upstream itself was not altered or imported as a whole.

NumPy 2 ABI compatibility is demonstrated for this installed combination, rather than inferred only from version bounds. Future package operations must preserve/retest that combination. See NumPy's [ABI migration guidance](https://numpy.org/doc/stable/numpy_2_0_migration_guide.html).

## Installed size and isolation

Measured logical file sizes after validation:

| Location | Bytes | Approximate MiB |
|---|---:|---:|
| `evaluation/envs/crf312` | 214,450,258 | 204.5 |
| `evaluation/mamba-root` package/index cache | 267,889,731 | 255.5 |
| `evaluation/crf-binary-audit` archives, tools, reports | about 25,521,000 | 24.3 |

These are logical sizes, not allocated disk space. Small report/log additions follow this measurement. Source/metadata/archive inspection adds several MB beyond the 47.64 MB environment payload. The hash-verified micromamba bootstrap archive was 4,696,444 bytes. No multi-GB dependencies or model weights were fetched. Existing upstream clone and `.venv-probe` remain present separately.

The installed environment used copying rather than hard links; link scripts, shortcuts and bytecode precompilation were disabled. Configuration and caches are inside the workspace. No shell hook or activation was installed. Micromamba briefly created a user-profile `.conda/environments.txt` text registration containing only this prefix; that task-created file was removed. It was not a Windows registry entry. No preexisting registration entries were removed. An empty `.conda` directory may remain.

Micromamba linking/listing stalled under the sandbox; the task-owned stalled processes were stopped. Offline linking completed outside that sandbox, with the same project-local paths and restrictions. No additional system installation was used to resolve the stall.

## Exact use and reproduction procedure

The validated environment already exists. To repeat the small compatibility check:

```powershell
Set-Location C:\Dev\Codex\MangaLocalTranslator
.\evaluation\envs\crf312\python.exe -I evaluation\scripts\validate_crf_api.py
.\evaluation\envs\crf312\python.exe -I -m pip check
```

To reproduce the 27-package environment in a **new** project-local prefix from the saved explicit SHA256 lock:

```powershell
Set-Location C:\Dev\Codex\MangaLocalTranslator
# Reuses the existing package cache; does not fetch model weights or the ML stack.
& .\evaluation\scripts\Recreate-CrfEnvironment.ps1 -Offline
```

The script refuses to overwrite an existing reproduction prefix and cleans up its new profile registration. Omit `-Offline` only when reinstalling from the locked package URLs is intended. It uses the already hash-verified local micromamba executable and explicit configuration; it does not install compilers or initialize a shell. The reproduction script was reviewed but not executed, because the installed environment has already passed and a duplicate installation adds no new evidence.

## Next steps for the complete evaluation environment

1. Use the validated `evaluation/envs/crf312/python.exe` as the evaluation interpreter. Preserve the explicit package lock and the CRF artifact hash.
2. Review and resolve the remaining packages before installation. `crf-binary-audit/requirements-evaluation-remainder.txt` is an overlay generated from the pinned upstream requirements, excluding CRF and torch/torchvision. Upstream files remain untouched. CRF is supplied by conda-forge; do not run upstream requirements verbatim, which would replace it with the source-build requirement.
3. Obtain exact CUDA-wheel/dependency resolution and download totals before any large installation. Previous broad-stack estimate remains approximately **2.6–3.0 GB download / 6–9 GB installed**, with overlap from the small environment now present. Do not interpret the successful CRF check as approval to install the rest. The candidate CUDA pair remains torch 2.14.1+cu130 and torchvision 0.29.1+cu130 from the official PyTorch index; no GPU torch check was run here.
4. After separate authorization for the remaining stack, install it through this environment's `python -m pip`, using a reviewed plan/wheelhouse and the overlay. Confirm NumPy and CRF remain intact, rerun this compatibility test, and run full pipeline import/config checks without model downloads.
5. Keep the 3.20 GB models deferred. No manga inference until samples and the required runtime/model approvals are in place.

## Decision

**Proceed without Microsoft C++ Build Tools for this evaluation.** The conda-forge Python 3.12 binary passed the targeted compatibility checks and preserves upstream's CRF call path without source edits. The dependency substitution and archived feedstock are reproducibility/maintenance caveats, not reasons to install a compiler immediately.

If a later requirement demands the exact pinned-source build or the binary fails on real masks, reconsider an exact-source trusted build. The fallback remains the import-only relocation documented in `CRF-FINDINGS.md`: move the two CRF imports inside `refine_mask`, leaving its body and caller unchanged. That would require approval, allow A/B only without CRF, and preserve the original reconstruction algorithm for use when CRF is available. No fallback patch was applied.

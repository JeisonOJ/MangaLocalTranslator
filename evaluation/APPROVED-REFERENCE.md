# Approved first-page reference

The user approved Run-02 as the preferred Spanish rendering of `ManualImageTest/5.jpg`. This approval selects a visual reference; it does not authorize new API calls, model runs, downloads, or automatic adoption without page-specific review.

- Original baseline, preserved: `results/google-full-page-01/reconstruction/run-01/`.
- Approved reference, preserved: `results/google-full-page-01/reconstruction/run-02/spanish-page.png`.
- Comparison: `results/google-full-page-01/reconstruction/run-02/side-by-side.png`.
- Original image and all API responses/translations remain unchanged.
- Reference dimensions: 1403×2048. Original SHA256: `e57e26a93fa353ccd0c3b71b4ebd419b79124ff928785d7de293ab594dd9aa18`.

## Successful configuration

Runtime: `evaluation/envs/crf312/python.exe`, Python 3.12.16, torch 2.14.1+cu130, torchvision 0.29.1+cu130, NumPy 2.5.4, transformers 5.19.0, conda-forge PyDenseCRF 1.0rc3. Upstream commit: `36fed8528d851f8e4cce8e35255e080f4138a8d3`; source unmodified.

1. **Detection/OCR:** upstream default detector, detection size 1536, text threshold 0.5, box threshold 0.7, unclip ratio 2.3; 48px Japanese OCR on CUDA. Raw text/line polygons/probabilities retained. Six dialogue groups mapped to C00–C05 in manga reading order. Page number excluded. No manual OCR correction substituted for raw text.
2. **Translation:** Google Cloud Translation Basic v2 REST NMT, source `ja`, target `es`, format `text`. Six unchanged OCR strings, 74 Unicode code points, one explicitly authorized request, no retries. Only Japanese text and required API options left the PC; image/coordinates stayed local. Credentials supplied through `MANGA_GOOGLE_TRANSLATE_API_KEY`, never stored in output. Exact raw responses and region mapping remain in `results/google-full-page-01/`.
3. **Removal mask:** reuse saved detector mask and approved OCR line geometry. Upstream `fit_text` CRF refinement, kernel size 3, dilation offset 20, ignore_bubble 0. Inspect mask overlay before inpainting. First-page mask covered 145,099 pixels; page number and artwork were excluded.
4. **Inpainting:** installed LaMa Large, CUDA, FP32, maximum processing dimension 1024. Fresh process; only LaMa weights initialized. Save cleaned image at original dimensions; verify pixels outside the approved removal mask are unchanged. Exit before rendering. This page used about 1.42 GiB peak process RSS and 1.21 GiB peak torch GPU reservation.
5. **Approved typography:** reuse cleaned image and exact API strings. Evaluation-only Pillow/FreeType renderer using existing Arial-Unicode-Regular.ttf; black text on cleaned white balloons. Wrap only at spaces, preserve punctuation/word spacing, center measured glyph bounds, prefer fewer then balanced lines. No word splitting, paraphrasing or truncation. First-page preferred sizes: 32 px for C00/C01, 26 px for C02–C05. Conservative balloon-interior rectangles were manually reviewed. Reject ink over dark artwork/borders; retain baseline rendering for any regressing region. C02 remains a tall block with some short lines.

Successful typography implementation remains available in `scripts/typography_run02.py`, with a frozen copy in Run-02. It does not import ML libraries or access the network. **It is a page-specific reproducible experiment, not a generic next-page command:** its source paths, six-region count, boxes and preferred sizes refer to page 5, and it refuses to overwrite Run-02. For a new page, create a separately named evaluation script/config and output directory using these same wrapping/spacing/centering rules. Do not reuse these coordinates or replace approved files.

The earlier upstream renderer removed punctuation spaces and could split words even with hyphenation disabled. The approved experiment bypasses those behaviors; it does not patch upstream. NLLB is rejected for the current fidelity requirement. M2M100 quality remains untested because its run stopped for RAM pressure. Neither local text-generation model is part of this approved configuration.

## Procedure for the next evaluation page

1. Obtain a user-authorized image path and preserve the original/hash. Choose a new per-page output directory.
2. Separately authorize the local detection/OCR run. Record raw OCR, confidence, polygons and proposed reading order; review uncertain Japanese, non-dialogue content and duplicates.
3. Freeze the exact outgoing text and stable region mapping. Calculate code-point count and estimated Basic v2 NMT cost. Obtain explicit per-job authorization before any potentially billable request; provide the key securely in the executing process. Use a new ledger; preserve prior ledgers; no silent retries or cloud fallback.
4. Review the returned exact Spanish before reconstruction. Do not silently editorialize it.
5. Separately authorize local reconstruction. Review the mask and page-specific typography boxes. Use fresh processes, with no local translation models, a 500 MiB available-RAM stop guard and CUDA/OOM monitoring. Start with several GiB available RAM and sufficient VRAM; do not infer future pages fit from this page's measurements.
6. Produce a candidate, inspect every region and compare with a page-specific baseline. Retain baseline behavior for any regression. Seek approval before adopting the candidate.

This reference establishes a successful one-page workflow, not broad OCR/translation reliability. No further processing is authorized by this documentation step.

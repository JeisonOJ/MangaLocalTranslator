# Selected models: download and initialization results

All four models initialized successfully without OCR, translation, or reconstruction. Upstream source and runtime packages were unchanged. No system installations, commits, or pushes.

Total selected payload: **3,200,047,996 bytes** (3.200 GB). Each artifact source, pinned version/revision, absolute path, byte size, expected integrity reference, and SHA256 is in [manifest.json](models/manifest.json).

Paths are under `evaluation/models/{detection,ocr,inpainting,nllb-600m}`. Selected artifacts: detect-20241225.ckpt; ocr_ar_48px.ckpt and alphabet-all-v7.txt; lama_large_512px.ckpt; NLLB distilled 600M pytorch_model.bin plus six JSON/tokenizer files.

Detector/OCR/LaMa matched upstream SHA256s; NLLB weights and SentencePiece matched published LFS SHA256s. Small NLLB config/tokenizer files matched pinned Git blob IDs; their local SHA256s are also recorded. Required tokenizer loaded and Spanish language token resolved. The initial CDN ETag comparison was corrected to the authoritative LFS SHA256; no weights were downloaded twice.

| Model | Device | Peak process RSS GiB | Peak torch reserved MiB |
|---|---|---:|---:|
| detector | cuda | 1.49 | 332.0 |
| ocr48 | cuda | 1.42 | 506.0 |
| lama_large | cuda | 1.36 | 514.0 |
| nllb600 | cpu | 2.13 | 332.0 |

RAM sampled every 50 ms. Peak total system used RAM: 13.47 GiB. Torch GPU allocator counters exclude driver/desktop/non-PyTorch allocations. Models were loaded one at a time and released, but upstream default detector retains a module-level GPU reference (~299 MiB); therefore later GPU peaks include that baseline. A full simultaneous-load configuration was not tested. No inference activations/workspaces are included. CPU RSS can understate future committed/touched weight memory. These figures do not establish inference peak memory.

Initialization used upstream loading methods, with a local NLLB directory selected in evaluation code. Offline HF settings prevented model fetching during loading. The sandboxed initialization stalled; retrying outside that sandbox completed without source/system changes. No model compatibility failure was observed.

**Ready for user-supplied manga samples: yes, for a small controlled evaluation.** Model loading and tokenizer checks passed; translation quality remains unknown. Supply authorized pages and checked Japanese text. Start with one page/segment, CPU NLLB and GPU image stages; close memory-heavy applications. Do not infer simultaneous loading or full-resolution reconstruction will fit from these checks alone.

Detailed loading measurements: [loading-results.json](models/loading-results.json). Download script and initialization script are in evaluation/scripts. Manifest and measurements are reproducible records; no sample inference has been performed.
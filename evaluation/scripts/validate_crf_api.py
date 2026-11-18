"""Compatibility checks on tiny synthetic arrays only; no models or manga inputs."""
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import sys

import numpy as np
import pydensecrf.densecrf as dcrf
from pydensecrf.utils import compute_unary, unary_from_softmax

ROOT = Path(__file__).resolve().parents[2]
source = ROOT / 'upstream/manga_translator/mask_refinement/text_mask_utils.py'
def synthetic_refine(rgb, raw):
    # Same CRF API/parameters as upstream refine_mask, without importing OpenCV or
    # the full ML pipeline. NumPy bitwise_not supplies the synthetic complement.
    probabilities = np.stack([np.bitwise_not(raw), raw], axis=-1).astype(np.float32) / 255.0
    unary = np.ascontiguousarray(unary_from_softmax(probabilities.transpose(2, 0, 1).reshape(2, -1)))
    model = dcrf.DenseCRF2D(raw.shape[1], raw.shape[0], 2)
    model.setUnaryEnergy(unary)
    model.addPairwiseGaussian(sxy=1, compat=3, kernel=dcrf.DIAG_KERNEL,
                             normalization=dcrf.NO_NORMALIZATION)
    model.addPairwiseBilateral(sxy=23, srgb=7, rgbim=rgb, compat=20,
                              kernel=dcrf.DIAG_KERNEL, normalization=dcrf.NO_NORMALIZATION)
    probabilities = np.asarray(model.inference(5))
    assert probabilities.shape == (2, raw.size)
    assert np.isfinite(probabilities).all()
    np.testing.assert_allclose(probabilities.sum(axis=0), 1.0, atol=1e-6)
    return (np.argmax(probabilities, axis=0).reshape(raw.shape) * 255).astype(np.uint8)
rgb = np.full((8, 8, 3), 255, dtype=np.uint8)
rgb[2:6, 3:5] = 0
raw = np.zeros((8, 8), dtype=np.uint8)
raw[2:6, 3:5] = 255
result = synthetic_refine(rgb, raw)
assert result.shape == (8, 8)
assert result.dtype == np.uint8
assert set(np.unique(result)).issubset({0, 255})
assert np.any(result == 255) and np.any(result == 0)
second = synthetic_refine(rgb, raw)
np.testing.assert_array_equal(result, second)

report = {
    'test_scope': 'synthetic 8x8 CRF API/ABI smoke test matching upstream parameters; full pipeline not imported; no manga, models, or GPU',
    'python': sys.version, 'python_executable': sys.executable, 'platform': platform.platform(),
    'numpy': np.__version__, 'numpy_file': np.__file__,
    'pydensecrf': importlib.metadata.version('pydensecrf'), 'native_module': dcrf.__file__,
    'native_sha256': hashlib.sha256(Path(dcrf.__file__).read_bytes()).hexdigest(),
    'upstream_source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
    'compute_unary_import': callable(compute_unary),
    'unary_from_softmax_import': callable(unary_from_softmax),
    'DIAG_KERNEL': int(dcrf.DIAG_KERNEL),
    'NO_NORMALIZATION': int(dcrf.NO_NORMALIZATION),
    'verified_calls': ['DenseCRF2D', 'setUnaryEnergy', 'addPairwiseGaussian',
                       'addPairwiseBilateral', 'inference(5)'],
    'result_shape': list(result.shape), 'result_dtype': str(result.dtype),
    'result_values': [int(x) for x in np.unique(result)],
    'result_sha256': hashlib.sha256(result.tobytes()).hexdigest(),
    'deterministic_repeat': True, 'passed': True,
}
out = ROOT / 'evaluation/crf-binary-audit/compatibility-result.json'
out.write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report, indent=2))

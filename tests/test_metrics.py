"""
Unit tests for Metrics and Circuit Analyzer modules.
Validates numeric correctness of PSNR, SSIM, MSE, BER, and circuit resource calculations.
"""

import numpy as np
import pytest
from metrics.psnr_ssim import (
    compute_psnr,
    compute_ssim,
    compute_mse,
    compute_bit_error_rate,
    evaluate_all,
)
from metrics.circuit_analyzer import CircuitAnalyzer
from core.neqr_encoder import NEQREncoder


def test_psnr_and_mse_calculations():
    """Verify PSNR and MSE for identical and perturbed images."""
    size = 16
    img1 = np.full((size, size), 128, dtype=np.uint8)

    # Identical images
    assert compute_psnr(img1, img1) == float("inf")
    assert compute_mse(img1, img1) == 0.0

    # Stego image with 1-bit LSB modification on all pixels
    img2 = img1 ^ 1
    psnr_val = compute_psnr(img1, img2)
    mse_val = compute_mse(img1, img2)

    assert mse_val == 1.0
    # For MSE=1.0: PSNR = 20 * log10(255 / 1) ≈ 48.1308 dB
    assert pytest.approx(48.1308, rel=1e-3) == psnr_val
    assert psnr_val >= 48.0


def test_ssim_calculation():
    """Verify SSIM score for cover vs LSB modified stego image."""
    size = 16
    rng = np.random.default_rng(100)
    img1 = rng.integers(50, 200, size=(size, size), dtype=np.uint8)
    img2 = np.copy(img1)
    img2[::2, ::2] = img2[::2, ::2] ^ 1  # Flip LSB on 25% of pixels

    ssim_val = compute_ssim(img1, img2)
    assert 0.99 <= ssim_val <= 1.0


def test_ber_and_evaluate_all():
    """Verify bit error rate and comprehensive evaluation dataclass."""
    orig_bits = [1, 0, 1, 1, 0, 0, 1, 0]
    extracted_bits_perfect = [1, 0, 1, 1, 0, 0, 1, 0]
    extracted_bits_corrupt = [1, 0, 0, 0, 0, 0, 1, 0]  # 2 errors

    assert compute_bit_error_rate(orig_bits, extracted_bits_perfect) == 0.0
    assert compute_bit_error_rate(orig_bits, extracted_bits_corrupt) == 0.25

    cover = np.full((16, 16), 100, dtype=np.uint8)
    stego = np.full((16, 16), 101, dtype=np.uint8)
    res = evaluate_all(cover, stego, orig_bits, extracted_bits_perfect, target_psnr=48.0, target_ssim=0.99)

    assert res.status_ber == "PASS"
    assert res.payload_capacity == 256
    assert res.embedding_rate == round(8 / 256.0, 4)


def test_circuit_analyzer():
    """Verify circuit analyzer extracts gate counts and depth accurately."""
    encoder = NEQREncoder(image_size=4, grayscale_bits=8)
    img = np.ones((4, 4), dtype=np.uint8) * 128
    circuit = encoder.encode(img)

    analyzer = CircuitAnalyzer()
    report = analyzer.analyze(circuit)

    assert report.num_qubits == 12
    assert report.total_gates > 0
    assert report.circuit_depth > 0
    assert 0.0 <= report.estimated_fidelity <= 1.0
    assert report.num_h_gates == 4

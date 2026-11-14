"""
PSNR, SSIM, MSE, and Bit Error Rate (BER) evaluation metrics.
Provides real numeric quality evaluation for steganographic image fidelity.
"""

from dataclasses import dataclass
from typing import List, Union, Any
import numpy as np
from skimage.metrics import structural_similarity as skimage_ssim


@dataclass
class MetricsResult:
    """Dataclass holding all image fidelity and payload extraction metrics."""
    psnr: float
    ssim: float
    mse: float
    ber: float
    payload_capacity: int       # Total embeddable bits in cover
    embedding_rate: float       # Bits embedded per pixel (bpp)
    status_psnr: str = "PASS"
    status_ssim: str = "PASS"
    status_ber: str = "PASS"


def compute_psnr(original: np.ndarray, stego: np.ndarray) -> float:
    """
    Compute Peak Signal-to-Noise Ratio (PSNR) in decibels (dB).
    Higher values (> 48 dB) indicate superior visual imperceptibility.
    """
    orig_f = original.astype(np.float64)
    stego_f = stego.astype(np.float64)
    mse = np.mean((orig_f - stego_f) ** 2)

    if mse == 0.0:
        return float("inf")

    max_pixel = 255.0
    psnr = 20.0 * np.log10(max_pixel / np.sqrt(mse))
    return round(float(psnr), 4)


def compute_ssim(original: np.ndarray, stego: np.ndarray) -> float:
    """
    Compute Structural Similarity Index (SSIM) between original and stego images.
    Values close to 1.0 indicate near-identical structural content.
    """
    if original.shape != stego.shape:
        raise ValueError(f"Image shapes do not match: {original.shape} vs {stego.shape}")

    min_dim = min(original.shape[0], original.shape[1])
    # SSIM requires odd window size <= min_dim
    win_size = min_dim if min_dim % 2 == 1 else min_dim - 1
    win_size = max(3, min(7, win_size))

    if original.ndim == 3:
        val = skimage_ssim(
            original,
            stego,
            data_range=255,
            win_size=win_size,
            channel_axis=-1,
        )
    else:
        val = skimage_ssim(
            original,
            stego,
            data_range=255,
            win_size=win_size,
        )
    return round(float(val), 6)


def compute_mse(original: np.ndarray, stego: np.ndarray) -> float:
    """
    Compute Mean Squared Error (MSE) between two grayscale images.
    """
    orig_f = original.astype(np.float64)
    stego_f = stego.astype(np.float64)
    mse = np.mean((orig_f - stego_f) ** 2)
    return round(float(mse), 6)


def compute_bit_error_rate(original_bits: List[int], extracted_bits: List[int]) -> float:
    """
    Compute Bit Error Rate (BER) between embedded and extracted payloads.
    0.0 represents 100% accurate, error-free reconstruction.
    """
    if not original_bits:
        return 0.0

    compare_len = min(len(original_bits), len(extracted_bits))
    if compare_len == 0:
        return 1.0

    errors = sum(1 for a, b in zip(original_bits[:compare_len], extracted_bits[:compare_len]) if a != b)
    # Add penalty if lengths mismatch
    length_penalty = abs(len(original_bits) - len(extracted_bits))
    total_errors = errors + length_penalty
    ber = total_errors / max(len(original_bits), len(extracted_bits))
    return round(float(ber), 6)


def evaluate_all(
    original: np.ndarray,
    stego: np.ndarray,
    original_bits: List[int],
    extracted_bits: List[int],
    target_psnr: float = 48.0,
    target_ssim: float = 0.99,
) -> MetricsResult:
    """
    Compute comprehensive metrics and check against quality thresholds.
    """
    psnr = compute_psnr(original, stego)
    ssim = compute_ssim(original, stego)
    mse = compute_mse(original, stego)
    ber = compute_bit_error_rate(original_bits, extracted_bits)

    total_pixels = original.shape[0] * original.shape[1]
    payload_capacity = total_pixels  # 1 bit per pixel for 1 LSB plane
    embedding_rate = round(len(original_bits) / float(total_pixels), 4)

    status_psnr = "PASS" if psnr >= target_psnr or np.isinf(psnr) else "FAIL"
    status_ssim = "PASS" if ssim >= target_ssim else "FAIL"
    status_ber = "PASS" if ber == 0.0 else "FAIL"

    return MetricsResult(
        psnr=psnr,
        ssim=ssim,
        mse=mse,
        ber=ber,
        payload_capacity=payload_capacity,
        embedding_rate=embedding_rate,
        status_psnr=status_psnr,
        status_ssim=status_ssim,
        status_ber=status_ber,
    )

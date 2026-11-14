"""
Metrics and Circuit Analysis Module for Quantum Image Steganography.

Computes:
- Peak Signal-to-Noise Ratio (PSNR > 48 dB)
- Structural Similarity Index (SSIM > 0.99)
- Mean Squared Error (MSE)
- Bit Error Rate (BER)
- Amplified visual difference map
- Quantum circuit gate count, depth, and qubit count metrics
"""

from dataclasses import dataclass, asdict
from typing import List, Union, Dict, Any, Tuple
import numpy as np
from skimage.metrics import structural_similarity as skimage_ssim
from qiskit import QuantumCircuit


@dataclass
class MetricsResult:
    """Dataclass holding image fidelity and extraction metrics."""
    psnr: float
    ssim: float
    mse: float
    ber: float
    payload_capacity: int
    embedding_rate: float
    status_psnr: str = "PASS"
    status_ssim: str = "PASS"
    status_ber: str = "PASS"

    def to_dict(self) -> Dict[str, Any]:
        res = asdict(self)
        if np.isinf(self.psnr):
            res["psnr"] = "Infinity (Lossless)"
        return res


@dataclass
class CircuitReport:
    """Dataclass holding quantum circuit complexity analysis metrics."""
    num_qubits: int
    total_gates: int
    circuit_depth: int
    nonlocal_gates: int
    gate_breakdown: Dict[str, int]

    @property
    def gate_distribution(self) -> Dict[str, int]:
        return self.gate_breakdown

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def compute_psnr(original: np.ndarray, stego: np.ndarray) -> float:
    """Compute Peak Signal-to-Noise Ratio (PSNR) in decibels (dB)."""
    orig_f = original.astype(np.float64)
    stego_f = stego.astype(np.float64)
    mse = np.mean((orig_f - stego_f) ** 2)

    if mse == 0.0:
        return float("inf")

    max_pixel = 255.0
    psnr = 20.0 * np.log10(max_pixel / np.sqrt(mse))
    return round(float(psnr), 4)


def compute_ssim(original: np.ndarray, stego: np.ndarray) -> float:
    """Compute Structural Similarity Index (SSIM)."""
    if original.shape != stego.shape:
        raise ValueError(f"Image shapes do not match: {original.shape} vs {stego.shape}")

    min_dim = min(original.shape[0], original.shape[1])
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
    """Compute Mean Squared Error (MSE)."""
    orig_f = original.astype(np.float64)
    stego_f = stego.astype(np.float64)
    mse = np.mean((orig_f - stego_f) ** 2)
    return round(float(mse), 6)


def compute_bit_error_rate(original_bits: List[int], extracted_bits: List[int]) -> float:
    """Compute Bit Error Rate (BER)."""
    if not original_bits:
        return 0.0

    compare_len = min(len(original_bits), len(extracted_bits))
    if compare_len == 0:
        return 1.0

    errors = sum(1 for a, b in zip(original_bits[:compare_len], extracted_bits[:compare_len]) if a != b)
    length_penalty = abs(len(original_bits) - len(extracted_bits))
    total_errors = errors + length_penalty
    ber = total_errors / max(len(original_bits), len(extracted_bits))
    return round(float(ber), 6)


def compute_difference_map(original: np.ndarray, stego: np.ndarray, amplification: float = 50.0) -> np.ndarray:
    """
    Compute absolute pixel difference map, amplified for visual inspection.
    """
    diff_arr = np.abs(original.astype(int) - stego.astype(int))
    diff_amp = np.clip(diff_arr * amplification, 0, 255).astype(np.uint8)
    return diff_amp


def evaluate_metrics(
    original: np.ndarray,
    stego: np.ndarray,
    original_bits: List[int],
    extracted_bits: List[int],
    target_psnr: float = 48.0,
    target_ssim: float = 0.99,
) -> MetricsResult:
    """
    Compute comprehensive metrics and test against target quality thresholds.
    """
    psnr = compute_psnr(original, stego)
    ssim = compute_ssim(original, stego)
    mse = compute_mse(original, stego)
    ber = compute_bit_error_rate(original_bits, extracted_bits)

    total_pixels = original.shape[0] * original.shape[1]
    payload_capacity = total_pixels
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


# Alias
evaluate_all = evaluate_metrics


class CircuitAnalyzer:
    """Analyzes QuantumCircuit depth, gate count, qubit allocation, and non-local operations."""

    def analyze(self, circuit: QuantumCircuit) -> CircuitReport:
        ops = dict(circuit.count_ops())
        total_gates = sum(ops.values())
        depth = circuit.depth()
        nonlocal_gates = circuit.num_nonlocal_gates()

        return CircuitReport(
            num_qubits=circuit.num_qubits,
            total_gates=total_gates,
            circuit_depth=depth,
            nonlocal_gates=nonlocal_gates,
            gate_breakdown=ops,
        )

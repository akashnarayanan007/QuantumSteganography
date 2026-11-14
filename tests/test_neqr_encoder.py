"""
Unit tests for NEQREncoder module.
Validates quantum circuit construction, qubit counts, superposition, and statevector normalization.
"""

import numpy as np
import pytest
from qiskit import QuantumCircuit
from core.neqr_encoder import NEQREncoder
from core.reconstructor import ImageReconstructor


def test_neqr_encoder_initialization():
    """Verify qubit allocation for various power-of-2 image sizes."""
    # 4x4 image: n = 2 -> 2*2 + 8 = 12 qubits
    enc_4 = NEQREncoder(image_size=4, grayscale_bits=8)
    assert enc_4.n == 2
    assert enc_4.position_qubits == 4
    assert enc_4.grayscale_qubits == 8
    assert enc_4.total_qubits == 12

    # 16x16 image: n = 4 -> 2*4 + 8 = 16 qubits
    enc_16 = NEQREncoder(image_size=16, grayscale_bits=8)
    assert enc_16.n == 4
    assert enc_16.position_qubits == 8
    assert enc_16.grayscale_qubits == 8
    assert enc_16.total_qubits == 16


def test_neqr_circuit_construction():
    """Verify that encode() produces a valid QuantumCircuit with correct operations."""
    image_size = 4
    encoder = NEQREncoder(image_size=image_size, grayscale_bits=8)
    test_img = np.array([
        [10, 20, 30, 40],
        [50, 60, 70, 80],
        [90, 100, 110, 120],
        [130, 140, 150, 160],
    ], dtype=np.uint8)

    circuit = encoder.encode(test_img)
    assert isinstance(circuit, QuantumCircuit)
    assert circuit.num_qubits == 12
    assert circuit.depth() > 0

    info = encoder.get_circuit_info(circuit)
    assert info["num_qubits"] == 12
    assert info["gate_count"] > 0
    # Must have Hadamard gates for position superposition
    assert info["operations"].get("h", 0) == 4


def test_neqr_statevector_normalization_and_reconstruction():
    """Verify that encode_statevector creates a unit-norm state and reconstructs accurately."""
    image_size = 8
    encoder = NEQREncoder(image_size=image_size, grayscale_bits=8)
    rng = np.random.default_rng(42)
    test_img = rng.integers(0, 256, size=(image_size, image_size), dtype=np.uint8)

    sv = encoder.encode_statevector(test_img)
    total_prob = np.sum(np.abs(sv) ** 2)
    assert np.isclose(total_prob, 1.0, atol=1e-6)

    # Reconstruct back to image
    reconstructor = ImageReconstructor()
    rec_img = reconstructor.statevector_to_image(sv, image_size=image_size, n=encoder.n, q=8)
    assert np.array_equal(test_img, rec_img)

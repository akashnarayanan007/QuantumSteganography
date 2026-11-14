"""
NEQR (Novel Enhanced Quantum Representation) Encoder Module.
Encodes classical 2D grayscale images into quantum states:
|I⟩ = (1/2^n) ∑ |C(Y,X)⟩ |Y⟩ |X⟩
"""

import math
from typing import Dict, Any, Union, List
import numpy as np
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister


class NEQREncoder:
    """
    Encodes 2^n x 2^n grayscale images into quantum circuits using NEQR.

    Qubit Layout:
    - Position Register: 2n qubits (qubits 0 .. 2n-1) representing (Y, X) coordinates
    - Grayscale Register: q qubits (qubits 2n .. 2n+q-1) representing pixel intensity C(Y,X)
    """

    def __init__(self, config: Union[dict, Any] = None, image_size: int = 16, grayscale_bits: int = 8):
        if config is not None:
            if isinstance(config, dict):
                img_cfg = config.get("image", {})
                self.image_size = int(img_cfg.get("cover_size", image_size))
                self.grayscale_bits = int(img_cfg.get("grayscale_bits", grayscale_bits))
            else:
                self.image_size = int(getattr(config.image, "cover_size", image_size))
                self.grayscale_bits = int(getattr(config.image, "grayscale_bits", grayscale_bits))
        else:
            self.image_size = image_size
            self.grayscale_bits = grayscale_bits

        if not (self.image_size > 0 and (self.image_size & (self.image_size - 1)) == 0):
            raise ValueError(f"Image size must be power of 2, got {self.image_size}")

        self.n = int(math.log2(self.image_size))
        self.position_qubits = 2 * self.n
        self.grayscale_qubits = self.grayscale_bits
        self.total_qubits = self.position_qubits + self.grayscale_qubits

    def encode(self, image: np.ndarray) -> QuantumCircuit:
        """
        Build a NEQR QuantumCircuit for the given image.
        Supports 2D grayscale or 3D RGB (uses first channel for state prep).
        For large images (e.g. >16x16), circuit gate count grows large;
        use encode_statevector for fast simulation.
        """
        img_2d = image[:, :, 0] if image.ndim == 3 else image
        if img_2d.shape != (self.image_size, self.image_size):
            raise ValueError(
                f"Image shape {img_2d.shape} does not match expected ({self.image_size}, {self.image_size})"
            )

        pos_reg = QuantumRegister(self.position_qubits, name="pos")
        gray_reg = QuantumRegister(self.grayscale_qubits, name="gray")
        qc = QuantumCircuit(pos_reg, gray_reg, name="NEQR_Image")

        # Step 1: Put all position qubits into uniform superposition
        for i in range(self.position_qubits):
            qc.h(pos_reg[i])

        # Step 2: Encode pixel values using Multi-Controlled X (mcx) gates
        pos_qubit_list = [pos_reg[i] for i in range(self.position_qubits)]

        for y in range(self.image_size):
            for x in range(self.image_size):
                pixel_val = int(img_2d[y, x])
                pos_val = (y << self.n) | x

                # Determine which position qubits need NOT gates to activate controls on pos_val
                inverted_controls: List[int] = []
                for p in range(self.position_qubits):
                    if not ((pos_val >> p) & 1):
                        inverted_controls.append(p)

                # Invert zero-control position qubits
                for p in inverted_controls:
                    qc.x(pos_reg[p])

                # Apply MCX to each grayscale qubit where pixel bit is 1
                for bit_idx in range(self.grayscale_qubits):
                    if (pixel_val >> bit_idx) & 1:
                        target_qubit = gray_reg[bit_idx]
                        qc.mcx(pos_qubit_list, target_qubit)

                # Restore inverted position qubits
                for p in inverted_controls:
                    qc.x(pos_reg[p])

        qc.barrier()
        return qc

    def encode_statevector(self, image: np.ndarray) -> np.ndarray:
        """
        Directly compute the exact NEQR statevector array for fast simulation.
        Optimized vectorized tile processing for high resolution (256x256 / 512x512).
        Statevector length = 2^(2n + q).
        Basis state |C(Y,X)⟩|Y,X⟩ has index (pixel_val << 2n) | (y << n | x).
        Amplitude = 1 / 2^n = 1 / image_size.
        """
        img_2d = image[:, :, 0] if image.ndim == 3 else image
        if img_2d.shape != (self.image_size, self.image_size):
            raise ValueError(
                f"Image shape {img_2d.shape} does not match expected ({self.image_size}, {self.image_size})"
            )

        dim = 1 << self.total_qubits
        statevector = np.zeros(dim, dtype=np.complex128)
        norm_factor = 1.0 / float(self.image_size)

        y_idx, x_idx = np.ogrid[: self.image_size, : self.image_size]
        pos_vals = (y_idx << self.n) | x_idx
        pixel_vals = img_2d.astype(np.int64)
        basis_indices = (pixel_vals << self.position_qubits) | pos_vals

        statevector[basis_indices.ravel()] = norm_factor
        return statevector

    def get_circuit_info(self, circuit: QuantumCircuit) -> Dict[str, Any]:
        """
        Extract quantum circuit complexity metrics.
        """
        gate_counts = dict(circuit.count_ops())
        return {
            "num_qubits": circuit.num_qubits,
            "gate_count": sum(gate_counts.values()),
            "circuit_depth": circuit.depth(),
            "num_parameters": circuit.num_parameters,
            "num_nonlocal_gates": circuit.num_nonlocal_gates(),
            "operations": gate_counts,
        }

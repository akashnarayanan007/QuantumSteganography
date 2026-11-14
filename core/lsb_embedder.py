"""
Q-LSB (Quantum Least Significant Bit) Embedder Module.
Embeds secret binary bitstreams into the least significant bit(s)
of NEQR quantum image registers using controlled Pauli-X / CNOT operations.
"""

import math
from typing import List, Union, Any, Tuple, Optional
import numpy as np
from qiskit import QuantumCircuit, QuantumRegister
from .image_utils import text_to_bits


class QLSBEmbedder:
    """
    Quantum LSB embedder for NEQR encoded images.
    Modifies quantum state amplitudes conditionally using MCX / Pauli-X gates.
    """

    def __init__(self, config: Union[dict, Any] = None):
        if config is not None:
            if isinstance(config, dict):
                emb_cfg = config.get("embedding", {})
                self.lsb_planes = int(emb_cfg.get("lsb_planes", 1))
                self.payload_type = str(emb_cfg.get("payload_type", "text"))
                self.secret_text = str(emb_cfg.get("secret_text", "AKASH_QIS"))
            else:
                self.lsb_planes = int(getattr(config.embedding, "lsb_planes", 1))
                self.payload_type = str(getattr(config.embedding, "payload_type", "text"))
                self.secret_text = str(getattr(config.embedding, "secret_text", "AKASH_QIS"))
        else:
            self.lsb_planes = 1
            self.payload_type = "text"
            self.secret_text = "AKASH_QIS"

    def prepare_payload(self, secret: Union[str, np.ndarray, None] = None, payload_type: Optional[str] = None) -> List[int]:
        """
        Convert secret payload (text or binary image array) to a flat list of binary bits (0 or 1).
        """
        p_type = payload_type or self.payload_type
        if p_type == "text":
            text = secret if isinstance(secret, str) else self.secret_text
            return text_to_bits(text)
        elif p_type == "image":
            if isinstance(secret, np.ndarray):
                return secret.flatten().astype(int).tolist()
            else:
                raise ValueError("Expected numpy array payload for payload_type='image'")
        else:
            raise ValueError(f"Unknown payload_type: {p_type}")

    def embed(
        self,
        circuit: QuantumCircuit,
        image: np.ndarray,
        payload_bits: List[int],
    ) -> Tuple[QuantumCircuit, int]:
        """
        Embed binary payload into a copy of the NEQR QuantumCircuit.
        Returns: (stego_circuit, num_pixels_modified)
        """
        stego_circuit = circuit.copy(name="Stego_NEQR_Image")
        img_2d = image[:, :, 0] if image.ndim == 3 else image
        image_size = img_2d.shape[0]
        n = int(math.log2(image_size))
        pos_qubits_count = 2 * n

        # Find registers
        pos_qubits = [stego_circuit.qubits[i] for i in range(pos_qubits_count)]
        # Grayscale LSB qubit is at index pos_qubits_count (qubit 2n)
        gray_lsb_qubit = stego_circuit.qubits[pos_qubits_count]

        modified_pixels = 0
        bit_idx = 0
        total_payload = len(payload_bits)

        for y in range(image_size):
            for x in range(image_size):
                if bit_idx >= total_payload:
                    break

                bit_to_embed = payload_bits[bit_idx]
                current_pixel = int(img_2d[y, x])
                current_lsb = current_pixel & 1

                if bit_to_embed != current_lsb:
                    modified_pixels += 1
                    pos_val = (y << n) | x

                    # Control inversion for 0-bits
                    inverted_controls: List[int] = []
                    for p in range(pos_qubits_count):
                        if not ((pos_val >> p) & 1):
                            inverted_controls.append(p)

                    # Invert
                    for p in inverted_controls:
                        stego_circuit.x(pos_qubits[p])

                    # Multi-controlled NOT on LSB qubit
                    stego_circuit.mcx(pos_qubits, gray_lsb_qubit)

                    # Restore
                    for p in inverted_controls:
                        stego_circuit.x(pos_qubits[p])

                bit_idx += 1
            if bit_idx >= total_payload:
                break

        return stego_circuit, modified_pixels

    def embed_statevector(
        self,
        statevector: np.ndarray,
        image: np.ndarray,
        payload_bits: List[int],
    ) -> Tuple[np.ndarray, int]:
        """
        Fast mode: Embed payload directly into statevector without building full circuit.
        Returns: (stego_statevector, num_pixels_modified)
        """
        stego_sv = np.copy(statevector)
        img_2d = image[:, :, 0] if image.ndim == 3 else image
        image_size = img_2d.shape[0]
        n = int(math.log2(image_size))
        pos_qubits_count = 2 * n

        modified_pixels = 0
        bit_idx = 0
        total_payload = len(payload_bits)

        for y in range(image_size):
            for x in range(image_size):
                if bit_idx >= total_payload:
                    break

                bit_to_embed = payload_bits[bit_idx]
                current_pixel = int(img_2d[y, x])
                current_lsb = current_pixel & 1

                if bit_to_embed != current_lsb:
                    modified_pixels += 1
                    new_pixel = current_pixel ^ 1  # Flip LSB

                    pos_val = (y << n) | x
                    old_basis_idx = (current_pixel << pos_qubits_count) | pos_val
                    new_basis_idx = (new_pixel << pos_qubits_count) | pos_val

                    # Transfer amplitude to target basis state
                    stego_sv[new_basis_idx] = stego_sv[old_basis_idx]
                    stego_sv[old_basis_idx] = 0.0

                bit_idx += 1
            if bit_idx >= total_payload:
                break

        return stego_sv, modified_pixels

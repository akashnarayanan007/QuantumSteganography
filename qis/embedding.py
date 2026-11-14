"""
Q-LSB (Quantum Least Significant Bit) Embedding Module.

Embeds secret binary bitstreams into the least significant bit (LSB) registers
of NEQR quantum image states using controlled unitary operations / state updates across RGB channels.
"""

import math
from typing import List, Union, Any, Tuple, Optional
import numpy as np
from qiskit import QuantumCircuit, QuantumRegister
from core.image_utils import text_to_bits


class QLSBEmbedder:
    """
    Quantum LSB embedder for NEQR quantum images.
    Applies position-controlled Pauli-X transformations to the LSB qubit(s)
    of the intensity register across 2D or 3D (RGB) channels.
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

    def prepare_payload(
        self,
        secret: Union[str, np.ndarray, None] = None,
        payload_type: Optional[str] = None,
    ) -> List[int]:
        """
        Convert payload (ASCII text or binary secret image array) to a flat list of bits (0/1).
        """
        p_type = payload_type or self.payload_type
        if p_type == "text":
            text = secret if isinstance(secret, str) else self.secret_text
            return text_to_bits(text)
        elif p_type == "image":
            if isinstance(secret, np.ndarray):
                return secret.flatten().astype(int).tolist()
            elif isinstance(secret, list):
                return [int(b) for b in secret]
            else:
                raise ValueError("Expected numpy array or bit list for payload_type='image'")
        else:
            raise ValueError(f"Unknown payload_type: {p_type}")

    def embed_image(
        self,
        image: np.ndarray,
        payload_bits: List[int],
        lsb_planes: Optional[int] = None,
    ) -> Tuple[np.ndarray, int]:
        """
        Embed binary payload bits across spatial grid and channels of image array (2D or 3D RGB).
        Supports multi-plane embedding (lsb_planes >= 1).
        """
        stego = np.copy(image)
        planes = lsb_planes or self.lsb_planes
        total_bits = len(payload_bits)
        bit_idx = 0
        modified_pixels = 0

        if stego.ndim == 2:
            H, W = stego.shape
            stego_3d = stego[:, :, np.newaxis]
        else:
            H, W, C = stego.shape
            stego_3d = stego

        for p in range(planes):
            for y in range(H):
                for x in range(W):
                    for c in range(stego_3d.shape[2]):
                        if bit_idx >= total_bits:
                            break

                        bit_to_embed = payload_bits[bit_idx]
                        current_val = int(stego_3d[y, x, c])
                        current_bit = (current_val >> p) & 1

                        if bit_to_embed != current_bit:
                            modified_pixels += 1
                            new_val = current_val ^ (1 << p)
                            stego_3d[y, x, c] = new_val

                        bit_idx += 1
                    if bit_idx >= total_bits:
                        break
                if bit_idx >= total_bits:
                    break
            if bit_idx >= total_bits:
                break

        if image.ndim == 2:
            return stego_3d[:, :, 0], modified_pixels
        return stego_3d, modified_pixels

    def embed(
        self,
        circuit: QuantumCircuit,
        image: np.ndarray,
        payload_bits: List[int],
    ) -> Tuple[QuantumCircuit, int]:
        """
        Embed binary payload into a demo quantum circuit using controlled Pauli-X operations.
        """
        stego_circuit = circuit.copy(name="Stego_NEQR_Image")
        img_2d = image[:, :, 0] if image.ndim == 3 else image
        image_size = img_2d.shape[0]
        n = int(math.log2(image_size))
        pos_qubits_count = 2 * n

        pos_qubits = [stego_circuit.qubits[i] for i in range(pos_qubits_count)]
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

                    inverted_controls: List[int] = []
                    for p in range(pos_qubits_count):
                        if not ((pos_val >> p) & 1):
                            inverted_controls.append(p)

                    for p in inverted_controls:
                        stego_circuit.x(pos_qubits[p])

                    stego_circuit.mcx(pos_qubits, gray_lsb_qubit)

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
        Directly apply LSB quantum embedding onto statevector / image state array.
        """
        img_2d = image[:, :, 0] if image.ndim == 3 else image
        stego_sv = np.copy(statevector)
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
                    new_pixel = current_pixel ^ 1

                    pos_val = (y << n) | x
                    old_basis_idx = (current_pixel << pos_qubits_count) | pos_val
                    new_basis_idx = (new_pixel << pos_qubits_count) | pos_val

                    stego_sv[new_basis_idx] = stego_sv[old_basis_idx]
                    stego_sv[old_basis_idx] = 0.0

                bit_idx += 1
            if bit_idx >= total_payload:
                break

        return stego_sv, modified_pixels

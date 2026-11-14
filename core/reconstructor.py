"""
Quantum Image Reconstructor Module.
Decodes quantum statevectors and measurement distributions into classical 2D pixel matrices.
"""

from typing import Dict, Union, Any
import numpy as np
from qiskit.quantum_info import Statevector


class ImageReconstructor:
    """
    Reconstructs classical 2D images from quantum statevectors or measurement counts.
    """

    def statevector_to_image(
        self,
        statevector: Union[Statevector, np.ndarray],
        image_size: int = 16,
        n: int = 4,
        q: int = 8,
        threshold: float = 1e-6,
    ) -> np.ndarray:
        """
        Convert quantum statevector into uint8 2D grayscale image.

        Qubit layout:
        - Position: lowest 2n bits (qubits 0..2n-1) -> pos_val = (y << n) | x
        - Grayscale: highest q bits (qubits 2n..2n+q-1) -> pixel_val
        """
        if isinstance(statevector, Statevector):
            data = statevector.data
        else:
            data = np.asarray(statevector)

        image = np.zeros((image_size, image_size), dtype=np.uint8)
        pos_mask = (1 << (2 * n)) - 1
        x_mask = (1 << n) - 1
        q_mask = (1 << q) - 1

        # Non-zero indices
        nonzero_indices = np.where(np.abs(data) > threshold)[0]

        for idx in nonzero_indices:
            idx = int(idx)
            pos_val = idx & pos_mask
            pixel_val = (idx >> (2 * n)) & q_mask

            y = (pos_val >> n) & x_mask
            x = pos_val & x_mask

            if 0 <= y < image_size and 0 <= x < image_size:
                image[y, x] = pixel_val

        return image

    def counts_to_image(
        self,
        counts: Dict[str, int],
        image_size: int = 16,
        n: int = 4,
        q: int = 8,
    ) -> np.ndarray:
        """
        Reconstruct image from shot measurement counts (for noisy simulation).
        Chooses the most probable grayscale value for each (y, x) position.
        """
        image = np.zeros((image_size, image_size), dtype=np.uint8)
        # Keep track of counts per (y, x): dict[(y, x), dict[pixel_val, count]]
        pixel_votes: Dict[tuple, Dict[int, int]] = {}

        total_qubits = 2 * n + q
        for bitstring, count in counts.items():
            # Remove any whitespace if formatted
            clean_str = bitstring.replace(" ", "")
            # Pad or ensure correct length
            clean_str = clean_str.zfill(total_qubits)
            val = int(clean_str, 2)

            pos_val = val & ((1 << (2 * n)) - 1)
            pixel_val = (val >> (2 * n)) & ((1 << q) - 1)

            y = (pos_val >> n) & ((1 << n) - 1)
            x = pos_val & ((1 << n) - 1)

            if 0 <= y < image_size and 0 <= x < image_size:
                pos_key = (y, x)
                if pos_key not in pixel_votes:
                    pixel_votes[pos_key] = {}
                pixel_votes[pos_key][pixel_val] = pixel_votes[pos_key].get(pixel_val, 0) + count

        for y in range(image_size):
            for x in range(image_size):
                pos_key = (y, x)
                if pos_key in pixel_votes and pixel_votes[pos_key]:
                    best_pixel = max(pixel_votes[pos_key].items(), key=lambda item: item[1])[0]
                    image[y, x] = best_pixel

        return image

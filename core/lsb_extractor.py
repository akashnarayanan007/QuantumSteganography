"""
Q-LSB (Quantum Least Significant Bit) Extractor Module.
Extracts embedded secret bits from NEQR statevectors or reconstructed stego images
and decodes them back to original text strings or binary images.
"""

import math
from typing import List, Union, Optional
import numpy as np
from .image_utils import bits_to_text
from .reconstructor import ImageReconstructor


class QLSBExtractor:
    """
    Extracts and decodes hidden payload from quantum statevectors or stego images.
    """

    def __init__(self):
        self.reconstructor = ImageReconstructor()

    def extract_from_statevector(
        self,
        statevector: np.ndarray,
        image_size: int,
        grayscale_bits: int = 8,
    ) -> List[int]:
        """
        Reconstruct image from statevector and extract LSB bitstream in raster order.
        """
        n = int(math.log2(image_size))
        stego_image = self.reconstructor.statevector_to_image(
            statevector, image_size=image_size, n=n, q=grayscale_bits
        )
        return self.extract_from_image(stego_image)

    def extract_from_image(
        self,
        image: np.ndarray,
        num_bits: Optional[int] = None,
    ) -> List[int]:
        """
        Extract LSB from each pixel in raster order.
        """
        flat_pixels = image.flatten()
        lsb_bits = [int(p & 1) for p in flat_pixels]
        if num_bits is not None:
            return lsb_bits[:num_bits]
        return lsb_bits

    def decode_payload(
        self,
        bits: List[int],
        payload_type: str = "text",
        payload_length: Optional[int] = None,
        image_size: int = 16,
    ) -> Union[str, np.ndarray]:
        """
        Decode extracted bits into ASCII string or binary image.
        """
        if payload_type == "text":
            if payload_length is not None:
                needed_bits = payload_length * 8
                return bits_to_text(bits[:needed_bits])
            return bits_to_text(bits)

        elif payload_type == "image":
            secret_dim = max(2, image_size // 2)
            total_pixels = secret_dim * secret_dim
            raw_bits = bits[:total_pixels]
            if len(raw_bits) < total_pixels:
                raw_bits.extend([0] * (total_pixels - len(raw_bits)))
            bin_arr = np.array(raw_bits, dtype=np.uint8).reshape((secret_dim, secret_dim))
            return bin_arr

        else:
            raise ValueError(f"Unknown payload_type: {payload_type}")

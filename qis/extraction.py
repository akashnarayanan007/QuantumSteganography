"""
Q-LSB (Quantum Least Significant Bit) Extraction Module.

Extracts hidden payloads from quantum stego statevectors or reconstructed stego images (RGB & Grayscale)
using inverse quantum measurement principles and LSB readout.
"""

import math
from typing import List, Union, Optional, Dict, Any
import numpy as np
from core.image_utils import bits_to_text
from core.reconstructor import ImageReconstructor


class QLSBExtractor:
    """
    Extracts embedded payload bits from quantum stego states or stego image arrays.
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
        Extract LSB bitstream from quantum statevector.
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
        lsb_planes: int = 1,
    ) -> List[int]:
        """
        Extract LSB bits from each pixel/channel in raster order across lsb_planes.
        """
        if image.ndim == 2:
            img_3d = image[:, :, np.newaxis]
        else:
            img_3d = image

        H, W, C = img_3d.shape
        extracted_bits: List[int] = []
        bit_idx = 0

        for p in range(lsb_planes):
            for y in range(H):
                for x in range(W):
                    for c in range(C):
                        if num_bits is not None and bit_idx >= num_bits:
                            break
                        val = int(img_3d[y, x, c])
                        bit = (val >> p) & 1
                        extracted_bits.append(bit)
                        bit_idx += 1
                    if num_bits is not None and bit_idx >= num_bits:
                        break
                if num_bits is not None and bit_idx >= num_bits:
                    break
            if num_bits is not None and bit_idx >= num_bits:
                break

        return extracted_bits

    def decode_payload(
        self,
        bits: List[int],
        payload_type: str = "image",
        payload_length: Optional[int] = None,
        image_meta: Optional[Dict[str, Any]] = None,
        image_size: int = 128,
    ) -> Union[str, np.ndarray]:
        """
        Decode extracted bitstream into original ASCII text or secret image array with proper [0, 255] scaling.
        """
        if payload_type == "text":
            if payload_length is not None:
                needed_bits = payload_length * 8
                return bits_to_text(bits[:needed_bits])
            return bits_to_text(bits)

        elif payload_type == "image":
            meta = image_meta or {}
            target_shape = meta.get("shape", None)
            is_binary = meta.get("is_binary", True)

            if target_shape is not None:
                shape = tuple(target_shape)
            else:
                secret_dim = max(4, image_size // 2)
                shape = (secret_dim, secret_dim)

            total_elements = int(np.prod(shape))

            if is_binary:
                raw_bits = bits[:total_elements]
                if len(raw_bits) < total_elements:
                    raw_bits.extend([0] * (total_elements - len(raw_bits)))
                bin_arr = np.array(raw_bits, dtype=np.uint8).reshape(shape)
                # Scale {0, 1} to {0, 255} for visual clarity
                secret_img = (bin_arr * 255).astype(np.uint8)
                return secret_img
            else:
                needed_bits = total_elements * 8
                raw_bits = bits[:needed_bits]
                if len(raw_bits) < needed_bits:
                    raw_bits.extend([0] * (needed_bits - len(raw_bits)))
                bytes_arr = np.packbits(np.array(raw_bits, dtype=np.uint8))
                secret_img = bytes_arr[:total_elements].reshape(shape)
                return secret_img
        else:
            raise ValueError(f"Unknown payload_type: {payload_type}")

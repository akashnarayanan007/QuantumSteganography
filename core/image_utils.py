"""
Image utility functions for Quantum Image Steganography.
Handles loading, resizing, synthetic generation, CLAHE enhancement,
and text/image payload binary bit conversions with full RGB support.
"""

from pathlib import Path
from typing import List, Union, Tuple, Dict, Any
import numpy as np
from PIL import Image
import cv2


def load_cover_image(
    path: Union[str, Path],
    size: int = 16,
    color_mode: str = "RGB",
    enhance_contrast: bool = False,
) -> np.ndarray:
    """
    Load cover image, convert to RGB or Grayscale, and resize to (size, size) using
    high-quality anti-aliasing (LANCZOS) resampling.
    Size must be a power of 2.
    """
    path_obj = Path(path)
    if not (size > 0 and (size & (size - 1)) == 0):
        raise ValueError(f"Image size must be a power of 2 (e.g. 4, 8, 16, 32, 128, 256, 512), got {size}")

    if not path_obj.exists():
        raise FileNotFoundError(f"Cover image not found at: {path_obj}")

    try:
        with Image.open(path_obj) as img:
            if color_mode.upper() == "RGB":
                rgb_img = img.convert("RGB")
                resized = rgb_img.resize((size, size), Image.Resampling.LANCZOS)
                arr = np.array(resized, dtype=np.uint8)
            else:
                gray_img = img.convert("L")
                resized = gray_img.resize((size, size), Image.Resampling.LANCZOS)
                arr = np.array(resized, dtype=np.uint8)

            if enhance_contrast:
                arr = apply_clahe_preprocessing(arr)
            return arr
    except Exception as e:
        raise IOError(f"Failed to load/process cover image from {path_obj}: {str(e)}") from e


def load_secret_image(
    path: Union[str, Path],
    max_capacity_bits: int = 16384,
    color_mode: str = "RGB",
    is_binary: bool = True,
) -> Tuple[np.ndarray, List[int], Dict[str, Any]]:
    """
    Load secret image, resize cleanly with anti-aliasing (LANCZOS) to fit max_capacity_bits,
    and return (secret_array, bit_list, metadata_dict).
    """
    path_obj = Path(path)
    if not path_obj.exists():
        raise FileNotFoundError(f"Secret image not found at: {path_obj}")

    try:
        with Image.open(path_obj) as img:
            mode = color_mode.upper()
            if mode == "RGB":
                converted = img.convert("RGB")
                num_channels = 3
            else:
                converted = img.convert("L")
                num_channels = 1

            if is_binary:
                target_pixels = max(1, max_capacity_bits // num_channels)
                side = max(4, int(np.sqrt(target_pixels)))
                h_dim, w_dim = side, side
                while h_dim * w_dim * num_channels > max_capacity_bits and h_dim > 2:
                    h_dim -= 1
                    w_dim -= 1

                resized = converted.resize((w_dim, h_dim), Image.Resampling.LANCZOS)
                arr = np.array(resized, dtype=np.uint8)
                binary_arr = (arr > 128).astype(np.uint8)
                bits = binary_arr.flatten().tolist()
                meta = {
                    "shape": list(binary_arr.shape),
                    "is_binary": True,
                    "bits_count": len(bits),
                    "color_mode": mode,
                }
                return binary_arr, bits, meta
            else:
                target_bytes = max(1, max_capacity_bits // 8)
                target_pixels = max(1, target_bytes // num_channels)
                side = max(4, int(np.sqrt(target_pixels)))
                h_dim, w_dim = side, side
                while h_dim * w_dim * num_channels * 8 > max_capacity_bits and h_dim > 2:
                    h_dim -= 1
                    w_dim -= 1

                resized = converted.resize((w_dim, h_dim), Image.Resampling.LANCZOS)
                arr = np.array(resized, dtype=np.uint8)
                bits = np.unpackbits(arr.flatten()).tolist()
                meta = {
                    "shape": list(arr.shape),
                    "is_binary": False,
                    "bits_count": len(bits),
                    "color_mode": mode,
                }
                return arr, bits, meta
    except Exception as e:
        raise IOError(f"Failed to load/process secret image from {path_obj}: {str(e)}") from e


def text_to_bits(text: str) -> List[int]:
    """Convert ASCII string into a flat list of binary bits."""
    bits: List[int] = []
    for char in text:
        ascii_val = ord(char)
        binary_str = format(ascii_val, "08b")
        bits.extend([int(b) for b in binary_str])
    return bits


def bits_to_text(bits: List[int]) -> str:
    """Convert a list of binary bits back to ASCII text."""
    chars: List[str] = []
    num_bytes = len(bits) // 8
    for i in range(num_bytes):
        byte_bits = bits[i * 8 : (i + 1) * 8]
        byte_val = 0
        for bit in byte_bits:
            byte_val = (byte_val << 1) | int(bit)
        if 32 <= byte_val <= 126 or byte_val in (9, 10, 13):
            chars.append(chr(byte_val))
        else:
            chars.append("?")
    return "".join(chars)


def generate_synthetic_cover(
    size: int = 16,
    color_mode: str = "RGB",
    save_path: Union[str, Path, None] = None,
) -> np.ndarray:
    """Create a synthetic cover image (RGB or Grayscale)."""
    if not (size > 0 and (size & (size - 1)) == 0):
        raise ValueError(f"Size must be a power of 2, got {size}")

    y, x = np.mgrid[0:size, 0:size]
    gradient = (x + y) / (2.0 * (size - 1))
    texture = np.sin(x * np.pi / 2.0) * np.cos(y * np.pi / 2.0) * 0.15
    combined = gradient + texture
    norm = (combined - combined.min()) / (combined.max() - combined.min() + 1e-8)
    channel_base = (30 + norm * (220 - 30)).astype(np.uint8)

    if color_mode.upper() == "RGB":
        r = channel_base
        g = np.flipud(channel_base)
        b = np.fliplr(channel_base)
        pixel_vals = np.stack([r, g, b], axis=-1)
        mode_str = "RGB"
    else:
        pixel_vals = channel_base
        mode_str = "L"

    if save_path:
        save_path_obj = Path(save_path)
        save_path_obj.parent.mkdir(parents=True, exist_ok=True)
        img = Image.fromarray(pixel_vals, mode=mode_str)
        img.save(save_path_obj)

    return pixel_vals


def generate_synthetic_secret(
    size: int = 16,
    color_mode: str = "RGB",
    save_path: Union[str, Path, None] = None,
) -> np.ndarray:
    """Create a synthetic secret pattern image."""
    secret_dim = max(4, size // 2)
    pattern = np.zeros((secret_dim, secret_dim), dtype=np.uint8)

    for i in range(secret_dim):
        for j in range(secret_dim):
            if (i // 2 + j // 2) % 2 == 0:
                pattern[i, j] = 1

    mid = secret_dim // 2
    pattern[mid - 1 : mid + 1, :] = 1
    pattern[:, mid - 1 : mid + 1] = 1

    if color_mode.upper() == "RGB":
        r = pattern * 255
        g = np.rot90(pattern) * 255
        b = (1 - pattern) * 255
        img_arr = np.stack([r, g, b], axis=-1).astype(np.uint8)
        mode_str = "RGB"
    else:
        img_arr = (pattern * 255).astype(np.uint8)
        mode_str = "L"

    if save_path:
        save_path_obj = Path(save_path)
        save_path_obj.parent.mkdir(parents=True, exist_ok=True)
        img = Image.fromarray(img_arr, mode=mode_str)
        img.save(save_path_obj)

    return img_arr


def apply_clahe_preprocessing(image: np.ndarray, clip_limit: float = 2.0, tile_grid_size: int = 4) -> np.ndarray:
    """Apply Contrast Limited Adaptive Histogram Equalization (CLAHE)."""
    if len(image.shape) == 2:
        grid = (max(1, min(tile_grid_size, image.shape[0])), max(1, min(tile_grid_size, image.shape[1])))
        clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=grid)
        return clahe.apply(image)
    elif len(image.shape) == 3:
        lab = cv2.cvtColor(image, cv2.COLOR_RGB2LAB)
        l, a, b = cv2.split(lab)
        grid = (max(1, min(tile_grid_size, image.shape[0])), max(1, min(tile_grid_size, image.shape[1])))
        clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=grid)
        cl = clahe.apply(l)
        limg = cv2.merge((cl, a, b))
        return cv2.cvtColor(limg, cv2.COLOR_LAB2RGB)
    return image

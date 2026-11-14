"""
Unit tests for Q-LSB embedding and extraction modules.
Validates payload conversion, quantum state modification, and lossless recovery.
"""

import numpy as np
import pytest
from core.image_utils import text_to_bits, bits_to_text, generate_synthetic_cover
from core.neqr_encoder import NEQREncoder
from core.lsb_embedder import QLSBEmbedder
from core.lsb_extractor import QLSBExtractor
from metrics.psnr_ssim import compute_bit_error_rate


def test_text_to_bits_roundtrip():
    """Verify lossless ASCII-binary bit conversion."""
    sample_texts = ["AKASH_QIS", "Quantum123!", "Hello World", "Steganography"]
    for text in sample_texts:
        bits = text_to_bits(text)
        assert len(bits) == len(text) * 8
        recovered = bits_to_text(bits)
        assert recovered == text


def test_lsb_embedder_and_extractor_full_cycle():
    """Verify embedding 'AKASH_QIS' into a 16x16 cover image achieves BER = 0.0."""
    image_size = 16
    cover_image = generate_synthetic_cover(image_size)
    encoder = NEQREncoder(image_size=image_size, grayscale_bits=8)
    sv = encoder.encode_statevector(cover_image)

    secret_text = "AKASH_QIS"
    embedder = QLSBEmbedder()
    payload_bits = embedder.prepare_payload(secret_text, payload_type="text")

    stego_sv, mods = embedder.embed_statevector(sv, cover_image, payload_bits)
    assert stego_sv.shape == sv.shape
    assert np.isclose(np.sum(np.abs(stego_sv) ** 2), 1.0, atol=1e-6)

    extractor = QLSBExtractor()
    extracted_bits = extractor.extract_from_statevector(stego_sv, image_size=image_size, grayscale_bits=8)
    recovered_text = extractor.decode_payload(
        extracted_bits, payload_type="text", payload_length=len(secret_text), image_size=image_size
    )

    assert recovered_text == secret_text
    ber = compute_bit_error_rate(payload_bits, extracted_bits[:len(payload_bits)])
    assert ber == 0.0


def test_binary_image_payload_embedding():
    """Verify embedding and recovering a 2D binary image pattern."""
    image_size = 16
    cover_image = generate_synthetic_cover(image_size)
    encoder = NEQREncoder(image_size=image_size, grayscale_bits=8)
    sv = encoder.encode_statevector(cover_image)

    # 8x8 binary secret pattern
    secret_dim = 8
    secret_img = np.zeros((secret_dim, secret_dim), dtype=np.uint8)
    secret_img[::2, ::2] = 1
    secret_img[1::2, 1::2] = 1

    embedder = QLSBEmbedder()
    payload_bits = embedder.prepare_payload(secret_img, payload_type="image")
    assert len(payload_bits) == 64

    stego_sv, _ = embedder.embed_statevector(sv, cover_image, payload_bits)

    extractor = QLSBExtractor()
    extracted_bits = extractor.extract_from_statevector(stego_sv, image_size=image_size, grayscale_bits=8)
    recovered_img = extractor.decode_payload(
        extracted_bits, payload_type="image", image_size=image_size
    )

    assert isinstance(recovered_img, np.ndarray)
    assert recovered_img.shape == (secret_dim, secret_dim)
    assert np.array_equal(secret_img, recovered_img)

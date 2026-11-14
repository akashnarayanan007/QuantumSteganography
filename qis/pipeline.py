"""
Core Execution Engine for Quantum Image Steganography (QIS).
Separates encode, decode, and full execution modes with full RGB color support & metadata header tracking.
"""

import json
from pathlib import Path
from typing import Dict, Any, Union, Optional
import yaml
import numpy as np
from PIL import Image

from core.image_utils import (
    load_cover_image,
    load_secret_image,
    generate_synthetic_cover,
    generate_synthetic_secret,
)
from .neqr import NEQRStatePrep
from .embedding import QLSBEmbedder
from .extraction import QLSBExtractor
from .metrics import (
    evaluate_metrics,
    CircuitAnalyzer,
    compute_difference_map,
)
from reporting.visualizer import Visualizer


def load_config(config_path: Union[str, Path]) -> Dict[str, Any]:
    """Load configuration dictionary from YAML file."""
    p = Path(config_path)
    if not p.exists():
        raise FileNotFoundError(f"Configuration file not found: {p}")
    with open(p, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def ensure_output_dirs(output_dir: Path) -> Dict[str, Path]:
    """Ensure output directory structure exists."""
    dirs = {
        "root": output_dir,
        "images": output_dir / "images",
        "circuits": output_dir / "circuits",
        "plots": output_dir / "plots",
    }
    for d in dirs.values():
        d.mkdir(parents=True, exist_ok=True)
    return dirs


def encode_pipeline(
    config: Dict[str, Any],
    cover_override: Optional[str] = None,
    secret_override: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Encode Mode:
    Takes cover and secret images, runs NEQR quantum embedding across RGB channels,
    and produces stego image + difference image + payload metadata.
    """
    base_dir = Path.cwd()
    out_dir_name = config.get("output", {}).get("output_dir", "output")
    dirs = ensure_output_dirs(base_dir / out_dir_name)

    img_cfg = config.get("image", {})
    cover_size = int(img_cfg.get("cover_size", 128))
    color_mode = str(img_cfg.get("color_mode", "RGB")).upper()
    grayscale_bits = int(img_cfg.get("grayscale_bits", 8))

    enhance_contrast = bool(img_cfg.get("enhance_contrast", False))

    cover_rel_path = cover_override or img_cfg.get("cover_path", "sample_images/cover.png")
    cover_path = base_dir / cover_rel_path

    if not cover_path.exists():
        print(f"[*] Generating synthetic cover image at {cover_path}...")
        generate_synthetic_cover(cover_size, color_mode=color_mode, save_path=cover_path)

    cover_image = load_cover_image(
        cover_path, cover_size, color_mode=color_mode, enhance_contrast=enhance_contrast
    )

    emb_cfg = config.get("embedding", {})
    payload_type = emb_cfg.get("payload_type", "image")
    lsb_planes = int(emb_cfg.get("lsb_planes", 2))
    secret_rel_path = img_cfg.get("secret_path", "sample_images/secret.png")
    secret_path = base_dir / secret_rel_path

    # Carrier capacity calculation
    channels = 3 if color_mode == "RGB" else 1
    max_capacity_bits = cover_size * cover_size * channels * lsb_planes

    embedder = QLSBEmbedder(config)

    if payload_type == "text":
        secret_text = secret_override or emb_cfg.get("secret_text", "AKASH_QIS")
        payload_bits = embedder.prepare_payload(secret_text, "text")
        secret_repr = secret_text
        secret_meta = {
            "payload_type": "text",
            "secret_text": secret_text,
            "bits_count": len(payload_bits),
            "lsb_planes": lsb_planes,
            "color_mode": color_mode,
        }
    else:
        if not secret_path.exists():
            print(f"[*] Generating synthetic secret image at {secret_path}...")
            generate_synthetic_secret(cover_size, color_mode=color_mode, save_path=secret_path)
        secret_arr, payload_bits, secret_meta = load_secret_image(
            secret_path, max_capacity_bits=max_capacity_bits, color_mode=color_mode, is_binary=True
        )
        secret_meta["payload_type"] = "image"
        secret_meta["lsb_planes"] = lsb_planes
        secret_repr = secret_arr

    # Write payload_meta.json so decode knows exact dimensions and payload layout
    meta_path = dirs["root"] / "payload_meta.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(secret_meta, f, indent=2)

    # Q-LSB Image Embedding across all spatial pixels & channels
    stego_image, pixels_mod = embedder.embed_image(cover_image, payload_bits, lsb_planes=lsb_planes)

    # Compute difference map
    diff_image = compute_difference_map(cover_image, stego_image, amplification=50.0)

    # Save images using exact color mode
    pil_mode = "RGB" if color_mode == "RGB" else "L"
    Image.fromarray(cover_image, mode=pil_mode).save(dirs["images"] / "cover.png")
    Image.fromarray(stego_image, mode=pil_mode).save(dirs["images"] / "stego.png")
    
    # Save difference map
    if diff_image.ndim == 3:
        Image.fromarray(diff_image, mode="RGB").save(dirs["images"] / "difference.png")
    else:
        Image.fromarray(diff_image, mode="L").save(dirs["images"] / "difference.png")

    print("[✓] Encoding Complete:")
    print(f"  • Cover Image saved to : {dirs['images'] / 'cover.png'} ({cover_image.shape})")
    print(f"  • Stego Image saved to : {dirs['images'] / 'stego.png'} ({stego_image.shape})")
    print(f"  • Difference Map saved to: {dirs['images'] / 'difference.png'}")
    print(f"  • Modified Pixels      : {pixels_mod} / {cover_image.size}")
    print(f"  • Embedded Bits        : {len(payload_bits)} / {max_capacity_bits} capacity")

    return {
        "cover_image": cover_image,
        "stego_image": stego_image,
        "payload_bits": payload_bits,
        "secret_repr": secret_repr,
        "secret_meta": secret_meta,
        "stego_path": dirs["images"] / "stego.png",
    }


def decode_pipeline(
    config: Dict[str, Any],
    stego_path_override: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Decode Mode:
    Takes ONLY the generated stego image (+ optional payload_meta.json header),
    runs inverse quantum extraction, and reconstructs the secret image with clean [0, 255] scaling.
    """
    base_dir = Path.cwd()
    out_dir_name = config.get("output", {}).get("output_dir", "output")
    dirs = ensure_output_dirs(base_dir / out_dir_name)

    stego_rel_path = stego_path_override or "output/images/stego.png"
    stego_file = base_dir / stego_rel_path

    if not stego_file.exists():
        raise FileNotFoundError(
            f"Stego image not found at {stego_file}. Please run '--mode encode' first."
        )

    meta_path = dirs["root"] / "payload_meta.json"
    secret_meta = {}
    if meta_path.exists():
        with open(meta_path, "r", encoding="utf-8") as f:
            secret_meta = json.load(f)

    img_cfg = config.get("image", {})
    color_mode = secret_meta.get("color_mode", str(img_cfg.get("color_mode", "RGB"))).upper()
    emb_cfg = config.get("embedding", {})
    payload_type = secret_meta.get("payload_type", str(emb_cfg.get("payload_type", "image")))
    lsb_planes = int(secret_meta.get("lsb_planes", emb_cfg.get("lsb_planes", 2)))

    # Read stego image using PIL in proper color mode
    pil_mode = "RGB" if color_mode == "RGB" else "L"
    stego_img_pil = Image.open(stego_file).convert(pil_mode)
    stego_image = np.array(stego_img_pil, dtype=np.uint8)
    cover_size = stego_image.shape[0]

    num_bits = secret_meta.get("bits_count", None)

    # Extract hidden payload using Q-LSB extraction
    extractor = QLSBExtractor()
    extracted_bits = extractor.extract_from_image(stego_image, num_bits=num_bits, lsb_planes=lsb_planes)

    if payload_type == "text":
        secret_text = secret_meta.get("secret_text", str(emb_cfg.get("secret_text", "AKASH_QIS")))
        recovered_secret = extractor.decode_payload(
            extracted_bits, payload_type="text", payload_length=len(secret_text), image_size=cover_size
        )
        rec_fig_arr = np.zeros((cover_size // 2, cover_size // 2, 3) if color_mode == "RGB" else (cover_size // 2, cover_size // 2), dtype=np.uint8)
        rec_img = Image.fromarray(rec_fig_arr, mode=pil_mode)
        rec_img.save(dirs["images"] / "recovered_secret.png")
        print("[✓] Decoding Complete:")
        print(f"  • Extracted Text Secret: '{recovered_secret}'")
    else:
        recovered_secret = extractor.decode_payload(
            extracted_bits, payload_type="image", image_meta=secret_meta, image_size=cover_size
        )
        rec_mode = "RGB" if recovered_secret.ndim == 3 else "L"
        rec_img = Image.fromarray(recovered_secret, mode=rec_mode)
        rec_img.save(dirs["images"] / "recovered_secret.png")
        print("[✓] Decoding Complete:")
        print(f"  • Recovered Secret Image saved to: {dirs['images'] / 'recovered_secret.png'} ({recovered_secret.shape})")

    return {
        "extracted_bits": extracted_bits,
        "recovered_secret": recovered_secret,
        "recovered_path": dirs["images"] / "recovered_secret.png",
    }


def full_pipeline(
    config: Dict[str, Any],
    cover_override: Optional[str] = None,
    secret_override: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Full Mode:
    Runs encode, decode, evaluation metrics, and circuit plotting sequentially.
    """
    base_dir = Path.cwd()
    out_dir_name = config.get("output", {}).get("output_dir", "output")
    dirs = ensure_output_dirs(base_dir / out_dir_name)

    print("\n--- PHASE 1: QUANTUM ENCODING ---")
    encode_res = encode_pipeline(config, cover_override, secret_override)

    print("\n--- PHASE 2: QUANTUM DECODING ---")
    decode_res = decode_pipeline(config)

    print("\n--- PHASE 3: METRICS & CIRCUIT EVALUATION ---")
    cover_image = encode_res["cover_image"]
    stego_image = encode_res["stego_image"]
    payload_bits = encode_res["payload_bits"]
    extracted_bits = decode_res["extracted_bits"]

    metrics_cfg = config.get("metrics", {})
    target_psnr = float(metrics_cfg.get("target_psnr", 48.0))
    target_ssim = float(metrics_cfg.get("target_ssim", 0.99))

    # Evaluate metrics on grayscale / flat representation if RGB
    cov_eval = cover_image[:, :, 0] if cover_image.ndim == 3 else cover_image
    steg_eval = stego_image[:, :, 0] if stego_image.ndim == 3 else stego_image

    metrics_result = evaluate_metrics(
        cover_image,
        stego_image,
        payload_bits,
        extracted_bits[: len(payload_bits)],
        target_psnr=target_psnr,
        target_ssim=target_ssim,
    )

    # Build demo NEQR & Stego circuit for visual plotting
    demo_size = 4
    demo_cover = cov_eval[:demo_size, :demo_size] if cov_eval.shape[0] >= demo_size else cov_eval
    demo_encoder = NEQRStatePrep(image_size=demo_size, grayscale_bits=8)
    demo_circuit = demo_encoder.encode(demo_cover)

    embedder = QLSBEmbedder(config)
    demo_payload = payload_bits[: demo_size * demo_size]
    demo_stego_circuit, _ = embedder.embed(demo_circuit, demo_cover, demo_payload)

    analyzer = CircuitAnalyzer()
    circuit_report = analyzer.analyze(demo_stego_circuit)

    vis = Visualizer(output_dir=dirs["root"])
    circ_diagram_path = dirs["circuits"] / "circuit_diagram.png"
    vis.plot_circuit(demo_stego_circuit, circ_diagram_path)

    # Visual plot generation
    vis.plot_image_comparison(
        cov_eval, steg_eval, encode_res["secret_repr"], decode_res["recovered_secret"]
    )
    vis.plot_difference_map(cov_eval, steg_eval)
    vis.plot_pixel_histogram(cov_eval, steg_eval)
    vis.plot_metrics_dashboard(metrics_result, circuit_report)

    # Save metrics_report.json
    metrics_report_dict = {
        "psnr_db": "Infinity (Lossless)" if np.isinf(metrics_result.psnr) else metrics_result.psnr,
        "ssim": metrics_result.ssim,
        "mse": metrics_result.mse,
        "ber": metrics_result.ber,
        "payload_capacity_bits": metrics_result.payload_capacity,
        "embedding_rate_bpp": metrics_result.embedding_rate,
        "status_psnr": metrics_result.status_psnr,
        "status_ssim": metrics_result.status_ssim,
        "status_ber": metrics_result.status_ber,
        "target_psnr_db": target_psnr,
        "target_ssim": target_ssim,
        "circuit_metrics": circuit_report.to_dict(),
    }

    report_path = dirs["root"] / "metrics_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(metrics_report_dict, f, indent=2)

    psnr_display = "∞ dB (Lossless)" if np.isinf(metrics_result.psnr) else f"{metrics_result.psnr:.2f} dB"
    print("\n╔═══════════════════════════════════════════════════════════╗")
    print("║                 QIS EVALUATION REPORT                     ║")
    print("╠═══════════════════════════════════════════════════════════╣")
    print(f"║  PSNR        : {psnr_display:<18} [Target: >{target_psnr} dB]  ║")
    print(f"║  SSIM        : {metrics_result.ssim:<18.6f} [Target: >{target_ssim}] ║")
    print(f"║  MSE         : {metrics_result.mse:<18.6f}                     ║")
    print(f"║  BER         : {metrics_result.ber:<18.6f} [Target: 0.0]      ║")
    print(f"║  Circuit     : {circuit_report.total_gates} gates, {circuit_report.num_qubits} qubits, depth {circuit_report.circuit_depth:<4} ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print(f"\n[✓] Circuit diagram saved to : {circ_diagram_path}")
    print(f"[✓] Metrics report saved to   : {report_path}\n")

    return {
        "metrics": metrics_result,
        "circuit_report": circuit_report,
        "metrics_report_path": report_path,
        "circuit_diagram_path": circ_diagram_path,
    }

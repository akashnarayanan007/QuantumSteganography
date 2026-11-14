# Sample Images Directory

This directory contains cover and secret sample images used for Quantum Image Steganography testing.

## Files
- `cover.png`: 16x16 (or custom 2^n x 2^n) grayscale cover image.
- `secret.png`: 8x8 binary payload image.

## How to replace with custom images:
1. Place any image (PNG, JPG, BMP) into this directory.
2. Update the `config.yaml` with your file path:
   ```yaml
   image:
     cover_size: 16
     cover_path: "sample_images/your_cover.png"
     secret_path: "sample_images/your_secret.png"
   ```
3. Or pass custom image paths via CLI:
   ```bash
   python main.py --cover sample_images/your_cover.png --mode full
   ```
The system will automatically resize cover images to $2^n \times 2^n$ and binarize secret images.

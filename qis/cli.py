"""
Command Line Interface (CLI) for Quantum Image Steganography (QIS).
"""

import argparse
import sys
from pathlib import Path

# Force UTF-8 stdout for Windows consoles
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from qis import (
    load_config,
    encode_pipeline,
    decode_pipeline,
    full_pipeline,
)

BANNER = """
╔═════════════════════════════════════════════════════════════╗
║         ⚛  Quantum Image Steganography (QIS)                ║
║            NEQR + Q-LSB Secure Data Hiding                  ║
║      Amrita School of Computing | QIS Lab Research          ║
╚═════════════════════════════════════════════════════════════╝
"""


def main():
    parser = argparse.ArgumentParser(
        prog="qis",
        description="Modular Quantum Image Steganography (NEQR + Q-LSB)",
    )
    parser.add_argument(
        "--config",
        type=str,
        default="config.yaml",
        help="Path to YAML configuration file",
    )
    parser.add_argument(
        "--mode",
        type=str,
        default="full",
        choices=["encode", "decode", "full", "encode-only", "decode-only"],
        help="Pipeline execution mode: encode, decode, or full",
    )
    parser.add_argument(
        "--cover",
        type=str,
        default=None,
        help="Override cover image path",
    )
    parser.add_argument(
        "--secret",
        type=str,
        default=None,
        help="Override secret payload (image path or text)",
    )
    parser.add_argument(
        "--stego",
        type=str,
        default=None,
        help="Override stego image path for decoding",
    )

    args = parser.parse_args()

    print(BANNER)

    cfg_path = Path(args.config)
    if not cfg_path.is_absolute():
        # Check current working directory, then check parent directory of this module
        if not cfg_path.exists():
            pkg_cfg = Path(__file__).resolve().parent.parent / "config.yaml"
            if pkg_cfg.exists():
                cfg_path = pkg_cfg
            else:
                cfg_path = Path.cwd() / cfg_path
        else:
            cfg_path = Path.cwd() / cfg_path

    try:
        config = load_config(cfg_path)
    except Exception as e:
        print(f"[!] Error loading configuration file '{cfg_path}': {e}", file=sys.stderr)
        sys.exit(1)

    mode = args.mode.lower()

    try:
        if mode in ("encode", "encode-only"):
            encode_pipeline(
                config=config,
                cover_override=args.cover,
                secret_override=args.secret,
            )
        elif mode in ("decode", "decode-only"):
            decode_pipeline(
                config=config,
                stego_path_override=args.stego,
            )
        elif mode == "full":
            full_pipeline(
                config=config,
                cover_override=args.cover,
                secret_override=args.secret,
            )
        else:
            print(f"[!] Invalid mode: {mode}", file=sys.stderr)
            sys.exit(1)
    except Exception as e:
        print(f"\n[!] Pipeline execution error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()


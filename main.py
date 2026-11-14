"""
Main CLI Application for Quantum Image Steganography (QIS).

Supports independent execution modes:
1. python main.py --mode encode
2. python main.py --mode decode
3. python main.py --mode full
"""

from qis.cli import main

if __name__ == "__main__":
    main()

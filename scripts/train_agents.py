#!/usr/bin/env python
from src.ml.train import train
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


if __name__ == "__main__":
    # Soporte para --mode historical
    mode = "historical"
    if len(sys.argv) > 1:
        for i, arg in enumerate(sys.argv):
            if arg == "--mode" and i + 1 < len(sys.argv):
                mode = sys.argv[i+1]
            elif arg.startswith("--mode="):
                mode = arg.split("=")[1]

    train(mode=mode)

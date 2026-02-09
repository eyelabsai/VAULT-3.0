#!/usr/bin/env python3
"""
Swap deployed model by copying archived .pkl files to root.

Usage:
    python swap_model.py                    # List available models
    python swap_model.py gestalt-24f-756c   # Swap to that model
    python swap_model.py gestalt-24f-756c --push  # Swap + git push to deploy
"""

import os
import sys
import shutil
import pickle
import subprocess

ARCHIVE_DIR = os.path.join(os.path.dirname(__file__), "models", "archives")
ROOT_DIR = os.path.dirname(__file__)
PKL_FILES = [
    "feature_names.pkl",
    "lens_size_model.pkl",
    "lens_size_scaler.pkl",
    "vault_model.pkl",
    "vault_scaler.pkl",
]


def list_models():
    print("\nAvailable models:\n")
    for name in sorted(os.listdir(ARCHIVE_DIR)):
        path = os.path.join(ARCHIVE_DIR, name)
        if not os.path.isdir(path):
            continue
        feat_path = os.path.join(path, "feature_names.pkl")
        if not os.path.exists(feat_path):
            continue
        features = pickle.load(open(feat_path, "rb"))
        readme_path = os.path.join(path, "README.md")
        desc = ""
        if os.path.exists(readme_path):
            with open(readme_path) as f:
                for line in f:
                    if line.startswith("- **Lens accuracy:**"):
                        desc += line.strip().replace("- **Lens accuracy:** ", "Lens: ")
                    if line.startswith("- **Vault MAE:**"):
                        desc += "  " + line.strip().replace("- **Vault MAE:** ", "MAE: ")
        print(f"  {name:30s}  {len(features)} features  {desc}")

    # Show what's currently live
    current_feat = os.path.join(ROOT_DIR, "feature_names.pkl")
    if os.path.exists(current_feat):
        current = pickle.load(open(current_feat, "rb"))
        print(f"\n  Currently deployed: {len(current)} features")
    print()


def swap(tag, push=False):
    source = os.path.join(ARCHIVE_DIR, tag)
    if not os.path.isdir(source):
        print(f"Error: '{tag}' not found in models/archives/")
        list_models()
        return False

    print(f"Swapping to: {tag}")
    for f in PKL_FILES:
        src = os.path.join(source, f)
        dst = os.path.join(ROOT_DIR, f)
        if os.path.exists(src):
            shutil.copy2(src, dst)
            print(f"  ✓ {f}")
        else:
            print(f"  ⚠ {f} not found in archive")

    if push:
        print("\nCommitting and pushing...")
        subprocess.run(["git", "add"] + PKL_FILES, cwd=ROOT_DIR)
        subprocess.run(
            ["git", "commit", "-m", f"Deploy model: {tag}"],
            cwd=ROOT_DIR,
        )
        subprocess.run(["git", "push", "origin", "main"], cwd=ROOT_DIR)
        print("✅ Pushed — Render will auto-deploy in ~3-5 min")
    else:
        print(f"\nFiles swapped locally. To deploy:")
        print(f"  git add *.pkl && git commit -m 'Deploy {tag}' && git push origin main")

    return True


if __name__ == "__main__":
    if len(sys.argv) < 2:
        list_models()
    else:
        tag = sys.argv[1]
        push = "--push" in sys.argv
        swap(tag, push)
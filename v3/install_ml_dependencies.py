#!/usr/bin/env python3
"""Script to install ML dependencies."""

import subprocess
import sys
import os

def install_package(package):
    """Install a package using pip."""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        print(f"✓ {package} installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install {package}: {e}")
        return False

def main():
    """Install all ML dependencies."""
    print("Installing ML dependencies...")
    
    # List of required packages
    packages = [
        "seaborn>=0.12.0",
        "matplotlib>=3.7.0", 
        "torch>=2.0.0",
        "transformers>=4.30.0",
        "scikit-learn>=1.3.0",
        "plotly>=5.0.0"
    ]
    
    success_count = 0
    total_packages = len(packages)
    
    for package in packages:
        if install_package(package):
            success_count += 1
    
    print(f"\nInstallation complete: {success_count}/{total_packages} packages installed successfully")
    
    if success_count == total_packages:
        print("🎉 All ML dependencies are ready!")
        return True
    else:
        print("⚠️ Some packages failed to install. Please check the errors above.")
        return False

if __name__ == "__main__":
    main()

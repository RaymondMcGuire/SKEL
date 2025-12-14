#!/usr/bin/env python3
"""
Installation script for SMPLH and MANO model data
Inspired by the DECA code repository: https://github.com/yfeng95/DECA
Merge process follows: https://github.com/vchoutas/smplx/blob/main/tools/README.md
"""

import os
import sys
import shutil
import zipfile
import tarfile
import getpass
import subprocess

try:
    import requests
except ImportError:
    print("Installing required package: requests")
    os.system(f"{sys.executable} -m pip install requests")
    import requests


def download_file(username: str, password: str, domain: str, sfile: str, output_path: str, name: str) -> bool:
    """
    Download model file from the official website.
    
    Args:
        username: Registered username
        password: Password
        domain: Download domain (e.g., 'mano')
        sfile: Source file name on server
        output_path: Path to save the downloaded file
        name: Display name for progress messages
    
    Returns:
        True if download successful, False otherwise
    """
    url = "https://download.is.tue.mpg.de/download.php"
    params = {
        "domain": domain,
        "sfile": sfile,
        "resume": "1"
    }
    
    data = {
        "username": username,
        "password": password
    }
    
    print(f"\nDownloading {name}...")
    
    try:
        response = requests.post(
            url,
            params=params,
            data=data,
            verify=False,
            stream=True
        )
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0
        
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        percent = (downloaded / total_size) * 100
                        print(f"\rProgress: {percent:.1f}% ({downloaded}/{total_size} bytes)", end="")
        
        print()
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"Download failed: {e}")
        return False


def verify_file_size(file_path: str, min_size_mb: int = 100) -> bool:
    """
    Verify that downloaded file exists and meets minimum size requirement.
    
    Args:
        file_path: Path to the file to verify
        min_size_mb: Minimum file size in megabytes
    
    Returns:
        True if file is valid, False otherwise
    """
    min_size = min_size_mb * 1024 * 1024
    if not os.path.exists(file_path):
        return False
    return os.path.getsize(file_path) >= min_size


def extract_tar_xz(tar_path: str, extract_dir: str) -> bool:
    """
    Extract a tar.xz file.
    
    Args:
        tar_path: Path to the tar.xz file
        extract_dir: Directory to extract to
    
    Returns:
        True if successful, False otherwise
    """
    try:
        print(f"Extracting {os.path.basename(tar_path)}...")
        with tarfile.open(tar_path, 'r:xz') as tar:
            tar.extractall(extract_dir)
        return True
    except Exception as e:
        print(f"Extraction failed: {e}")
        return False


def extract_zip(zip_path: str, extract_dir: str) -> bool:
    """
    Extract a zip file.
    
    Args:
        zip_path: Path to the zip file
        extract_dir: Directory to extract to
    
    Returns:
        True if successful, False otherwise
    """
    try:
        print(f"Extracting {os.path.basename(zip_path)}...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
        return True
    except Exception as e:
        print(f"Extraction failed: {e}")
        return False


def run_merge_script(smplh_fn: str, mano_left_fn: str, mano_right_fn: str, output_folder: str) -> bool:
    """
    Run the merge_smplh_mano.py script to merge SMPLH and MANO models.
    
    Args:
        smplh_fn: Path to SMPLH model file
        mano_left_fn: Path to MANO left hand model
        mano_right_fn: Path to MANO right hand model
        output_folder: Output folder for merged model
    
    Returns:
        True if successful, False otherwise
    """
    merge_script = os.path.join("../dependancies", "merge_smplh_mano.py")
    
    if not os.path.exists(merge_script):
        print(f"Error: Merge script not found at {merge_script}")
        return False
    
    cmd = [
        sys.executable,
        merge_script,
        "--smplh-fn", smplh_fn,
        "--mano-left-fn", mano_left_fn,
        "--mano-right-fn", mano_right_fn,
        "--output-folder", output_folder
    ]
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Merge script failed: {e}")
        if e.stderr:
            print(e.stderr)
        return False


def main():
    """Main entry point for the SMPLH/MANO installation script."""
    
    # Suppress SSL warnings
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    print("=" * 60)
    print("SMPLH & MANO Model Installation Script")
    print("=" * 60)
    print("\nBefore you continue, you must register at:")
    print("  https://mano.is.tue.mpg.de/")
    print("and agree to the MANO license terms.\n")
    
    # Get credentials
    username = input("Username (MANO): ").strip()
    password = getpass.getpass("Password (MANO): ").strip()
    
    if not username or not password:
        print("Error: Username and password are required.")
        sys.exit(1)
    
    # Setup paths
    data_dir = "../data"
    
    # Use different temp folder names to avoid Windows case-insensitive issue
    smplh_temp_dir = os.path.join(data_dir, "_smplh_temp_extract")
    mano_temp_dir = os.path.join(data_dir, "_mano_temp_extract")
    
    smplh_tar_path = os.path.join(data_dir, "SMPLH.tar.xz")
    mano_zip_path = os.path.join(data_dir, "MANO.zip")
    
    # Output directory
    output_dir = os.path.join(data_dir, "smplx", "smplh")
    
    # Create directories
    os.makedirs(data_dir, exist_ok=True)
    
    # Clean up any existing temp directories
    for temp_dir in [smplh_temp_dir, mano_temp_dir]:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
    
    # ========== Download SMPLH ==========
    if not download_file(
        username, password,
        domain="mano",
        sfile="smplh.tar.xz",
        output_path=smplh_tar_path,
        name="SMPLH"
    ):
        print("Error: SMPLH download failed. Please check your credentials and try again.")
        sys.exit(1)
    
    if not verify_file_size(smplh_tar_path, min_size_mb=100):
        print("Error: SMPLH download failed or file is too small. Please check your credentials.")
        sys.exit(1)
    
    print(f"SMPLH download complete: {os.path.getsize(smplh_tar_path) / (1024*1024):.1f} MB")
    
    # ========== Download MANO ==========
    if not download_file(
        username, password,
        domain="mano",
        sfile="mano_v1_2.zip",
        output_path=mano_zip_path,
        name="MANO"
    ):
        print("Error: MANO download failed. Please check your credentials and try again.")
        sys.exit(1)
    
    # MANO is smaller, so use a smaller size check (e.g., 1MB)
    if not verify_file_size(mano_zip_path, min_size_mb=1):
        print("Error: MANO download failed or file is too small. Please check your credentials.")
        sys.exit(1)
    
    print(f"MANO download complete: {os.path.getsize(mano_zip_path) / (1024*1024):.1f} MB")
    
    # ========== Extract files ==========
    os.makedirs(smplh_temp_dir, exist_ok=True)
    os.makedirs(mano_temp_dir, exist_ok=True)
    
    if not extract_tar_xz(smplh_tar_path, smplh_temp_dir):
        print("Error: Failed to extract SMPLH.")
        sys.exit(1)
    
    if not extract_zip(mano_zip_path, mano_temp_dir):
        print("Error: Failed to extract MANO.")
        sys.exit(1)
    
    # ========== Merge SMPLH and MANO ==========
    print("\nMerging SMPLH and MANO models...")
    os.makedirs(output_dir, exist_ok=True)
    
    # Paths to model files
    mano_left = os.path.join(mano_temp_dir, "mano_v1_2", "models", "MANO_LEFT.pkl")
    mano_right = os.path.join(mano_temp_dir, "mano_v1_2", "models", "MANO_RIGHT.pkl")
    
    # Process female model
    print("\nProcessing FEMALE model...")
    smplh_female = os.path.join(smplh_temp_dir, "female", "model.npz")
    
    if not run_merge_script(smplh_female, mano_left, mano_right, output_dir):
        print("Error: Failed to merge FEMALE model.")
        sys.exit(1)
    
    # Rename output file
    src_model = os.path.join(output_dir, "model.pkl")
    dst_female = os.path.join(output_dir, "SMPLH_FEMALE.pkl")
    if os.path.exists(src_model):
        shutil.move(src_model, dst_female)
        print(f"  Created: SMPLH_FEMALE.pkl")
    
    # Process male model
    print("\nProcessing MALE model...")
    smplh_male = os.path.join(smplh_temp_dir, "male", "model.npz")
    
    if not run_merge_script(smplh_male, mano_left, mano_right, output_dir):
        print("Error: Failed to merge MALE model.")
        sys.exit(1)
    
    # Rename output file
    dst_male = os.path.join(output_dir, "SMPLH_MALE.pkl")
    if os.path.exists(src_model):
        shutil.move(src_model, dst_male)
        print(f"  Created: SMPLH_MALE.pkl")
    
    # ========== Cleanup ==========
    print("\nCleaning up...")
    shutil.rmtree(smplh_temp_dir)
    shutil.rmtree(mano_temp_dir)
    os.remove(smplh_tar_path)
    os.remove(mano_zip_path)
    
    print("\n" + "=" * 60)
    print("SMPLH & MANO installation completed successfully!")
    print(f"Model files are located in: {os.path.abspath(output_dir)}")
    print("  - SMPLH_FEMALE.pkl")
    print("  - SMPLH_MALE.pkl")
    print("=" * 60)


if __name__ == "__main__":
    main()
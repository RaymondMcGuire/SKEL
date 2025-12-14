#!/usr/bin/env python3
"""
Installation script for SMPL model data
Inspired by the DECA code repository: https://github.com/yfeng95/DECA
"""

import os
import sys
import shutil
import zipfile
import getpass

try:
    import requests
except ImportError:
    print("Installing required package: requests")
    os.system(f"{sys.executable} -m pip install requests")
    import requests


def download_smpl(username: str, password: str, output_path: str) -> bool:
    """
    Download SMPL model from the official website.
    
    Args:
        username: Registered username on SMPL website
        password: Password for SMPL website
        output_path: Path to save the downloaded zip file
    
    Returns:
        True if download successful, False otherwise
    """
    url = "https://download.is.tue.mpg.de/download.php"
    params = {
        "domain": "smpl",
        "sfile": "SMPL_python_v.1.1.0.zip",
        "resume": "1"
    }
    
    data = {
        "username": username,
        "password": password
    }
    
    print("\nDownloading SMPL...")
    
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


def extract_and_organize(zip_path: str, data_dir: str) -> bool:
    """
    Extract SMPL zip file and organize the model files.
    
    Args:
        zip_path: Path to the downloaded zip file
        data_dir: Base data directory
    
    Returns:
        True if successful, False otherwise
    """
    # Use a completely different name to avoid Windows case-insensitive issue
    temp_extract_dir = os.path.join(data_dir, "_smpl_temp_extract")
    smpl_output_dir = os.path.join(data_dir, "smpl")
    
    try:
        # Clean up any existing temp directory
        if os.path.exists(temp_extract_dir):
            shutil.rmtree(temp_extract_dir)
        
        # Extract zip file
        print("Extracting SMPL.zip...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_extract_dir)
        
        # Create output directory
        os.makedirs(smpl_output_dir, exist_ok=True)
        
        # Define file mappings (source -> destination)
        models_dir = os.path.join(
            temp_extract_dir, 
            "SMPL_python_v.1.1.0", 
            "smpl", 
            "models"
        )
        
        file_mappings = {
            "basicmodel_f_lbs_10_207_0_v1.1.0.pkl": "SMPL_FEMALE.pkl",
            "basicmodel_m_lbs_10_207_0_v1.1.0.pkl": "SMPL_MALE.pkl",
            "basicmodel_neutral_lbs_10_207_0_v1.1.0.pkl": "SMPL_NEUTRAL.pkl"
        }
        
        # Copy and rename files (use copy instead of move for safety)
        print("Organizing model files...")
        for src_name, dst_name in file_mappings.items():
            src_path = os.path.join(models_dir, src_name)
            dst_path = os.path.join(smpl_output_dir, dst_name)
            
            if os.path.exists(src_path):
                shutil.copy2(src_path, dst_path)
                print(f"  {src_name} -> {dst_name}")
            else:
                print(f"  Warning: {src_name} not found")
        
        # Cleanup temporary files
        print("Cleaning up...")
        shutil.rmtree(temp_extract_dir)
        os.remove(zip_path)
        
        return True
        
    except Exception as e:
        print(f"Extraction failed: {e}")
        return False


def main():
    """Main entry point for the SMPL installation script."""
    
    # Suppress SSL warnings
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    print("=" * 60)
    print("SMPL Model Installation Script")
    print("=" * 60)
    print("\nBefore you continue, you must register at:")
    print("  https://smpl.is.tue.mpg.de/")
    print("and agree to the SMPL license terms.\n")
    
    # Get credentials
    username = input("Username (SMPL): ").strip()
    password = getpass.getpass("Password (SMPL): ").strip()
    
    if not username or not password:
        print("Error: Username and password are required.")
        sys.exit(1)
    
    # Setup paths
    data_dir = "../data"
    zip_path = os.path.join(data_dir, "SMPL.zip")
    
    # Create data directory
    os.makedirs(data_dir, exist_ok=True)
    
    # Download SMPL
    if not download_smpl(username, password, zip_path):
        print("Error: Download failed. Please check your credentials and try again.")
        sys.exit(1)
    
    # Verify file size (should be > 100MB)
    min_size = 100 * 1024 * 1024  # 100 MB
    if not os.path.exists(zip_path) or os.path.getsize(zip_path) < min_size:
        print("Error: Downloaded file is too small. Please check your credentials.")
        sys.exit(1)
    
    print(f"Download complete: {os.path.getsize(zip_path) / (1024*1024):.1f} MB")
    
    # Extract and organize files
    if not extract_and_organize(zip_path, data_dir):
        print("Error: Failed to extract and organize files.")
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("SMPL installation completed successfully!")
    print(f"Model files are located in: {os.path.abspath('../data/smpl/')}")
    print("=" * 60)


if __name__ == "__main__":
    main()
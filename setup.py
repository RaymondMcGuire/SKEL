from setuptools import find_packages, setup
from pathlib import Path

requirements = [
    "wheel",
    "torch>=1.6.0",
    "smplx",
    "trimesh",
    "tqdm",
    "matplotlib",
    "moderngl-window==2.4.6",
]

# Read README.md with explicit UTF-8 encoding (fixes cp932 decode issues on Windows)
this_dir = Path(__file__).parent
long_description = (this_dir / "README.md").read_text(encoding="utf-8")

setup(
    name="skel",
    description="SKEL model Loader.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    version="1.0",  # prefer string
    author="Marilyn Keller",
    packages=find_packages(),
    include_package_data=True,
    keywords=[
        "motion",
        "machine learning",
        "sequences",
        "smpl",
        "computer graphics",
        "computer vision",
        "3D",
        "meshes",
        "skel",
        "smpl",
    ],
    platforms=["any"],
    install_requires=requirements,
)

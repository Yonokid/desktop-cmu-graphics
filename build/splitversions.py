import shutil
import os
import re
import platform
import argparse
from file_io_util import *

# Regex used to remove the zip version code from the pip version and vice versa
ZIP_REGEX=r"### ZIPFILE VERSION ###.*?### END ZIPFILE VERSION ###"
PYPI_REGEX=r"### PYPI VERSION ###.*?### END PYPI VERSION ###"

def split_versions(zip_dest, pypi_dest, ignore_fn, dots):
    make_all_dirs(dots + zip_dest, dots + pypi_dest)
    # cmu_graphics package
    print("Copying cmu_graphics package to pypi_upload/src/ ...")
    shutil.copytree(dots + "cmu_graphics", dots + f"{pypi_dest}/cmu_graphics", ignore=ignore_fn)
    print("Copying cmu_graphics package to cmu_graphics_installer/ ...")
    shutil.copytree(dots + "cmu_graphics", dots + f"{zip_dest}/cmu_graphics")
    # sample files
    print("Copying sample files to pypi_upload/src/cmu_graphics ...")
    shutil.copytree(dots + "samples", dots + f"{pypi_dest}/cmu_graphics/samples")
    print("Copying sample files to pypi_upload/src/cmu_graphics ...")
    for sample_path in os.listdir(dots + "samples"):
        shutil.copy2(dots + f"samples/{sample_path}", dots + f"{zip_dest}/cmu_graphics/{sample_path}")
    # Meta files and docs
    for path in ["LICENSE", "INSTRUCTIONS.pdf"]:
        shutil.copy2(dots + path, dots + f"{zip_dest}/{get_filename(path)}")
    pypi_parent = "/".join(pypi_dest.split("/")[:-1])
    for path in ["LICENSE", "README.md", "setup.py", "pyproject.toml"]:
        shutil.copy2(dots + path, dots + f"{pypi_parent}/{get_filename(path)}") 
        # Note that those files are in a different location than src, where the
        # actual package is

    # Separate the PyPI and zip versions of cmu_graphics from each other
    pypi_source_dirs = [
        dots + f"{pypi_dest}/cmu_graphics",
        dots + f"{pypi_dest}/cmu_graphics/libs"
        ]
    for dir in pypi_source_dirs:
        for path in os.listdir(dir):
            full_path = f"{dir}/{path}"
            if os.path.isfile(full_path):
                replace_file_text(full_path, ZIP_REGEX, "", re.DOTALL)
    zip_source_dirs = [
        dots + f"{zip_dest}/cmu_graphics",
        dots + f"{zip_dest}/cmu_graphics/libs"
        ]
    for dir in zip_source_dirs:
        for path in os.listdir(dir):
            full_path = f"{dir}/{path}"
            if os.path.isfile(full_path):
                replace_file_text(full_path, PYPI_REGEX, "", re.DOTALL)

def rm_temp_dirs(zip_dest, pypi_dest, dots, deploy_dest = None):
    shutil.rmtree(dots + zip_dest)
    shutil.rmtree(dots + pypi_dest)
    if deploy_dest != None:
        shutil.rmtree(dots + deploy_dest)

def main(args):
    if args.mode not in ['split', 'clean']:
        print("Invalid mode: choose one of 'split' or 'clean'")
        os._exit(1)
    if args.location not in ['root', 'tests']:
        print("Invalid location: choose one of 'root' or 'tests'")
        os._exit(1)
    else:
        python_str = ""
        root_dir = ""
        if args.location == 'tests':
            python_major, python_minor, _ = platform.python_version_tuple()
            python_str = f"{python_major}{python_minor}"
            root_dir = "../"

        zip_dest = "cmu_graphics_installer" + python_str
        pypi_dest= f"pypi_upload{python_str}/src"
        if args.mode == "split":
            print("""Manually splitting the zip and pip versions of CMU
Graphics. Please make sure to re-run this command with the 'clean' flag to 
remove the temporary files.""")
            ignore_fn = shutil.ignore_patterns("*loader", "certifi")
            split_versions(zip_dest, pypi_dest, ignore_fn, root_dir)
            os._exit(0)
        elif args.mode == "clean":
            pypi_dest = "pypi_upload" + python_str
            print("Cleaning up temporary zip and pip versions of CMU Graphics...", end="")
            rm_temp_dirs(zip_dest, pypi_dest, root_dir)
            print("Done!")
            os._exit(0)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    # mode must be split or clean
    parser.add_argument(
        'mode', 
        type=str, 
        help='Specifies whether to create or delete the test files'
    )
    # location must be root or tests
    parser.add_argument(
        'location', 
        type=str, 
        help='The location in which the file creation/deletion is happening'
    )
    args = parser.parse_args()
    main(args)
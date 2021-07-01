# -*- coding: UTF-8 -*-

import os
from setuptools import setup
from typing import List


def _get_relative_path(file_path: str) -> str:
    return os.path.join(os.path.dirname(__file__), file_path)


def load_requirements() -> List[str]:
    # Load requirements
    requirements = []  # type: List[str]
    with open(_get_relative_path("requirements.txt"), "r") as req_file:
        lines = [line.rstrip("\n") for line in req_file]
        lines = list(filter(lambda line: line != "" and line[0] != "#", lines))
        for line in lines:
            hash_pos = line.find("#")
            if hash_pos != -1:
                requirements.append(line[:hash_pos].strip())
            else:
                requirements.append(line)
    return requirements


def main():
    drive_ns = {}
    with open(_get_relative_path("drive/__version__.py")) as f:
        exec(f.read(), drive_ns)

    setup(
        name='drive',
        version=drive_ns["__version__"],
        author='Baptiste Fontaine',
        author_email='baptiste.fontaine@oscaro.com',
        packages=['drive', 'drive.cli'],
        url='https://github.com/NoName115/drive',
        license='MIT License',
        description='Google Drive client',
        long_description=open('README.md', encoding='utf-8').read(),
        long_description_content_type='text/markdown',
        install_requires=load_requirements(),
        classifiers=[
            'License :: OSI Approved :: MIT License',
            'Programming Language :: Python :: 3.6',
            'Programming Language :: Python :: 3.7',
            'Programming Language :: Python :: 3.8',
            'Programming Language :: Python :: 3.9',
        ],
        entry_points={
            "console_scripts": [
                "gd-upload=drive.cli.upload:main",
                "gd-download=drive.cli.download:main",
            ]
        }
    )


if __name__ == "__main__":
    main()

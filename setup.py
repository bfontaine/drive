# -*- coding: UTF-8 -*-

from setuptools import setup

# http://stackoverflow.com/a/7071358/735926
import re

VERSIONFILE = 'drive/__init__.py'
verstrline = open(VERSIONFILE, 'rt').read()
VSRE = r'^__version__\s+=\s+[\'"]([^\'"]+)[\'"]'
mo = re.search(VSRE, verstrline, re.M)
if mo:
    verstr = mo.group(1)
else:
    raise RuntimeError("Unable to find version string in %s." % VERSIONFILE)

setup(
    name='drive',
    version=verstr,
    author='Baptiste Fontaine',
    author_email='b@ptistefontaine.fr',
    packages=['drive'],
    url='https://github.com/oscaro/drive',
    license='MIT License',
    description='Google Drive client',
    long_description=open('README.md', encoding='utf-8').read(),
    long_description_content_type='text/markdown',
    install_requires=[
        "google-api-python-client==2.7.0",
        "httplib2==0.19.1",
        "oauth2client==4.1.3",
        "openpyxl==3.0.7",
        "python-magic",
    ],
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
    ],
)

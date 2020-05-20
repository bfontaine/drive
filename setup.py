# -*- coding: UTF-8 -*-

from setuptools import setup

# http://stackoverflow.com/a/7071358/735926
import re
VERSIONFILE='drive/__init__.py'
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
    author_email='baptiste.fontaine@oscaro.com',
    packages=['drive'],
    url='https://github.com/oscaro/drive',
    license='MIT License',
    description='Google Drive client',
    long_description=open('README.md', encoding='utf-8').read(),
    long_description_content_type='text/markdown',
    install_requires=[
        "datatypes==0.1.0",
        "google-api-python-client==1.5.3",
        "httplib2==0.18.0",
        "oauth2client==3.0.0",
        "openpyxl==2.4.0",
        "pyasn1==0.1.9",
        "pyasn1-modules==0.0.8",
        "python-magic==0.4.12",
        "rsa==3.4.2",
        "simplejson==3.8.2",
        "six==1.10.0",
        "uritemplate==0.6",
    ],
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
)

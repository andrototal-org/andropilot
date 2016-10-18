"""
andropilot
----------
"""
from setuptools import find_packages, setup


with open('README.rst', 'r') as f:
    long_description = f.read()

EXCLUDE_FROM_PACKAGES = ['docs._build','docs._template', 'docs._static']

setup(
    name='andropilot',
    version='1.0',
    license='GPL',
    description='andropilot package',
    long_description=long_description,
    packages=find_packages(exclude=EXCLUDE_FROM_PACKAGES),
    classifiers=[
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.3',
        'Programming Language :: Python :: 2.4',
        'Programming Language :: Python :: 2.5',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
    ],
)

#!/usr/bin/env python3

from setuptools import setup, find_packages

required = []
with open('requirements.txt') as f:
    required = f.read().splitlines()

setup(name='registro.br',
      version='1.0',
      description='API and shell CLI to access registro.br domains and dns records',
      author='Fernando Crespo',
      author_email='fernando82@gmail.com',
      url='https://github.com/fcrespo82/registro.br',
      packages=find_packages('.'),
      scripts=['cli.py', 'shell.py'],
      entry_points={
          'console_scripts': [
              'registrobr-cli = cli.py:main',
              'registrobr-shell = shell.py:main'
          ]
      },
      install_requires=required
      )

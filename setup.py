from __future__ import absolute_import
from __future__ import print_function

import os, sys

from setuptools import setup

install_requires = [
    'minibelt',
    'pyyaml',
]

setup(name='timon',
      version='0.0.1',
      description='module with git hooks',
      classifiers=[
      ],
      keywords='tiny monitor',
      url='https://www.teledomic.eu',
      author='Teledomic',
      author_email='info@teledomic.eu',
      # TODO: add discovery of packages
      packages=[
            'timon', 
            ],
      scripts=[],
      entry_points={
          'console_scripts': [
              'timon = timon.commands:main',
          ]
      },
      test_suite='nose.collector',
      install_requires=install_requires,
      tests_require=['nose'],
      zip_safe = False)


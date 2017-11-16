from __future__ import absolute_import
from __future__ import print_function

import os, sys

from setuptools import setup


setup(name='timon',
      version='0.0.3',
      description='module with git hooks',
      classifiers=[
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3 :: Only',
        'Intended Audience :: Sysadmins / DevOps',
        'Intended Audience :: Information Technology',
        'Operating System :: POSIX :: Linux',
        'Operating System :: Microsoft :: Windows',
        'Topic :: Internet',
        'Topic :: Internet :: File Transfer Protocol (FTP)',
        'Programming Language :: Python',

      ],
      keywords='tiny monitor',
      url='https://www.teledomic.eu',
      author='Teledomic',
      author_email='info@teledomic.eu',
      license='Apache Software License',
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
      install_requires=[
        'mytb',
        'minibelt',
        'pyyaml',
        'requests',
      ],
      extra_requires=dict(
        all=[],
        ),
      tests_require=['nose', 'pytest'],
      zip_safe=False,
      include_package_data=True,
    )


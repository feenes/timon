from __future__ import absolute_import
from __future__ import print_function

from setuptools import setup


setup(name='timon',
      version='0.3.0',
      description='simple, low resource monitoring tool',
      classifiers=[
            'Development Status :: 3 - Alpha',
      ],
      keywords='tiny monitor',
      url='https://www.teledomic.eu',
      author='Teledomic',
      author_email='info@teledomic.eu',
      license='Apache Software License',
      # TODO: add discovery of packages
      packages=[
            'timon',
            'timon.conf',
            'timon.notifiers',
            'timon.plugins',
            'timon.scripts',
            'timon.tests',
            ],
      scripts=[],
      entry_points={
          'console_scripts': [
              'timon = timon.commands:main',
              'timon_build = timon.bld_commands:main',
          ]
      },
      install_requires=[
        'click',
        'cryptography',
        'mytb',
        'minibelt',
        'pyyaml',
        'requests',
      ],
      extra_requires=dict(
        all=[],
        ),
      setup_requires=['pytest-runner'],
      tests_require=['pytest', 'pytest-asyncio'],
      zip_safe=False,
      include_package_data=True,
      python_requires='>=3.5, <4',
      )

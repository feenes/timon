from setuptools import find_packages
from setuptools import setup

long_description = """simple, low resource monitoring tool,
that should be able to run for example on a raspberry for
monitoring just a few nodes
"""


setup(name='timon',
      version='0.4.0',
      description='simple, low resource monitoring tool',
      long_description=long_description,
      classifiers=[
            'Development Status :: 3 - Alpha',
      ],
      keywords='tiny monitor',
      url='https://www.teledomic.eu',
      author='Teledomic',
      author_email='info@teledomic.eu',
      license='Apache Software License',
      # TODO: add discovery of packages
      packages=find_packages(),
      scripts=[],
      entry_points={
          'console_scripts': [
              'timon = timon.commands:main',
              'timon_build = timon.bld_commands:main',
          ]
      },
      project_urls={
        "Homepage": "https://github.com/feenes/timon",
        "Documentation": "https://github.com/feenes/timon",
        "Source": "https://github.com/feenes/timon",
        "SayThanks": "https://github.com/feenes",
        "Funding": "https://donate.pypi.org",
        "Tracker": "https://github.com/feenes/timon/issues",
      },
      install_requires=[
        'click',
        'cryptography',
        'httpx',
        'mytb',
        'minibelt',
        'peewee',
        'pyyaml',
        'pyopenssl',
        'requests',
        "quart"
      ],
      extra_requires=dict(
        all=[],
        ),
      python_requires='>=3.11, <4',
      setup_requires=['pytest-runner'],
      tests_require=['pytest'],
      zip_safe=False,
      include_package_data=True,
      )

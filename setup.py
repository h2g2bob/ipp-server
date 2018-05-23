#! /usr/bin/python

from setuptools import setup, find_packages

REQUIREMENTS = [
    "requests"
]

setup(
      name='ipp-server',
      author="David Batley",
      license="BSD2",
      description='An ipp server',
      version='0.2',
      url='http://github.com/h2g2bob/ipp-server',
      packages=find_packages(exclude=["tests"]),
      test_suite="tests.test_request",
      package_data={
        'ippserver': ['data/*'],
      },
      classifiers=[
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD2 License',
        'Programming Language :: Python',
        'Topic :: Software Development :: Libraries :: Python Modules'],
      install_requires=REQUIREMENTS,
      entry_points={
        'console_scripts': [
            'ippserver = ippserver.__main__:main',
        ]
    }
)

#! /usr/bin/python

from setuptools import setup, find_packages

REQUIREMENTS = [
    "requests"
]

setup(
      name='ipp-server',
      author="David Batley",
      author_email="git@dbatley.com",
      license="BSD2",
      description='An IPP server which acts like a printer',
      long_description='A module which implements enough of IPP to fool CUPS into thinking it is a real printer.',
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

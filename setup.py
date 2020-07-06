# coding: utf-8

import setuptools

setuptools.setup(
  name='ffd',
  version='0.0.2',
  author='dlr',
  author_email='dlr@yy.com',
  description=u'Fast downloader',
  packages=setuptools.find_packages(),
  url='https://dlr.com',
  entry_points={
    'console_scripts': [
      'ffd=ffd.cli:main'
    ]
  },
  classifiers=[
      'Programming Language :: Python :: 3 :: Only'
  ]
)

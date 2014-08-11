#!/usr/bin/python
# coding: utf-8
from setuptools import setup

setup(name='uploader',
      version='0.3.1',
      description='Uploading administration tool',
      author='Denis Denisenko',
      author_email='d.winmain@gmail.com',
      url='https://bitbucket.org/winmain/uploader/',
      packages=['uploader'],
      keywords='upload ssh ftp',
      entry_points={
        'console_scripts': [
            'uploader = uploader.run:main',
            ],
        },
      )

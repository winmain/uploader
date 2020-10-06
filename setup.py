#!/usr/bin/env python3
# coding: utf-8
from setuptools import setup

setup(name='uploader',
      version='0.5.0',
      description='SSH upload administration tool',
      author='Denis Denisenko',
      author_email='d.winmain@gmail.com',
      url='https://github.com/winmain/uploader',
      packages=['uploader'],
      keywords='upload ssh',
      classifiers=['Environment :: Console',
                   'Intended Audience :: Developers',
                   'Intended Audience :: System Administrators',
                   'Operating System :: POSIX',
                   'Programming Language :: Python',
                   'Topic :: System :: Systems Administration'],
      entry_points={
          'console_scripts': [
              'uploader = uploader.run:main',
          ],
      },
      )

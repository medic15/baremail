#!/usr/bin/env python

from distutils.core import setup
import glob

# Utility function to read the README file.
def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(name = 'BareMail',
      version = '0.1.0',
      description = 'A pure Python email service',
      long_description = read('READMT.txt')
      author='Alan Willis',
      author_email='Alan Willis <baremail@samara-rt.com',
      url='https://github.com/medic15/baremail',
      scripts = glob.glob('scripts/*'),
      packages = ['baremail'],
      data_files = glob.glob('config/*') +
                   glob.glob('docs/html/*') +
                   glob.glob('docs/html/_static/*'),
      classifiers = [
        'Development Status :: 3 - Alpha',
        'Intended Audience :: End Users/Desktop',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Operating System :: POSIX',
        'Programming Language :: Python :: 2',
        'Topic :: Communications :: Email'
     ]
    )


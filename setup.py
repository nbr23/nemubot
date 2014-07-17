#!/usr/bin/env python3
#-*- encoding: utf-8 -*-

import os
import re
from glob import glob
try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

with open(os.path.join(os.path.dirname(__file__),
                      'lib',
                       '__init__.py')) as f:
        version = re.search("self.version_txt = '([^']+)'", f.read()).group(1)

with open('requirements.txt', 'r') as f:
    requires = [x.strip() for x in f if x.strip()]

#with open('test-requirements.txt', 'r') as f:
#    test_requires = [x.strip() for x in f if x.strip()]

dirs = os.listdir("./modules/")
data_files = []
for i in dirs:
    data_files.append(("nemubot/modules", glob('./modules/' + i + '/*')))

setup(
    name="nemubot",
    version=version,
    description="A smart and modulable IM bot!",
    long_description=open('README.md').read(),

    author='nemunaire',
    author_email='nemunaire@nemunai.re',

    url='https://github.com/nemunaire/nemubot',
    license='AGPLv3',

    classifiers=[
        'Development Status :: 2 - Pre-Alpha',

        'Environment :: Console',

        'Topic :: Communications :: Chat :: Internet Relay Chat',
        'Intended Audience :: Information Technology',

        'License :: OSI Approved :: GNU Affero General Public License v3',

        'Operating System :: POSIX',

        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
    ],

    keywords='bot irc',

    install_requires = requires,

    package_dir={ 'nemubot': 'lib' },

    packages=[
        'nemubot',
        'nemubot.prompt',
        'nemubot.tools',
        'nemubot.xmlparser',
    ],

    scripts=[
        'bin/nemubot',
#        'bin/module_tester',
    ],

#    data_files=data_files,
)

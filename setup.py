#!/usr/bin/env python

from setuptools import setup, find_packages
import errorguimonitor
import os


def extra_dependencies():
    import sys
    ret = []
    if sys.version_info < (2, 7):
        ret.append('argparse')
    return ret


def read(*names):
    values = dict()
    extensions = ['.txt', '.rst']
    for name in names:
        value = ''
        for extension in extensions:
            filename = name + extension
            if os.path.isfile(filename):
                value = open(name + extension).read()
                break
        values[name] = value
    return values

long_description = """
%(README)s

News
====

%(CHANGES)s

""" % read('README', 'CHANGES')

setup(
    name='errorguimonitor',
    version=errorguimonitor.__version__,
    description='Check ErrorGUI for new errors or significant increase of existing errors between environments (CI vs DEMO, DEMO vs QED, QED vs PROD)',
    long_description=long_description,
    classifiers=[
        "Development Status :: 1 - Development",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3.6",
        "Topic :: Documentation",
    ],
    keywords='errorguimonitor help track errors',
    author='Ihar Malkevich',
    author_email='imalkevich@gmail.com',
    maintainer='Ihar Malkevich',
    maintainer_email='imalkevich@gmail.com',
    url='https://github.com/imalkevich/errorguimonitor',
    license='MIT',
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'errorguimonitor = errorguimonitor.errorguimonitor:command_line_runner',
        ]
    },
    install_requires=[
        'PrettyTable',
        'numpy',
        'pyquery',
        #'pygments',
        'requests',
        #'requests-cache'
    ] + extra_dependencies(),
)

errorguimonitor
====================================================

command line utility to send notifications about new/increased errors from ErrorGUI
-------------------------------------------

.. image:: https://secure.travis-ci.org/imalkevich/errorguimonitor.png?branch=master
        :target: https://travis-ci.org/imalkevich/errorguimonitor

.. image:: https://codecov.io/github/imalkevich/errorguimonitor/coverage.svg?branch=master
    :target: https://codecov.io/github/imalkevich/errorguimonitor
    :alt: codecov.io

Are you watching for module and would like to understand whether new code being added is
not causing new issues - run this tool on a regular basis to be able to see the trends in errors.

Installation
------------

::

    pip install errorguimonitor

or

::

    python setup.py install

Usage
-----

::

    usage: reporter.py [-h] [-e ENVIRONMENT] [-d DATE] [-u USER] [-p PASSWORD]
                   [-smtp_user SMTP_USER] [-smtp_password SMTP_PASSWORD] [-v]

    compare errors for two periods in s specific environment via the command line

    optional arguments:
    -h, --help            show this help message and exit
    -e ENVIRONMENT, --environment ENVIRONMENT
                            the environment (QED only at the moment)
    -d DATE, --date DATE  the target date (year-month-day)
    -u USER, --user USER  SAFE ID user
    -p PASSWORD, --password PASSWORD
                            SAFE ID password
    -smtp_user SMTP_USER, --smtp_user SMTP_USER
                            Gmail account username
    -smtp_password SMTP_PASSWORD, --smtp_password SMTP_PASSWORD
                            Gmail account password
    -v, --version         displays the current version of errorguimonitor

Author
------

-  Ihar Malkevich (imalkevich@gmail.com)
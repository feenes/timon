Overview
========
Timon is a an implementation of a low resource low performance monitoring system.

.. image:: https://travis-ci.org/feenes/timon.svg?branch=master
    :target: https://travis-ci.org/feenes/timon

It has mainly been implemented as a programming exercise, which started when I
noticed, that our monitoring system at work (Shinken a Python fork of nagios)
was using way too many resources and was just complete overkill for our modest
monitoring requirements.

I'm sure there's other solutions, which will be more complete, more compatible,
more efficient, more whatever.
But here my attempt on a simple monitoring solution using few resources, but
still being implemented in a high level language (Python3 with asyncio)


Objectives
----------

- when idle 0 memory footprint (crontab driven) or low memory footprint (one bash / or python process only) while idle
- asynchronous efficient implementation, but allow threads/subprocesses
- configurable/skalable  to adapt to resources available and amount of services to monitor
- easy to install (just clone or pip install)
- easy to configure (one yaml file)
- easy to enhance (simple python module import)


Getting Started
===============

Commands
---------

- timon config:  compiles/parses/checks config
- timon run:     runs monitoring (one shot or loop)
- timon status:  displays timon status


Configuration
-------------
.. _config_example: timon/data/examples/timon.yaml
The config file format is not documented, but here at least one config_example_




For Developpers
================
.. _generic_frontend_info: timon/webclient/README.rst
.. _webif1_frontend_info: timon/webclient/webif1/README.rst

More information about the web front ends generic_frontend_info_
an be found at webif1_frontend_info_


Compiling the web front end
----------------------------

You will require a working node environment.  You might for example use nvm.

    pip install -e .
    timon_build webif all

Testing / Running the web front end(s)
---------------------------------------




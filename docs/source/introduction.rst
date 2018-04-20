Introduction
=============

.. image:: https://travis-ci.org/feenes/timon.svg?branch=master

.. warning:: Timon is a very young project, so it's up to you to decide whether it's limited 
  features are sufficient for you.
The config file format and the API may still change until version 1.0 will be published.

`Timon` is minimalistic approach for server monitoring written in Python.
It's main purpose is to monitor small to midsized server networks with a monotoring server, 
that has rather small requirements.
The goal is not to achieve high scalability or best performance.


Main objectives of this project are:

* when idle 0 memory footprint (crontab driven) or low memory footprint (one bash / or python process only) while idle 
* lazy import mechanism for low foot print / faster execution
* asynchronous efficient implementation, but allow threads / subprocesses
* configurable / skalable (for small to mid sized environments) to adapt to resources being available and to amount of services to monitor
* easy to install (just clone or pip install)
* easy to configure (one yaml file)
* easy to enhance (simple python module import)
* easy reuse of probes / notify scripts from nagios / shinken

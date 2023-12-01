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

Installation
------------

With pip::

    pip install timon

For development::

    # clone the git repo
    pip install -e .

Commands
---------
Caution: before launching a command, make sure a timon.yaml config file is available at the place you launch the command

- timon config:  compiles/parses/checks config
- timon run:     runs monitoring (one shot or loop)
- timon status:  displays timon status

Configuration
-------------
.. _config_example: timon/data/examples/timon.yaml

The config file format is not documented, but here at least one config_example_


Probes
======

Here's a list of all developed probes. All probes must inherits from a mother probe and have **resources** class param set and correspond
to a resource described in Resources_ section

Usable probes:
--------------
.. _SubProcBprobe:

timon.probes.SubProcBprobe:
---------------------------
A probe using a subprocess command

conf params:
  :cmd: list of args to run as a command
  :timeout: (integer, default=90) number of seconds after when the subprocess will be kill if it doesn't respond

.. _HttpProbe:

timon.probes.HttpProbe:
-----------------------

probe performing an HTTP request

(inherits from SubProcBprobe_)

conf params:
  :verify_ssl: (bool, default=None) whether ssl server cert should be verified
  :send_cert: (bool, default=False) send certs to the server
  :url: (str) complete_url on which request should be performed to
  :url_params: (list) params to pass to url via % formatters
  :urlpath: default url path if urlparam not set
  :url_param: (str) which probe param contains the relative url

host params:
  :client_cert: (str) path of the client cert
  :hostname: (str) name of the host
  :proto: (str) web protocol (https)
  :port: (int) port to use

2 ways to pass url (CAUTION: Use only 1 of 2):

- PASS COMPLETE URL with *url* and *urlparams* params
  (Caution: order in *urlparams* is important)

  EXAMPLE:
  Next params ::

    url: 'http://titi/%s/%s/croq/'
    url_params:
      - 'Hello'
      - 'World'

  Yields final url:
  'http://titi/Hello/World/croq/'

- PASS URL PARAMS with url_param and urlpath params

timon.probes.ThreadProbe:
-------------------------
just do a print and a sleep ... What's this ????? Remove it perhaps

HttpIsUpProbe:
--------------
checks whether a web server is up
*script_module* = `"timon.scripts.isup"`

timon.probes.SSLCertProbe:
--------------------------
Verify whether an SSL cert is expired or will expire soon

(inherits from SubProcModProbe_)

*script_module* = `"timon.scripts.cert_check"`

conf params:
  :host: (str) name of the host

host params:
  :hostname: (str) name of the host
  :port: (int, default=443) host port to use

timon.probes.SSLClientCAProbe:
------------------------------
Verify whether an SSL Server says, that it accepts certs signed by a given CA

(inherits from SubProcModProbe_)

*script_module* = `"timon.scripts.clientca_check"`

conf params:
  :host: (str) name of the host
  :ca_rex: (str) regular expression that shall match the CA string with format C=../ST=../L=../O=../OU=..CN=../emailAddress=..
host params:
  :hostname: (str) name of the host
  :port: (int, default=443) host port to use

timon.probes.DiskFreeProbe:
---------------------------
just a `pass` , to delete ?

timon.probes.HttpJsonProbe:
---------------------------
probe requesting a json file and checking if a value inside it correspond to a regex.
the rule must be with this form: ``"key1.key2:regexstr"``

(inherits from HttpProbe_)

*script_module* = `"timon.scripts.http_json"`

params:
  :ok_rule: (str) rule to respect to have an OK code
  :warning_rule: (str) rule to respect to have a WARNING code
  :error_rule: (str) rule to respect to have an ERROR code

timon.probes.HttpJsonIntervalProbe:
-----------------------------------
probe requesting a json file and checking if a value inside it is:
  * between 2 values (example: ``"key1.key2:[0, 20]"``)
  * greater than a value (example: ``"key1.key2.key3>60"``)
  * lesser than a value (example: ``"key<20"``)
  * equal to a value (example: ``"key1.key2:200"``)

(inherits from HttpProbe_)

*script_module* = `"timon.scripts.http_json"`

conf params:
  :ok_rule: (str) rule to respect to have an OK code
  :warning_rule: (str) rule to respect to have a WARNING code
  :error_rule: (str) rule to respect to have an ERROR code

Base probes:
------------
(Base probes must be inherited.)

.. _Probe:

timon.probes.Probe:
-------------------
Base class of all probes

conf params:
  :notifiers: (default=[]) list of notifier names to use if probe fails. notifier names must be in yaml conf file (see Notifiers_)
  :schedule: (str, default=None) name of the interval schedular to respect between runs. ex: "2min". Must correspond to an existing schedular conf
    that there are in yaml config file. (see Schedulars_)

.. _SubProcModProbe:

timon.probes.SubProcModProbe:
-----------------------------
A subprocess probe calling the passed module in **script_module** attribute.

Daughter classes must have this script_module attribute

(inherits from SubProcBprobe_)

.. _Resources:

Resources
=========
- subproc
- network
- threads

.. _Schedulars:

Schedulars Conf
===============
In the yaml conf there's a *schedules* part. Each schedular used to launch periodically probes must be contained here.The confs must contain *interval* and *failinterval* attributes.

:interval: interval (int in seconds) after which the probe will be relaunch if everythings ok
:failinterval: interval (int in seconds) after which the probe will be relaunch if an error occurs during previous run

Here an example::

  schedules:
    30sec: {failinterval: 15, interval: 30}

.. _Notifiers:

Notifiers
=========

timon.notifiers.postrequest.PostRequestNotifier
-----------------------------------------------
Send WARNING ERROR CRITICAL probe results to a server via http/https

conf params:
  :url: (str) url where send data
  :cert: (str) .crt path to use

timon.notifiers.cmd.CmdNotifier
-----------------------------------------------

conf params:
  :cmd: (list) ???

Klaus Help !?!?

For Probe Developpers
========================

Timon Probe Scripts
--------------------

Probe scripts are command line scripts, that can be called with some parameters, and that return a status message on stdout.

A status must start with one of the following words:

<STATUS> message

Some functionality is probed:

- OK:  the probed item is working as expected
- WARNING: the probe item is not working as expected, but not in a critical state
- ERROR: the probed item is not working as expected and in a critical state
- UNKNOWN: the item's state could not be retrieved

The exit code of a script depend on the status: pls check (timon/scripts/flags.py)

- OK: exit code 0
- WARNING: exit code 1
- ERROR: exit code 2
- UNKNOWN: exit code 3

For Developpers
================
.. _generic_frontend_info: timon/webclient/README.rst
.. _webif1_frontend_info: timon/webclient/webif1/README.rst

More information about the web front ends generic_frontend_info_
an be found at webif1_frontend_info_


Compiling the web front end
----------------------------

You will require a working node environment.  You might for example use nodeenv or nvm:

nodeenv example::

    pip install -e .
    # TODO: next two lines should be integrated into a build script
    pip install nodeenv
    nodeenv -p -n 12.22.12
    # now build
    timon_build webif all



Testing / Running the web front end(s)
---------------------------------------



Who's using timon
------------------

* MHComm ( https://mhcomm.fr ) for some of their server monitoring

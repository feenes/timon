Timon is a an implementation of a low resource low performance monitoring system.

It has mainly been implemented as a programming exercise, which started when I
noticed, that our monitoring system at work (shinken a python fork of nagios)
was using way too many resources.

I'm sure there's other solutions, which will be more complete, more compatible, 
more efficient, more whatever.
But here my attempt on a simple monitoring solution using few resources, but
still being implemented in a high level language (Python3 with asyncio)


Objectives:
- 0 memory footprint (crontab driven) or low memory footprint
    (one bash / or python process only) while idle 
- asynchronous efficient implementation, but allow threads
    subprocesses
- configurable/skalable  to adapt to resources available and
    amount of services to monitor
- easy to install (just clone or pip install)
- easy to configure (one yaml file)
- easy to enhance (simple python module import)


Commands:
- timon init    create a new timon project
- timon config  compiles/parses/checks config 
- timon run     runs monitoring (one shot or loop)
- timon status  displays timon status


Configuration:
 [a sample config file](timon/data/examples/timon.yaml)


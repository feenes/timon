The Timon Configfile
======================

Timon can be configured with one configfile. 
Lateron we might add features allowing to split the config into multiple files. 

We might also develop some better kind of inheritance in the future, but in the moment the main idea is to use 
little inheritance and simple code to handle the configuration.

Config Sections Overview
-------------------------

* Header sections (config type, version)
* probe description section (what to monitor)
* schedule description (when / how often to monitor)
* Host description section (whom to monitor)
* user section (whom to notify on state changes)
* notifier description (how to notify in state changes)
* default values for sections 
* resource section (not implented/TBD: configuration to limit resources)
* service section (not implemented/TBD: how to control timon while running)
* plugin section (not implemenrted/TBD: how to add plugins)


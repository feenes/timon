#!/usr/bin/env python

# #############################################################################
# Copyright : (C) 2023 by MHComm. All rights reserved
#
# __author__ = "Quentin Laymajoux"
# __email__ = "info@mhcomm.fr"
#
# Name       : timon.plugins
"""
Summary: This folder contains all classic plugins supported by timon.
All plugins have to inherit from timon.plugins.base.TimonBasePlugin

All timon plugins must have coroutines `start` and `stop`.

To permits importing plugins correctly, all plugin files must have a
`plugin_cls` variable that corespond to the plugin class

If you want to enable a plugin and use it, you have to add correct lines in the
plugins section of the timon config file with correct params + an extra
`enabled` param set to True. The plugin name will correspond to the plugin file
name.
"""
# #############################################################################
import logging
from importlib import import_module

from timon.plugins.base import ENABLED_PLUGINS
from timon.plugins.base import TimonBasePlugin

logger = logging.getLogger(__name__)


def get_all_plugins():
    return ENABLED_PLUGINS


def import_plugin(pluginname, cfg, **kwargs):
    module_name = ".".join(["timon", "plugins", pluginname])
    module = import_module(module_name)
    plugin_cls = getattr(module, "plugin_cls")
    plugin = plugin_cls(name=pluginname, cfg=cfg, **kwargs)
    if not isinstance(plugin, TimonBasePlugin):
        raise TypeError(
            "Plugin %s doesn't inherits from "
            "timon.plugins.base.TimonBasePlugin",
            pluginname)
    return plugin


async def start_plugins(nursery):
    """
    Start all imported plugins
    """
    for plugin in ENABLED_PLUGINS:
        if not plugin.is_started:
            nursery.start_soon(plugin.start_plugin, nursery)
        else:
            logger.warning(
                "Trying to start plugin %s but already started",
                plugin.name)


async def stop_plugins(nursery):
    for plugin in ENABLED_PLUGINS:
        if plugin.is_started:
            nursery.start_soon(plugin.stop_plugin, nursery)
        else:
            logger.warning(
                "Trying to stop plugin %s but already stopped",
                plugin.name)

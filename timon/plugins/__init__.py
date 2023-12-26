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
`enabled` param set to True.
The plugin name will correspond to the plugin module name. For generic timon
plugins, the complete module name is not necessary, only the end (the file name
without the extension) can be used.
"""
# #############################################################################
import logging
from importlib import import_module

from timon.plugins.base import ENABLED_PLUGINS
from timon.plugins.base import TimonBasePlugin

logger = logging.getLogger(__name__)


def get_all_plugins():
    return ENABLED_PLUGINS


def import_plugin(pluginmod, cfg, **kwargs):
    if "." in pluginmod:
        module_name = pluginmod
    else:
        module_name = f"timon.plugins.{pluginmod}"
    module = import_module(module_name)
    plugin_cls = getattr(module, "plugin_cls")
    plugin = plugin_cls(name=pluginmod, cfg=cfg, **kwargs)
    if not isinstance(plugin, TimonBasePlugin):
        raise TypeError(
            "Plugin %s doesn't inherits from "
            "timon.plugins.base.TimonBasePlugin",
            pluginmod)
    return plugin


async def start_plugins(async_tg):
    """
    Start all imported plugins
    """
    start_tasks = []
    for plugin in ENABLED_PLUGINS:
        if not plugin.is_started:
            start_tasks.append(async_tg.create_task(plugin.start_plugin()))
        else:
            logger.warning(
                "Trying to start plugin %s but already started",
                plugin.name)
    return start_tasks


async def stop_plugins(async_tg):
    stop_tasks = []
    for plugin in ENABLED_PLUGINS:
        if plugin.is_started:
            stop_tasks.append(async_tg.create_task(plugin.stop_plugin()))
        else:
            logger.warning(
                "Trying to stop plugin %s but already stopped",
                plugin.name)
    return stop_tasks

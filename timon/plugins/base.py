#!/usr/bin/env python

# #############################################################################
# Copyright : (C) 2023 by MHComm. All rights reserved
#
# __author__ = "Quentin Laymajoux"
# __email__ = "info@mhcomm.fr"
#
# Name       : timon.plugins.base
"""
Summary: The timon plugins mother class
"""
# #############################################################################
import logging

ENABLED_PLUGINS = []

logger = logging.getLogger(__name__)


class TimonBasePlugin():
    def __init__(self, name, cfg, **kwargs):
        self.name = name
        self.tmoncfg = cfg
        self.is_started = False
        if kwargs:
            logger.warning(
                "Unknown kwargs for plugin %s : %r", self.name, kwargs)
        ENABLED_PLUGINS.append(self)

    async def start_plugin(self):
        logger.info("Starting plugin %s", self.name)
        await self.start()
        self.is_started = True
        logger.info("Plugin %s started", self.name)

    async def start(self):
        raise NotImplementedError(
            "Plugin %s doesn't have a start method implemented", self.name)

    async def stop_plugin(self):
        logger.info("Stopping plugin %s", self.name)
        await self.stop()
        self.is_started = False
        logger.info("plugin %s stopped", self.name)

    async def stop(self):
        raise NotImplementedError(
            "Plugin %s doesn't have a start method implemented", self.name)


class OnDbStorePluginMixin:
    async def on_db_store(
        self,
        has_state_changed: bool,
        probename: str,
        timestamp: float,
        msg: str,
        status: str
    ):
        raise NotImplementedError(
            "Plugin %s doesn't have on_db_store method implemented", self.name)

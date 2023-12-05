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

    async def start_plugin(self, nursery):
        await self.start(nursery)
        self.is_started = True

    async def start(self, nursery):
        raise NotImplementedError(
            "Plugin %s doesn't have a start method implemented", self.name)

    async def stop_plugin(self, nursery):
        await self.stop(nursery)
        self.is_started = False

    async def stop(self, nursery):
        raise NotImplementedError(
            "Plugin %s doesn't have a start method implemented", self.name)

#!/usr/bin/env python

# #############################################################################
# Copyright : (C) 2023 by MHComm. All rights reserved
#
# __author__ = "Quentin Laymajoux"
# __email__ = "info@mhcomm.fr"
#
# Name       : timon.plugins.timon_httpsrv
"""
Summary: A timon plugin that creates an http server that permits interacting
with timon
"""
# #############################################################################
import asyncio
import logging

from timon.plugins.base import TimonBasePlugin
from timon.plugins.http_server.views import app
from timon.plugins.http_server.views import run_app

logger = logging.getLogger(__name__)


class HttpServerPlugin(TimonBasePlugin):
    def __init__(self, host="localhost", port=12345, **kwargs):
        self.host = host
        self.port = port
        self.srv_task = None
        super().__init__(**kwargs)

    async def start(self):
        setattr(app, "tmoncfg", self.tmoncfg)
        self.srv_task = asyncio.create_task(
            run_app(self.host, self.port))

    async def stop(self):
        self.srv_task.cancel()


plugin_cls = HttpServerPlugin

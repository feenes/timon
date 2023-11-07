#!/usr/bin/env python

# #############################################################################
# Copyright : (C) 2023 by MHComm. All rights reserved
#
# __author__ = "Quentin Laymajoux"
# __email__ = "info@mhcomm.fr"
#
# Name       : timon.plugins.http_server.views
"""
Summary: The http server plugin views and routes
"""
# #############################################################################
import json
import logging

from quart_trio import QuartTrio

logger = logging.getLogger(__name__)

app = QuartTrio(__name__)

KNOWN_ROUTES = {
    "/resources/": "returns a list of all resources and their availability",
    "/heap/": "returns the lenght of the heap",
}


@app.route("/")
async def get_index():
    """
    returns a list of all routes and help text
    """
    return KNOWN_ROUTES


@app.route("/resources/")
async def get_resources():
    """
    returns a list of all resources and their availability
    """
    rsrc_infos = {}
    rsrcs = app.tmoncfg.queue.get_resources()
    for rsrc_name, rsrc in rsrcs.items():
        semaph = rsrc.semaph
        rsrc_infos[rsrc_name] = {
            "value": semaph.value,
        }
    return rsrc_infos


@app.route("/heap/")
async def get_heap_len():
    """
    returns the lenght of the heap
    """
    heap = app.tmoncfg.get_queue().heap
    data_to_return = {
        "heap_length": len(heap)
    }
    return data_to_return

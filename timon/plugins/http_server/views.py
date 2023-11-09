#!/usr/bin/env python

# #############################################################################
# Copyright : (C) 2023 by MHComm. All rights reserved
#
# __author__ = "Quentin Laymajoux"
# __email__ = "info@mhcomm.fr"
#
# Name       : timon.plugins.http_server.views
"""
Summary: The http server plugin's views and routes
"""
# #############################################################################
import logging

from quart_trio import QuartTrio

from timon.probes.probe_if import mk_probe

logger = logging.getLogger(__name__)

app = QuartTrio(__name__)

KNOWN_ROUTES = {
    "/resources/": "returns a list of all resources and their availability",
    "/heap/lenght/": "returns the lenght of the heap",
    "/probes/<?probename>/run/": ("force run the probename and returns "
                                  "the result"),
}


@app.route("/")
async def get_index():
    """
    returns a list of all routes and their help text
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


@app.route("/heap/lenght/")
async def get_heap_len():
    """
    returns the lenght of the heap
    """
    heap = app.tmoncfg.get_queue().heap
    data_to_return = {
        "heap_length": len(heap)
    }
    return data_to_return


@app.route("/probes/<probename>/run/")
async def force_probe_run(probename):
    """
    run corresponding probe and returns the result
    TODO: actually, doesn't change rslt in status file, and doesn't
    update the heap, just run the probe and return the result
    """
    probes = app.tmoncfg.get_probes()
    probe_infos = None
    for probe in probes:
        if probe["name"] == probename:
            probe_infos = probe
            break
    else:
        return {"error": f"cannot find probe {probename}"}
    cls_name = probe_infos['cls']
    prb_dict = dict(
        t_next=0,
        interval=0,
        failinterval=0,
        done_cb=None,
    )
    prb_dict.update(probe_infos)
    probe = mk_probe(cls_name, **prb_dict)
    await probe.run()
    data_to_return = {
        "status": probe.status,
        "msg": probe.msg,
    }
    return data_to_return

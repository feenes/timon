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
import json
import logging
import time

from quart import request
from quart_trio import QuartTrio

from timon.probes.probe_if import mk_probe

logger = logging.getLogger(__name__)

app = QuartTrio(__name__)

KNOWN_ROUTES = {
    "/resources/": (
        "(GET) returns a list of all resources and their"
        " availability"),
    "/queue/": "(GET) returns the queue as a list",
    "/queue/lenght/": "(GET) returns the lenght of the queue",
    "/queue/probe/<probename>/": "(GET) search probe in queue",
    "/probes/<probename>/run/": (
        "(GET) force run the probename and returns "
        "the result"),
    "/rescheduler/probes/": (
        "(POST) reschedule specified probes. request args :"
        "{'probenames': <list of probenames to reschedule>,"
        " 'timestamp': <optional, the timestamp of the "
        "rescheduling>}"),

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
        rsrc_infos[rsrc_name] = {
            "value": rsrc.semaph.value,
        }
    return rsrc_infos


@app.route("/queue/")
async def get_queue():
    """
    returns the probes in queue
    """
    queue = app.tmoncfg.get_queue()
    return queue.as_dict()


@app.route("/queue/lenght/")
async def get_queue_len():
    """
    returns the lenght of the waiting probes
    """
    queue = app.tmoncfg.get_queue()
    data_to_return = {
        "queue_length": len(queue)
    }
    return data_to_return


@app.route("/queue/probe/<probename>/")
async def search_probe_in_queue(probename):
    """
    Search a probe in the queue, and returns it if it exists else returns a 404
    """
    queue = app.tmoncfg.get_queue()
    prb_info = queue.get_probe_n_schedule(probename)
    if prb_info:
        return prb_info
    return (
        f"probe {probename} not found in queue (maybe in running state)",
        404)


@app.route("/probes/<probename>/run/")
async def force_probe_run(probename):
    """
    runs corresponding probe and returns the result
    CAUTION: actually this API, doesn't change rslt in status file, and doesn't
    update the queue, just runs the probe and returns the result
    """
    probes = app.tmoncfg.get_probes()
    probe_infos = None
    for probe in probes:
        if probe["name"] == probename:
            probe_infos = probe
            break
    else:
        return f"cannot find probe {probename}", 404
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


@app.route("/rescheduler/probes/", methods=['POST'])
async def reschedule_probes():
    """
    Reschedule a specific probe to have
    Params in request body:
        - probenames
        - timestamp (optional, default=time.time())
    """
    strdata = await request.get_data()
    data = json.loads(strdata)
    probenames = data["probenames"]
    new_scheduler = data.get("timestamp", time.time())
    queue = app.tmoncfg.get_queue()
    queue.reschedule_probes(probenames=probenames, new_t_next=new_scheduler)
    return "OK"

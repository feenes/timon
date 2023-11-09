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
from heapq import heappop
from heapq import heappush

from quart import jsonify
from quart import request
from quart_trio import QuartTrio

from timon.probes.probe_if import mk_probe

logger = logging.getLogger(__name__)

app = QuartTrio(__name__)

KNOWN_ROUTES = {
    "/resources/": ("(GET) returns a list of all resources and their"
                    " availability"),
    "/queue/": "(GET) returns the heap as a list",
    "/queue/lenght/": "(GET) returns the lenght of the heap",
    "/queue/probe/<probename>/": "(GET) search probe in heap",
    "/probes/<?probename>/run/": ("(GET) force run the probename and returns "
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
        semaph = rsrc.semaph
        rsrc_infos[rsrc_name] = {
            "value": semaph.value,
        }
    return rsrc_infos


@app.route("/queue/")
async def get_queue():
    """
    returns the probes in queue
    """
    heap = app.tmoncfg.get_queue().heap
    copied_heap = heap.copy()
    copied_heap.sort()
    return jsonify(copied_heap)


@app.route("/queue/lenght/")
async def get_queue_len():
    """
    returns the lenght of the waiting probes
    """
    heap = app.tmoncfg.get_queue().heap
    data_to_return = {
        "heap_length": len(heap)
    }
    return data_to_return


@app.route("/queue/probe/<probename>/")
async def search_probe_in_queue(probename):
    """
    Search a probe in the queue, and returns it if it exists else returns a 404
    """
    heap = app.tmoncfg.get_queue().heap
    for item in heap:
        if item[1] == probename:
            return jsonify(item)
    return f"probe {probename} not found in heap", 404


@app.route("/probes/<probename>/run/")
async def force_probe_run(probename):
    """
    runs corresponding probe and returns the result
    CAUTION: actually this API, doesn't change rslt in status file, and doesn't
    update the heap, just runs the probe and returns the result
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
    heap = app.tmoncfg.get_queue().heap
    probes_to_reschedule = []
    other_probes = []
    for idx in range(len(heap)):
        prb_schedular = heappop(heap)
        if prb_schedular[1] in probenames:
            probes_to_reschedule.append(prb_schedular)
        else:
            other_probes.append(prb_schedular)
    for prb_info in other_probes:
        heappush(heap, prb_info)
    for prb_info in probes_to_reschedule:
        prb_info[0] = new_scheduler
        heappush(heap, prb_info)
    return "OK"

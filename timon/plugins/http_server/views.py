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

from quart import Quart
from quart import request

from timon.probes.probe_if import mk_probe

logger = logging.getLogger(__name__)

app = Quart(__name__)


async def run_app(host, port, shutdown_trigger=None):
    await app.run_task(
        host=host, port=port,
        shutdown_trigger=shutdown_trigger,
    )


KNOWN_ROUTES = {
    "/resources/": str(
        "(GET) returns a list of all resources and their"
        " availability"),
    "/queue/": "(GET) returns the queue as a list",
    "/queue/lenght/": "(GET) returns the lenght of the queue",
    "/queue/probe/<probename>/": "(GET) search probe in queue",
    "/probes/<probename>/run/": (
        "(POST) force run the probename and returns "
        "the result"),
    "/probes/<probename>/results/": (
        "(GET) returns the list of results ordered by datetime"
        " for a specific probename"
    ),
    "/probes/<probename>/changes/": (
        "(GET) returns the list of last result status changes"
        " for a specific probename ordered by datetime"
    ),
    "/rescheduler/probes/": (
        "(POST) reschedule specified probes. request args :"
        "{'probenames': <list of probenames to reschedule>,"
        " 'timestamp': <optional, the timestamp of the "
        "rescheduling>}"),
    "/api/hosts/": (
        "(GET) returns the dict of all hosts in the config file."
    ),
    "/api/probes/": (
        "(GET) returns the dict of all probes and their config"
    ),
    "/api/state/": (
        "(GET) returns the probe states (like the timon_state.json"
        " file but thinner)"
    ),
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
            "value": rsrc.semaph._value,
        }
    return rsrc_infos


@app.route("/queue/")
async def get_queue():
    """
    returns the probes in queue
    """
    queue = app.tmoncfg.get_queue()
    return queue.as_dict()


@app.route("/queue/length/")
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


@app.route("/probes/<probename>/run/", methods=['POST'])
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


@app.route("/probes/<probename>/results/", methods=['GET'])
async def get_probe_results(probename):
    dbstore = app.tmoncfg.dbstore
    if not dbstore:
        return "DbStore not activated", 500
    rslts = await dbstore.get_probe_results(probename)
    if not rslts:
        return f"probename {probename} not in db", 404
    return rslts


@app.route("/probes/<probename>/changes/", methods=['GET'])
async def get_probe_result_changes(probename):
    dbstore = app.tmoncfg.dbstore
    if not dbstore:
        return "DbStore not activated", 500
    rslts = await dbstore.get_hist_probe_results(probename)
    if not rslts:
        return f"probename {probename} not in db", 404
    return rslts


@app.route("/api/hosts/", methods=['GET'])
async def get_hosts():
    """
    (GET) returns the dict of all hosts using the
    timoncfg_state.json file
    returns:

    {
    "AHNACPrls": {
            "addr": "c3363-ahnac-mhcare.xtremcloud.fr",
            "fullurl": null,
            "hostname": "c3363-ahnac-mhcare.xtremcloud.fr",
            "name": "AHNACPrls",
            "other_data": {
                "product_level": "PROD",
                "srv_type": "MHCARE"
            },
            "probes": [
                {
                    "probe": "ISUP",
                    "name": "AHNACPrls_isup"
                },
                {
                    "probe": "CELERY",
                    "name": "AHNACPrls_CELERY"
                }
            ],
            "uid": "AHNACP"
        },
    """
    timoncfg_state_file = app.tmoncfg.fname
    with open(timoncfg_state_file, "r") as fin:
        config = json.load(fin)
    data_to_return = {}
    probes_cfg = config["all_probes"]
    for name, host_cfg in config["hosts"].items():
        host_data = {
            "addr": host_cfg["addr"],
            "fullurl": host_cfg["fullurl"],
            "hostname": host_cfg["hostname"],
            "name": name,
            "other_data": host_cfg["other_data"],
            "probes": [],
            "uid": host_cfg["uid"],
        }
        for probename in host_cfg["probes"]:
            host_data["probes"].append(
                {
                    "probe": probes_cfg.get("probename", {}).get("probe"),
                    "name": probename,
                }
            )
        data_to_return[name] = host_data
    return data_to_return


@app.route("/api/probes/", methods=['GET'])
async def get_probes_cfg():
    """
    (GET) returns the dict of all probes and their config using the
    timoncfg_state.json file

    returns:

    {
        "BCB": {
         "name": "BCB",
         "schedule": "5min",
         "schedule_interval": 300,
         "value_rex": "blabla (\d) tata"  # noqa F405
        },
       ..........
    }
    """
    timoncfg_state_file = app.tmoncfg.fname
    with open(timoncfg_state_file, "r") as fin:
        config = json.load(fin)
    probes_cfg = config["probes"]
    schedules_cfg = config["schedules"]
    data_to_return = {}
    for probename, probe_cfg in probes_cfg.items():
        probe_schedule = probe_cfg["schedule"]
        cfg_to_return = {
            "name": probename,
            "schedule": probe_schedule,
            "schedule_interval": schedules_cfg[probe_schedule]["interval"],
            "value_rex": probe_cfg.get("value_rex"),
        }
        data_to_return[probename] = cfg_to_return
    return data_to_return


@app.route("/api/state/", methods=['GET'])
async def get_probes_state():
    """
    Returns the content of probe_state.json file a little cleaner
    """
    timon_state_file = app.tmoncfg.cfg['statefile']
    with open(timon_state_file, "r") as fin:
        tmon_state = json.load(fin)
    return tmon_state["probe_state"]

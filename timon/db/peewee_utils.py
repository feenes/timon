#!/usr/bin/env python

# #############################################################################
# Copyright : (C) 2023 by MHComm. All rights reserved
#
# __author__ = "Quentin Laymajoux"
# __email__ = "info@mhcomm.fr"
#
# Name       : timon.db.serializers
"""
Summary: Serializers and some db funcs that cannot be imported before
the db configuration
"""
# #############################################################################
import logging
from functools import reduce
from threading import Event
from threading import Thread

from timon.conf.flags import FLAG_UNKNOWN_STR
from timon.db.models import ProbeRslt

logger = logging.getLogger(__name__)


def get_probe_results(probename, flushevent, limit=0):
    flushevent.wait()
    qs = ProbeRslt.select().where(ProbeRslt.name == probename).order_by(
        ProbeRslt.dt.desc()).dicts()
    if limit:
        qs = qs.limit(limit)
    rslts = []
    for row in qs:
        rslts.append(row)
    return rslts


class PeeweeDbStoreThread(Thread):
    """
    A thread that permits to write probe results in a peewee db at
    regular intervals.
    For every probe, it have only 10 records and every time it receive
    a new record for a probe, it overwrites the older one to keep this
    number of 10 records.
    """
    def __init__(self, backend, probenames):
        self.backend = backend
        self.rsltqueue = backend.storersltqueue
        self.stopevent = Event()
        self.waitevent = Event()
        self.started = Event()
        self.flushevent = backend.flushevent
        self.interval = 10
        self.chunk_size = 10000  # commit transaction for every self.chunk_size
        # created elements
        self.stored_records = 10
        self.probenames = probenames
        super().__init__()

    def init_db(self):
        """
        If not existing, creates `self.stored_records` fake probe results
        for every probenames
        """
        logger.info("Init db")
        self.backend.db.connect()
        self.backend.db.create_tables([ProbeRslt])
        with self.backend.db.transaction() as transaction:
            chunk_cnt = 0
            to_deletesubqueries = []  # delete is not atomic so deleting by id
            # is an alternative way to have a speeder init
            for prbname in self.probenames:
                cnt_probe = ProbeRslt.select().where(
                    ProbeRslt.name == prbname).count()
                if cnt_probe < self.stored_records:
                    logger.info(
                        "peeweedbstore: creating %d fake probe rslt "
                        "for prb %s", self.stored_records - cnt_probe,
                        prbname,
                        )
                    for idx in range(cnt_probe, self.stored_records):
                        ProbeRslt.create(
                            name=prbname, msg="fake", status=FLAG_UNKNOWN_STR)
                        chunk_cnt += 1
                    if chunk_cnt >= self.chunk_size:
                        transaction.commit()
                        chunk_cnt = 0
                elif cnt_probe > self.stored_records:
                    limit = cnt_probe - self.stored_records
                    logger.info(
                        "peeweedbstore: deleting %d probe rslt "
                        "for prb %s", limit,
                        prbname,
                        )
                    to_deletesubqueries.append(ProbeRslt.select(
                        ProbeRslt.id).where(
                            ProbeRslt.name == prbname).order_by(
                                ProbeRslt.dt.asc()).limit(limit)
                    )
            if to_deletesubqueries:
                len_subqueries = len(to_deletesubqueries)
                step = 20  # cannot use chunk_size because of
                # sqlite3.OperationalError: parser stack overflow
                for start_idx in range(0, len_subqueries, step):
                    end_idx = min(start_idx + step, len_subqueries)
                    delete_query = ProbeRslt.delete().where(
                        reduce(lambda a, b: a | b, (
                            ProbeRslt.id << sq for sq in to_deletesubqueries[
                                start_idx:end_idx]))
                    )
                    delete_query.execute()
        self.is_initialized = True
        logger.info("End init db")

    def store_probe_results(self):
        if not self.rsltqueue.empty():
            with self.backend.db.transaction() as transaction:
                chunk_cnt = 0
                for i in range(self.rsltqueue.qsize()):
                    rslt = self.rsltqueue.get()
                    prbname = rslt["name"]
                    msg = rslt["msg"]
                    status = rslt["status"]
                    dt = rslt["dt"]
                    # UPDATE older result
                    updt_query = ProbeRslt.update(
                        dt=dt, msg=msg, status=status).where(
                            ProbeRslt.id == (
                                ProbeRslt
                                .select(ProbeRslt.id)
                                .where(ProbeRslt.name == prbname)
                                .order_by(ProbeRslt.dt.asc())
                                .limit(1)
                                .scalar()
                            )
                        )
                    updt_query.execute()
                    chunk_cnt += 1
                    if chunk_cnt >= self.chunk_size:
                        transaction.commit()
                        chunk_cnt = 0

    def run(self):
        logger.info("Running PeeweeDbThreadingStore")
        self.init_db()
        self.started.set()
        while not self.stopevent.is_set():
            self.waitevent.wait(self.interval)
            self.store_probe_results()
            self.flushevent.set()
        logger.info("End running PeeweeDbThreadingStore")
        self.started.clear()

    def stop(self):
        self.stopevent.set()
        self.waitevent.set()

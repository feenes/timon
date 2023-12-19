#!/usr/bin/env python

# #############################################################################
# Copyright : (C) 2023 by MHComm. All rights reserved
#
# __author__ = "Quentin Laymajoux"
# __email__ = "info@mhcomm.fr"
#
# Name       : timon.db.peewee_utils
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
from timon.db.models import ProbeRsltChangeHistory

logger = logging.getLogger(__name__)


def get_probe_results(probename, flushevent=None, limit=0):
    if flushevent:
        flushevent.wait()
    qs = ProbeRslt.select().where(ProbeRslt.name == probename).order_by(
        ProbeRslt.dt.desc()).dicts()
    if limit:
        qs = qs.limit(limit)
    rslts = []
    for row in qs:
        rslts.append(row)
    return rslts


def get_hist_probe_results(probename, flushevent=None, limit=0):
    if flushevent:
        flushevent.wait()
    qs = ProbeRsltChangeHistory.select().where(
        ProbeRsltChangeHistory.name == probename).order_by(
            ProbeRsltChangeHistory.dt.desc()).dicts()
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
        self.histrsltqueue = backend.storehistrsltqueue
        self.stopevent = Event()
        self.waitevent = Event()
        self.started = Event()
        self.flushevent = backend.flushevent
        self.interval = 10
        # commit transaction for every self.chunk_size
        # created elements
        self.chunk_size = 10000
        self.stored_records = 10
        self.probenames = probenames
        super().__init__()

    def _populate_tables_with_fake_results(self, model, transaction):
        """
        populate Tables with self.stored_records fake entries for each
        probenames if the number in db is inferior.
        If the number of records in db is superior at self.stored_records,
        delete difference

        Args:
            model (Peewee Db Model): The peewee model to init
            transaction (db.transaction): the transaction to use
        """
        chunk_cnt = 0
        # delete is not atomic so deleting by id
        # is an alternative way to have a faster init
        to_deletesubqueries = []
        for prbname in self.probenames:
            probe_cnt = model.select().where(
                model.name == prbname).count()
            if probe_cnt < self.stored_records:
                logger.info(
                    "peeweedbstore: creating %d fake probe rslt "
                    "for prb %s", self.stored_records - probe_cnt,
                    prbname,
                    )
                for idx in range(probe_cnt, self.stored_records):
                    model.create(
                        name=prbname, msg="fake", status=FLAG_UNKNOWN_STR)
                    chunk_cnt += 1
                if chunk_cnt >= self.chunk_size:
                    transaction.commit()
                    chunk_cnt = 0
            elif probe_cnt > self.stored_records:
                limit = probe_cnt - self.stored_records
                logger.info(
                    "peeweedbstore: deleting %d probe rslt "
                    "for prb %s", limit,
                    prbname,
                    )
                to_deletesubqueries.append(model.select(
                    model.id).where(
                        model.name == prbname).order_by(
                            model.dt.asc()).limit(limit)
                )
        if to_deletesubqueries:
            len_subqueries = len(to_deletesubqueries)
            # cannot use chunk_size because of
            # sqlite3.OperationalError: parser stack overflow
            step = 20
            for start_idx in range(0, len_subqueries, step):
                end_idx = min(start_idx + step, len_subqueries)
                delete_query = ProbeRslt.delete().where(
                    reduce(lambda a, b: a | b, (
                        ProbeRslt.id << sq for sq in to_deletesubqueries[
                            start_idx:end_idx]))
                )
                delete_query.execute()

    def init_db(self):
        """
        If not existing, creates `self.stored_records` fake probe results
        for every probenames
        """
        logger.info("Init db")
        self.backend.db.connect()
        self.backend.db.create_tables([ProbeRslt])
        self.backend.db.create_tables([ProbeRsltChangeHistory])
        with self.backend.db.transaction() as transaction:
            self._populate_tables_with_fake_results(ProbeRslt, transaction)
            self._populate_tables_with_fake_results(
                ProbeRsltChangeHistory, transaction)
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

    def store_hist_probe_results(self):
        if not self.histrsltqueue.empty():
            with self.backend.db.transaction() as transaction:
                chunk_cnt = 0
                for i in range(self.histrsltqueue.qsize()):
                    rslt = self.histrsltqueue.get()
                    prbname = rslt["name"]
                    msg = rslt["msg"]
                    status = rslt["status"]
                    dt = rslt["dt"]
                    # UPDATE older result
                    updt_query = ProbeRsltChangeHistory.update(
                        dt=dt, msg=msg, status=status).where(
                            ProbeRsltChangeHistory.id == (
                                ProbeRsltChangeHistory
                                .select(ProbeRsltChangeHistory.id)
                                .where(ProbeRsltChangeHistory.name == prbname)
                                .order_by(ProbeRsltChangeHistory.dt.asc())
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
            self.store_hist_probe_results()
            self.flushevent.set()
        logger.info("End running PeeweeDbThreadingStore")
        self.started.clear()

    def stop(self):
        self.stopevent.set()
        self.waitevent.set()

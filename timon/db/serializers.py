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
from datetime import datetime
from threading import Thread

from timon.conf.flags import FLAG_UNKNOWN_STR
from timon.db.models import ProbeRslt

logger = logging.getLogger(__name__)


def init_db(db):
    db.connect()
    db.create_tables([ProbeRslt])


class PeeweeDbThreadingStore(Thread):
    """
    A thread that permits to write probe results in a peewee db at
    regular intervals.
    For every probe, it have only 10 records and every time it receive
    a new record for a probe, it overwrite the older one to keep this
    number of 10 records.
    """
    def __init__(self, backend, probenames):
        self.backend = backend
        self.rsltqueue = backend.rsltqueue
        self.stopevent = backend.stopevent
        self.interval = 60
        self.chunk_size = 100
        self.stored_records = 10
        self.probenames = probenames
        super().__init__()

    def init_db(self):
        """
        If don't exist, creates 10 fake probe results for every probenames
        """
        logger.info("Init db")
        with self.backend.db.transaction() as transaction:
            chunk = 0
            for prbname in self.probenames:
                cnt_probe = ProbeRslt.select().where(
                    ProbeRslt.name == prbname).count()
                if cnt_probe < self.stored_records:
                    for idx in range(cnt_probe, self.stored_records):
                        ProbeRslt.create(
                            name=prbname, msg="fake", status=FLAG_UNKNOWN_STR)
                        chunk += 1
                    if chunk >= self.chunk_size:
                        transaction.commit()
                        chunk = 0
        logger.info("End init db")

    def store_probe_results(self):
        if not self.rsltqueue.empty():
            with self.backend.db.transaction() as transaction:
                chunk = 0
                while not self.rsltqueue.empty():
                    rslt = self.rsltqueue.get()
                    prbname = rslt["probename"]
                    msg = rslt["msg"]
                    status = rslt["status"]
                    timestamp = rslt["timestamp"]
                    dt = datetime.fromtimestamp(timestamp)
                    # UPDATE older result
                    ProbeRslt.update(dt=dt, msg=msg, status=status).where(
                        ProbeRslt.name == prbname).order_by(
                            ProbeRslt.dt.asc()).limit(1)
                    chunk += 1
                    if chunk >= self.chunk_size:
                        transaction.commit()
                        chunk = 0

    def run(self):
        logger.info("Running PeeweeDbThreadingStore")
        self.init_db()
        while not self.stopevent.is_set():
            self.stopevent.wait(self.interval)
            self.store_probe_results()
        logger.info("End running PeeweeDbThreadingStore")

#!/usr/bin/env python

# #############################################################################
# Copyright : (C) 2023 by MHComm. All rights reserved
#
# __author__ = "Quentin Laymajoux"
# __email__ = "info@mhcomm.fr"
#
# Name       : timon.db.backends
"""
Summary: Backend Classes to use in dbstore
"""
# #############################################################################
import logging
from queue import Queue
from threading import Event

from peewee import SqliteDatabase

logger = logging.getLogger(__name__)


class BaseBackend():
    """
    This class is unuseful, but helps to know which funcs must be implemented
    in backends
    """

    def __init__(self, **db_cfg):
        raise NotImplementedError("BaseBackend must be inherited")

    def stop(self):
        """
        Cleanly stop the backend
        """
        raise NotImplementedError("Backend stop func must be implemented")

    def setup(self, probenames):
        """
        Setup and start the backend
        """
        raise NotImplementedError("Backend setup func must be implemented")

    def store_probe_result(self, probename, timestamp, msg, status):
        """Store a probe result

        Args:
            probename (str): name of the probe
            timestamp (int|float): timestamp if the probe run
            msg (str): probe rslt message
            status (str): status of the probe result
        """
        raise NotImplementedError(
            "Backend store_probe_result func must be implemented")


class PeeweeBaseBackend(BaseBackend):
    """
    Store probe results in a db via peewee ORM
    CAUTION: must be inherited and _get_db func must be
    implemented.
    """
    def __init__(self, **db_cfg):
        self.rsltqueue = Queue(maxsize=10000)
        self.stopevent = Event()
        self.thread_store = None
        self.db = None

    def setup(self, probenames):
        from timon.db.serializers import PeeweeDbThreadingStore
        from timon.db.serializers import init_db
        self.thread_store = PeeweeDbThreadingStore(self, probenames)
        self.db = db = self._get_db()
        init_db(db)
        self.thread_store.start()

    def stop(self):
        logger.info("Stopping Peewee backend")
        self.stopevent.set()
        self.thread_store.join()

    def store_probe_result(self, probename, timestamp, msg, status):
        prb_rslt = {
            "probename": probename,
            "msg": msg,
            "status": status,
            "timestamp": timestamp,
        }
        self.rsltqueue.put(prb_rslt)

    def _get_db(self):
        raise NotImplementedError(
            "PeeweeBackend _get_db func must be implemented")


class PeeweeSqliteBackend(PeeweeBaseBackend):
    """
    Store results in an sqlite db
    """
    def __init__(self, **db_cfg):
        self.db_fpath = db_cfg["db_fpath"]
        super().__init__(**db_cfg)

    def _get_db(self):
        db = SqliteDatabase(self.db_fpath)
        return db

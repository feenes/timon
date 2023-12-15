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
from datetime import datetime
from queue import Queue
from threading import Event

import trio
from peewee import SqliteDatabase

logger = logging.getLogger(__name__)


THREAD_SEMAPHORE = trio.Semaphore(5)


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

    def start(self, probenames):
        """
        Setup and start the backend
        """
        raise NotImplementedError("Backend setup func must be implemented")

    async def get_probe_results(self, probename):
        """
        Get probe results for a given probename
        Rslts is a list of dict ordered by datetime
        """
        raise NotImplementedError(
            "Backend get_probe_results func must be implemented")

    async def store_probe_result(self, probename, timestamp, msg, status):
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
        self.storersltqueue = Queue(maxsize=10000)
        self.flushevent = Event()
        self.store_thread = None
        self.db = None

    def start(self, probenames):
        self.db = self._get_db()
        from timon.db import peewee_utils
        self.store_thread = peewee_utils.PeeweeDbStoreThread(self, probenames)
        self.store_thread.start()

    def stop(self):
        logger.info("Stopping Peewee backend")
        self.store_thread.stop()
        self.store_thread.join()
        self.db.close()

    def _request_flush(self):
        """
        Ask the flush of the queue in db
        """
        self.flushevent.clear()
        self.store_thread.waitevent.set()
        self.store_thread.waitevent.clear()

    async def get_probe_results(self, probename):
        from timon.db.peewee_utils import get_probe_results
        self._request_flush()
        async with THREAD_SEMAPHORE:
            return await trio.to_thread.run_sync(
                get_probe_results, probename, self.flushevent)

    async def store_probe_result(self, probename, timestamp, msg, status):
        prb_rslt = {
            "name": probename,
            "msg": msg,
            "status": status,
            "dt": datetime.fromtimestamp(timestamp),
        }
        while self.storersltqueue.full():
            self._request_flush()
            await trio.sleep(0.1)
        self.storersltqueue.put(prb_rslt)

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

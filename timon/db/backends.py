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
import asyncio
import logging
from datetime import datetime
from queue import Queue
from threading import Event

from peewee import SqliteDatabase

logger = logging.getLogger(__name__)

# a semaphore that limits the number of concurrent threads
THREAD_SEMAPHORE = asyncio.Semaphore(5)


class BaseBackend():
    """
    This class is an abstract class and is useless, but helps to know
    which funcs must be implemented in backends
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
        Setup and start the backend.
        Probenames are the list of all probenames. Used to populate the db
        with fake results first time (or delete if there's too many)
        """
        raise NotImplementedError("Backend setup func must be implemented")

    async def get_probe_results(self, probename):
        """
        Get probe results for a given probename
        Rslts is a list of dict ordered by datetime
        """
        raise NotImplementedError(
            "Backend get_probe_results func must be implemented")

    async def get_hist_probe_results(self, probename):
        """
        Get history probe result (state changed) for a given probename
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

    async def store_hist_probe_result(self, probename, timestamp, msg, status):
        """Store a history probe result (state changed)

        Args:
            probename (str): name of the probe
            timestamp (int|float): timestamp if the probe run
            msg (str): probe rslt message
            status (str): status of the probe result
        """
        raise NotImplementedError(
            "Backend store_hist_probe_result func must be implemented")


class PeeweeBaseBackend(BaseBackend):
    """
    Store probe results in a db via peewee ORM
    CAUTION: must be inherited and _get_db func must be
    implemented.
    """
    def __init__(self, **db_cfg):
        self.storersltqueue = Queue(maxsize=10000)
        self.storehistrsltqueue = Queue(maxsize=10000)
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
            return await asyncio.to_thread(
                get_probe_results, probename, self.flushevent)

    async def get_hist_probe_results(self, probename):
        from timon.db.peewee_utils import get_hist_probe_results
        self._request_flush()
        async with THREAD_SEMAPHORE:
            return await asyncio.to_thread(
                get_hist_probe_results, probename, self.flushevent)

    async def store_probe_result(self, probename, timestamp, msg, status):
        prb_rslt = {
            "name": probename,
            "msg": msg,
            "status": status,
            "dt": datetime.fromtimestamp(timestamp),
        }
        if self.storersltqueue.full():
            logger.warning("rslt queue is full, flushing and waiting")
            while self.storersltqueue.full():
                self._request_flush()
                await asyncio.sleep(0.1)
            logger.warning("rslt queue isn't full anymore")
        self.storersltqueue.put(prb_rslt)

    async def store_hist_probe_result(self, probename, timestamp, msg, status):
        prb_rslt = {
            "name": probename,
            "msg": msg,
            "status": status,
            "dt": datetime.fromtimestamp(timestamp),
        }
        if self.storehistrsltqueue.full():
            logger.warning("hist rslt queue is full, flushing and waiting")
            while self.storehistrsltqueue.full():
                self._request_flush()
                await asyncio.sleep(0.1)
            logger.warning("hist rslt queue isn't full anymore")
        self.storehistrsltqueue.put(prb_rslt)

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

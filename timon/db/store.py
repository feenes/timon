#!/usr/bin/env python

# #############################################################################
# Copyright : (C) 2023 by MHComm. All rights reserved
#
# __author__ = "Quentin Laymajoux"
# __email__ = "info@mhcomm.fr"
#
# Name       : timon.db.store
"""
Summary: Abstraction Class for Db Store
"""
# #############################################################################
import logging
import signal

logger = logging.getLogger(__name__)


store = None


class DbStore():
    """
    Abstraction class for DbStore. backend attr must be defined
    (at instant, only PeeweeSqliteBackend was developed so it is hardcoded)
    """
    instantiated = False

    def __init__(self, **db_cfg):
        from timon.db.backends import PeeweeSqliteBackend
        if self.__class__.instantiated:
            raise Exception("DbStore already instanciated, cannot be twice")
        self.__class__.instantiated = True
        self.backend = PeeweeSqliteBackend(**db_cfg)
        self.started = False

    def stop(self):
        logger.info("Stopping DBSTORE")
        self.backend.stop()
        self.started = False

    def start(self, probenames):
        logger.info("Starting DBSTORE")
        if self.started:
            logger.warning("DbStore already started ....")
            return
        self.backend.start(probenames)
        self.started = True

        def my_signal_handler(signum, frame):
            if self.started:
                self.stop()
        self.old_sigint = signal.getsignal(signal.SIGINT)
        self.old_sigterm = signal.getsignal(signal.SIGTERM)
        signal.signal(signal.SIGTERM, my_signal_handler)
        signal.signal(signal.SIGINT, my_signal_handler)

    def store_probe_result(self, probename, timestamp, msg, status):
        self.backend.store_probe_result(probename, timestamp, msg, status)


def get_store(**db_cfg):
    global store
    store = DbStore(**db_cfg)
    return store

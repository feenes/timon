#!/usr/bin/env python
"""
#############################################################################
Copyright : (C) 2023 by Teledomic.eu All rights reserved

Name:         timon.tests.test_db

Description:  some unit tests for checking db class and functions

#############################################################################
"""
import asyncio
import time
from datetime import datetime
from pathlib import Path
from unittest import TestCase

from timon.db.store import get_store


class DbStoreTestCase(TestCase):
    def setUp(self):
        self.dbstore = None
        return super().setUp()

    def tearDown(self):
        if self.dbstore:
            self.dbstore.stop()
        return super().tearDown()

    def test_peeweesqlite_dbstore(self):
        """
        check that the dbstore can be initialized and rslts are correctly
        written in db
        """
        sqlite_db_fname = "timon_tstsqlite.db"
        sqlite_db_fpath = Path(sqlite_db_fname)
        if sqlite_db_fpath.exists():
            sqlite_db_fpath.unlink()
        prbname = "PRBNAME0"
        self.dbstore = dbstore = get_store(db_fpath=sqlite_db_fname)
        # TEST INIT AND FAKE POPULATE
        dbstore.start(probenames=[prbname])
        store_thread = dbstore.backend.store_thread
        store_thread.started.wait()
        limit = store_thread.stored_records
        rslts = asyncio.run(dbstore.get_probe_results(prbname))
        hist_rslts = asyncio.run(dbstore.get_hist_probe_results(prbname))
        # Check the db is correctly initialized
        # CHeck fake probe rslts
        assert len(rslts) == limit
        for rslt in rslts:
            assert rslt["msg"] == "fake"
        # CHeck fake hist probe rslts
        assert len(hist_rslts) == limit
        for rslt in hist_rslts:
            assert rslt["msg"] == "fake"
        # Creating a result
        probe_result = {
            "probename": prbname,
            "timestamp": time.time(),
            "msg": "msg1",
            "status": "OK",
        }
        expected_probe_record = probe_result.copy()
        expected_probe_record["dt"] = datetime.fromtimestamp(
            expected_probe_record["timestamp"])
        expected_probe_record.pop("timestamp")
        expected_probe_record["name"] = expected_probe_record["probename"]
        expected_probe_record.pop("probename")
        asyncio.run(dbstore.store_probe_result(*probe_result.values()))
        # TEST PROBE RESULT
        rslts = asyncio.run(dbstore.get_probe_results(prbname))
        assert len(rslts) == limit
        rslt_in_db = rslts[0]
        assert rslt_in_db.get("id")
        for key, val in expected_probe_record.items():
            assert rslt_in_db[key] == val
        asyncio.run(dbstore.store_probe_result(*probe_result.values()))
        # TEST HIST PROBE RESULT
        asyncio.run(dbstore.store_hist_probe_result(*probe_result.values()))
        hist_rslts = asyncio.run(dbstore.get_hist_probe_results(prbname))
        assert len(hist_rslts) == limit
        rslt_in_db = hist_rslts[0]
        assert rslt_in_db.get("id")
        for key, val in expected_probe_record.items():
            assert rslt_in_db[key] == val

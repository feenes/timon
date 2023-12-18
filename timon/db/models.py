#!/usr/bin/env python

# #############################################################################
# Copyright : (C) 2023 by UNKNOWN. All rights reserved
#
# __author__ = "Quentin Laymajoux"
#
# Name       : timon.db.models
"""
Summary: Peewee models for probe results
"""
# #############################################################################
import datetime
import logging

from peewee import CharField
from peewee import DateTimeField
from peewee import Model
from peewee import TextField

from timon.conf.flags import FLAG_MAP
from timon.db import store

logger = logging.getLogger(__name__)


db = store.store.backend.db

STATUS_CHOICES = {key: key for key in FLAG_MAP.keys()}


class ProbeRslt(Model):
    """
    Model of a Probe result object
    """
    name = CharField(index=True)
    dt = DateTimeField(default=datetime.datetime.now)
    msg = TextField()
    status = CharField(choices=STATUS_CHOICES)

    class Meta:
        database = db

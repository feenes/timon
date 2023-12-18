#!/usr/bin/env python

# #############################################################################
# Copyright : (C) 2023 by MHComm. All rights reserved
#
# __author__ = "Klaus Foerster"
# __email__ = "info@mhcomm.fr"
#
# Name       : timon.tests.test_crt.py
"""
Summary      : test probes that check certs

"""
# #############################################################################
from datetime import datetime
from datetime import timedelta
from random import randint
from unittest.mock import patch

from timon.scripts.cert_check import get_cert_info
from timon.scripts.cert_check import get_cert_status


class MockCert:
    """
    MockCertObject

    helping to create a cert with a certain duration
    and a certain remaining validity time
    """
    def __init__(self, duration=90, remaining=21):
        """
        :param duration: the duration the cert is valid
        :param remaining: days remaining till cert is invalid
        """
        now = datetime.now()
        self.not_valid_after = now + timedelta(days=remaining, seconds=1)
        self.not_valid_before = (
            self.not_valid_after - timedelta(duration))

    def __str__(self):
        return f"{self.not_valid_before} - {self.not_valid_after}"


def mock_cert_info(hostname, port, servername):
    """
    mock for timon.scripts.cert_check:get_cert_info

    to avoid real ssl traffic for testing
    """

    if "long" in hostname:
        duration = randint(101, 200)
        remaining = 40
    else:
        duration = randint(30, 99)
        remaining = 20

    if "invalid" in hostname:
        remaining -= randint(1, 19)
    elif "expired" in hostname:
        remaining = randint(-100, -1)
    else:  # valid
        remaining = min(remaining + randint(1, 40), duration-1)
    remaining = min(remaining, duration)

    cert = MockCert(duration=duration, remaining=remaining)

    print(hostname, duration, remaining, cert)
    return cert


@patch('timon.scripts.cert_check.get_cert_info', mock_cert_info)
def test_cert_check():
    status = get_cert_status("expired_short", 443, "invalid_short")
    print(status)
    assert status[0] == "ERROR"
    status = get_cert_status("expired_long", 443, "invalid_long")
    print(status)
    assert status[0] == "ERROR"

    status = get_cert_status("invalid_short", 443, "invalid_short")
    print(status)
    assert status[0] == "WARNING"
    status = get_cert_status("invalid_long", 443, "invalid_long")
    print(status)
    assert status[0] == "WARNING"

    status = get_cert_status("valid_long", 443, "valid_long")
    print(status)
    assert status[0] == "OK"

    status = get_cert_status("valid_short", 443, "valid_short")
    print(status)
    assert status[0] == "OK"


def test_get_cert_info():
    cert = get_cert_info("github.com", 443, "github.com")
    not_bef = cert.not_valid_before
    assert isinstance(not_bef, datetime)
    not_aft = cert.not_valid_after
    assert isinstance(not_aft, datetime)
    subject = cert.subject
    print(not_bef, not_aft, repr(subject))
    assert "github.com" in str(subject)

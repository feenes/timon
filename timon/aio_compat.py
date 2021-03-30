"""
Layer allowing to write 'more modern' asyncio code with older pythons (3.6)
"""
import sys

VER = sys.version_info[:2]

if VER >= (3, 7):
    from asyncio import get_running_loop  # noqa: F401
else:
    from asyncio import get_event_loop as get_running_loop  # noqa: F401

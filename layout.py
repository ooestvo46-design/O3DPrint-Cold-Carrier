"""
layout.py

Compatibility wrapper around geometry.Layout.
"""

from geometry import Layout


def create_layout():
    return Layout()


def can_centers():
    return Layout().canCenters()


def ice_pack():
    return Layout().icePack()


def base():
    return Layout().base()


def handle_slots():
    layout = Layout()
    if hasattr(layout, "handleGuideRails"):
        return layout.handleGuideRails()
    return []


def vent_slots():
    return Layout().ventSlots()


def drain_points():
    return Layout().drainPoints()

"""
geometry.py

Parametric geometry calculations for O3DPrint Cold Carrier V2.
No Fusion API here. Only math/layout logic.
"""

from config import PARAMETERS


class Layout:
    def __init__(self):
        self.canDiameter = PARAMETERS["canDiameter"]
        self.canRadius = self.canDiameter / 2.0

        self.wall = PARAMETERS["wall"]
        self.bottomThickness = PARAMETERS["bottomThickness"]

        self.iceWidth = PARAMETERS["iceWidth"]
        self.iceThickness = PARAMETERS["iceThickness"]
        self.iceHeight = PARAMETERS["iceHeight"]

        self.airGap = PARAMETERS["airGap"]
        self.guideRail = PARAMETERS["guideRail"]
        self.guideRailHeight = PARAMETERS.get("guideRailHeight", 55.0)

        self.holderInnerRadius = self.canRadius + 1.0
        self.holderOuterRadius = self.holderInnerRadius + self.wall

        self.coolingGap = 2.5
        self.leftX = -(self.iceThickness / 2.0 + self.coolingGap + self.holderOuterRadius)
        self.rightX = +(self.iceThickness / 2.0 + self.coolingGap + self.holderOuterRadius)

        self.rowSpacing = self.canDiameter + 3.0
        self.rows = (-self.rowSpacing, 0.0, self.rowSpacing)

        self.outerMarginX = 8.0
        self.outerMarginY = 9.0
        self.cornerCut = 18.0

    def canCenters(self):
        points = []
        for x in (self.leftX, self.rightX):
            for y in self.rows:
                points.append((x, y))
        return points

    def icePack(self):
        return (
            -self.iceThickness / 2.0,
            -self.iceHeight / 2.0,
            self.iceThickness,
            self.iceHeight,
        )

    def base(self):
        centers = self.canCenters()
        minX = min(x for x, _ in centers) - self.holderOuterRadius - self.outerMarginX
        maxX = max(x for x, _ in centers) + self.holderOuterRadius + self.outerMarginX
        minY = min(y for _, y in centers) - self.holderOuterRadius - self.outerMarginY
        maxY = max(y for _, y in centers) + self.holderOuterRadius + self.outerMarginY
        return (minX, minY, maxX - minX, maxY - minY)

    def basePolygon(self):
        x, y, width, height = self.base()
        corner = min(self.cornerCut, width / 4.0, height / 4.0)
        return [
            (x + corner, y),
            (x + width - corner, y),
            (x + width, y + corner),
            (x + width, y + height - corner),
            (x + width - corner, y + height),
            (x + corner, y + height),
            (x, y + height - corner),
            (x, y + corner),
        ]

    def iceGuideRails(self):
        rail_length = self.iceHeight - 8.0
        y = -rail_length / 2.0
        return [
            (-self.iceThickness / 2.0 - self.guideRail, y, self.guideRail, rail_length),
            (self.iceThickness / 2.0, y, self.guideRail, rail_length),
        ]

    def centerStop(self):
        return (
            -self.iceThickness / 2.0 - self.guideRail,
            -self.iceHeight / 2.0 - 4.0,
            self.iceThickness + 2.0 * self.guideRail,
            5.0,
        )

    def handleGuideRails(self):
        x, y, width, height = self.base()
        rail_width = 7.0
        rail_length = 36.0
        inset = 12.0
        return [
            (x + inset, y + height / 2.0 - rail_length / 2.0, rail_width, rail_length),
            (x + width - inset - rail_width, y + height / 2.0 - rail_length / 2.0, rail_width, rail_length),
        ]

    def coolingRibs(self):
        ribs = []
        rib_width = 3.0

        for x in (self.leftX, self.rightX):
            side = -1 if x < 0 else 1
            inner_x = side * (self.iceThickness / 2.0 + 1.5)
            outer_x = x - side * (self.holderInnerRadius + 2.0)
            width = abs(outer_x - inner_x)
            start_x = min(inner_x, outer_x)

            for y in self.rows:
                ribs.append((start_x, y - rib_width / 2.0, width, rib_width))

        return ribs

    def raisedCanPads(self):
        pads = []
        pad_radius = 3.8
        offset = self.canRadius * 0.48

        for cx, cy in self.canCenters():
            pads.append((cx, cy + offset, pad_radius))
            pads.append((cx - offset * 0.866, cy - offset / 2.0, pad_radius))
            pads.append((cx + offset * 0.866, cy - offset / 2.0, pad_radius))

        return pads

    def drainPoints(self):
        points = [(0.0, 0.0)]
        points.extend(self.canCenters())
        return points

    def ventSlots(self):
        slots = []
        slot_width = 3.0
        slot_height = 12.0

        for side in (-1, 1):
            x = side * (self.iceThickness / 2.0 + self.guideRail + 2.0)
            for y in (-50.0, -25.0, 0.0, 25.0, 50.0):
                slots.append((x - slot_width / 2.0, y - slot_height / 2.0, slot_width, slot_height))

        return slots

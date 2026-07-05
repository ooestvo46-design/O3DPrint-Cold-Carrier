"""
geometry.py

All 2D layout calculations for O3DPrint Cold Carrier.
No Fusion API here.
Only math.
"""

from config import PARAMETERS


class Layout:

    def __init__(self):

        self.canDiameter = PARAMETERS["canDiameter"]

        self.canRadius = self.canDiameter / 2

        self.wall = PARAMETERS["wall"]

        self.iceThickness = PARAMETERS["iceThickness"]

        self.iceHeight = PARAMETERS["iceHeight"]

        self.airGap = PARAMETERS["airGap"]

        self.spacing = self.canDiameter + self.airGap

        self.leftX = -(self.iceThickness / 2 + self.airGap + self.canRadius)

        self.rightX = +(self.iceThickness / 2 + self.airGap + self.canRadius)

        self.holderInnerRadius = self.canRadius + self.airGap / 2

        self.holderOuterRadius = self.holderInnerRadius + self.wall

        self.row1 = -self.spacing
        self.row2 = 0
        self.row3 = self.spacing

    def canCenters(self):

        return [

            (self.leftX, self.row1),

            (self.leftX, self.row2),

            (self.leftX, self.row3),

            (self.rightX, self.row1),

            (self.rightX, self.row2),

            (self.rightX, self.row3)

        ]

    def icePack(self):

        return (

            -self.iceThickness / 2,

            -self.iceHeight / 2,

            self.iceThickness,

            self.iceHeight

        )

    def base(self):

        centers = self.canCenters()

        minX = min(x for x, y in centers) - self.holderOuterRadius - self.wall
        maxX = max(x for x, y in centers) + self.holderOuterRadius + self.wall
        minY = min(y for x, y in centers) - self.holderOuterRadius - self.wall
        maxY = max(y for x, y in centers) + self.holderOuterRadius + self.wall

        return (

            minX,

            minY,

            maxX - minX,

            maxY - minY

        )

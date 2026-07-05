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
        self.frameOpeningWeb = PARAMETERS["frameOpeningWeb"]
        self.structuralRib = PARAMETERS["structuralRib"]
        self.outerFrameRib = PARAMETERS["outerFrameRib"]
        self.holderBlendRib = PARAMETERS["holderBlendRib"]
        self.moldedWebRib = PARAMETERS["moldedWebRib"]
        self.sideBandRib = PARAMETERS["sideBandRib"]
        self.iceRailWidth = PARAMETERS["iceRailWidth"]
        self.handleReceiverRib = PARAMETERS["handleReceiverRib"]
        self.sidePanelHeight = PARAMETERS["sidePanelHeight"]
        self.sidePanelThickness = PARAMETERS["sidePanelThickness"]
        self.holderButtressRib = PARAMETERS["holderButtressRib"]
        self.iceShoulderRib = PARAMETERS["iceShoulderRib"]

        self.holderInnerRadius = self.canRadius + 1.0
        self.holderOuterRadius = self.holderInnerRadius + self.wall

        self.coolingGap = PARAMETERS["coolingGap"]
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
            (-self.iceThickness / 2.0 - self.iceRailWidth, y, self.iceRailWidth, rail_length),
            (self.iceThickness / 2.0, y, self.iceRailWidth, rail_length),
        ]

    def iceGuideRibs(self):
        rail_length = self.iceHeight - 8.0
        lower_y = -rail_length / 2.0
        upper_y = rail_length / 2.0
        return [
            (-self.iceThickness / 2.0 - self.iceRailWidth / 2.0, lower_y,
             -self.iceThickness / 2.0 - self.iceRailWidth / 2.0, upper_y,
             self.iceRailWidth),
            (self.iceThickness / 2.0 + self.iceRailWidth / 2.0, lower_y,
             self.iceThickness / 2.0 + self.iceRailWidth / 2.0, upper_y,
             self.iceRailWidth),
        ]

    def iceChannelBlendRibs(self):
        rail_length = self.iceHeight - 8.0
        lower_y = -rail_length / 2.0
        upper_y = rail_length / 2.0
        flare = self.iceRailWidth * 2.2
        rail_left = -self.iceThickness / 2.0 - self.iceRailWidth / 2.0
        rail_right = self.iceThickness / 2.0 + self.iceRailWidth / 2.0

        return [
            (rail_left - flare, lower_y - flare, rail_left, lower_y, self.iceRailWidth),
            (rail_right + flare, lower_y - flare, rail_right, lower_y, self.iceRailWidth),
            (rail_left - flare, upper_y + flare, rail_left, upper_y, self.iceRailWidth),
            (rail_right + flare, upper_y + flare, rail_right, upper_y, self.iceRailWidth),
        ]

    def centerStop(self):
        return (
            -self.iceThickness / 2.0 - self.iceRailWidth,
            -self.iceHeight / 2.0 - 4.0,
            self.iceThickness + 2.0 * self.iceRailWidth,
            5.0,
        )

    def centerStopRib(self):
        y = -self.iceHeight / 2.0 - 1.5
        return (
            -self.iceThickness / 2.0 - self.iceRailWidth / 2.0,
            y,
            self.iceThickness / 2.0 + self.iceRailWidth / 2.0,
            y,
            self.iceRailWidth,
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
        rib_positions = [
            (self.rows[0] + self.rows[1]) / 2.0,
            (self.rows[1] + self.rows[2]) / 2.0,
        ]

        for x in (self.leftX, self.rightX):
            side = -1 if x < 0 else 1
            inner_x = side * (self.iceThickness / 2.0 + 1.5)
            outer_x = x - side * (self.holderInnerRadius + 2.0)
            width = abs(outer_x - inner_x)
            start_x = min(inner_x, outer_x)

            for y in rib_positions:
                ribs.append((start_x, y - rib_width / 2.0, width, rib_width))

        return ribs

    def structuralRibs(self):
        ribs = []
        centers = self.canCenters()
        left_centers = [point for point in centers if point[0] < 0]
        right_centers = [point for point in centers if point[0] > 0]
        tangent_offset = self.holderInnerRadius + self.structuralRib / 2.0

        for column in (left_centers, right_centers):
            column = sorted(column, key=lambda point: point[1])
            for start, end in zip(column, column[1:]):
                for side in (-1, 1):
                    x = start[0] + side * tangent_offset
                    waist_x = x - side * (self.structuralRib * 0.48)
                    middle_y = (start[1] + end[1]) / 2.0
                    fade = self.holderOuterRadius * 0.42

                    ribs.append((x, start[1] + fade, waist_x, middle_y, self.structuralRib))
                    ribs.append((waist_x, middle_y, x, end[1] - fade, self.structuralRib))

        return ribs

    def moldedWebRibs(self):
        ribs = []
        rail_left = -self.iceThickness / 2.0 - self.iceRailWidth / 2.0
        rail_right = self.iceThickness / 2.0 + self.iceRailWidth / 2.0
        inner_overlap = self.holderOuterRadius - 3.0

        for cx, cy in self.canCenters():
            side = -1 if cx < 0 else 1
            channel_x = rail_left if side < 0 else rail_right
            inner_x = cx - side * inner_overlap
            y_delta = self.rowSpacing * 0.32
            outer_y_delta = self.rowSpacing * 0.18

            ribs.append((inner_x, cy + y_delta, channel_x, cy, self.moldedWebRib))
            ribs.append((inner_x, cy - y_delta, channel_x, cy, self.moldedWebRib))
            ribs.append((cx, cy + outer_y_delta, channel_x, cy + y_delta, self.moldedWebRib * 0.66))
            ribs.append((cx, cy - outer_y_delta, channel_x, cy - y_delta, self.moldedWebRib * 0.66))

        for y in (
            (self.rows[0] + self.rows[1]) / 2.0,
            (self.rows[1] + self.rows[2]) / 2.0,
        ):
            ribs.append((
                self.leftX + self.holderInnerRadius,
                y,
                self.rightX - self.holderInnerRadius,
                y,
                self.moldedWebRib * 0.72,
            ))

        return ribs

    def holderBlendRibs(self):
        ribs = []
        overlap = 3.0
        blend_length = self.holderOuterRadius * 0.32
        radial_start = self.holderOuterRadius - overlap
        radial_end = self.holderOuterRadius + blend_length

        for cx, cy in self.canCenters():
            side = -1 if cx < 0 else 1
            directions = [
                (side, 0.0),
                (0.0, -1.0),
                (0.0, 1.0),
                (-side * 0.65, -0.76),
                (-side * 0.65, 0.76),
                (side * 0.55, -0.83),
                (side * 0.55, 0.83),
            ]

            for dx, dy in directions:
                length = (dx * dx + dy * dy) ** 0.5
                unit_x = dx / length
                unit_y = dy / length
                ribs.append((
                    cx + unit_x * radial_start,
                    cy + unit_y * radial_start,
                    cx + unit_x * radial_end,
                    cy + unit_y * radial_end,
                    self.holderBlendRib,
                ))

        return ribs

    def perimeterRibs(self):
        ribs = []
        side_offset = self.holderOuterRadius + self.sideBandRib / 2.0 - 6.0
        end_offset = self.holderOuterRadius + self.sideBandRib / 2.0 - 10.0

        for column_x, side in ((self.leftX, -1), (self.rightX, 1)):
            outer_x = column_x + side * side_offset
            waist_x = outer_x - side * (self.sideBandRib * 1.25)
            shoulder_x = column_x - side * (self.holderOuterRadius * 0.45)
            bottom_y = self.rows[0] - end_offset
            top_y = self.rows[2] + end_offset

            for lower, upper in zip(self.rows, self.rows[1:]):
                middle = (lower + upper) / 2.0
                fade = self.holderOuterRadius * 0.38
                ribs.append((outer_x, lower + fade, waist_x, middle, self.sideBandRib))
                ribs.append((waist_x, middle, outer_x, upper - fade, self.sideBandRib))

            ribs.append((outer_x, top_y, shoulder_x, self.rows[2] + self.holderOuterRadius * 0.55, self.sideBandRib))
            ribs.append((outer_x, bottom_y, shoulder_x, self.rows[0] - self.holderOuterRadius * 0.55, self.sideBandRib))

            ribs.append((outer_x, self.rows[0], column_x, self.rows[0] - self.holderOuterRadius * 0.8, self.sideBandRib))
            ribs.append((outer_x, self.rows[2], column_x, self.rows[2] + self.holderOuterRadius * 0.8, self.sideBandRib))

        return ribs

    def verticalSidePanels(self):
        panels = []
        panel_span = self.holderOuterRadius * 0.84
        y_min = self.rows[0] - panel_span
        y_max = self.rows[2] + panel_span
        z_min = self.bottomThickness
        z_max = self.bottomThickness + self.sidePanelHeight

        for column_x, side in ((self.leftX, -1), (self.rightX, 1)):
            x = column_x + side * (self.holderOuterRadius + self.sidePanelThickness * 0.45)
            windows = []

            for lower, upper in zip(self.rows, self.rows[1:]):
                center_y = (lower + upper) / 2.0
                half_width = self.rowSpacing * 0.26
                lower_half_width = half_width * 1.16
                upper_half_width = half_width * 0.82
                windows.append([
                    (center_y - lower_half_width, z_min + 5.0),
                    (center_y + lower_half_width, z_min + 5.0),
                    (center_y + upper_half_width, z_max - 5.5),
                    (center_y - upper_half_width, z_max - 5.5),
                ])

            return_points = {
                "side": side,
                "x": x,
                "thickness": self.sidePanelThickness,
                "outer": [
                    (y_min + 10.0, z_min),
                    (y_max - 10.0, z_min),
                    (y_max, z_min + 7.0),
                    (y_max - 5.0, z_max),
                    (y_min + 5.0, z_max),
                    (y_min, z_min + 7.0),
                ],
                "windows": windows,
            }
            panels.append(return_points)

        return panels

    def sidePanelRibs(self):
        ribs = []
        side_offset = self.holderOuterRadius + self.sidePanelThickness
        panel_inner = self.holderOuterRadius * 0.48

        for column_x, side in ((self.leftX, -1), (self.rightX, 1)):
            outer_x = column_x + side * side_offset
            inner_x = column_x - side * panel_inner

            for lower, upper in zip(self.rows, self.rows[1:]):
                mid_y = (lower + upper) / 2.0
                aperture = self.rowSpacing * 0.31
                ribs.append((outer_x, lower + aperture, inner_x, mid_y, self.sideBandRib * 0.82))
                ribs.append((inner_x, mid_y, outer_x, upper - aperture, self.sideBandRib * 0.82))

        return ribs

    def holderButtressRibs(self):
        ribs = []
        side_offset = self.holderOuterRadius + self.sidePanelThickness

        for cx, cy in self.canCenters():
            side = -1 if cx < 0 else 1
            outer_x = cx + side * side_offset
            shoulder_x = cx + side * (self.holderOuterRadius * 0.36)
            ribs.append((shoulder_x, cy, outer_x, cy, self.holderButtressRib))
            ribs.append((
                cx + side * (self.holderOuterRadius * 0.16),
                cy - self.holderOuterRadius * 0.36,
                outer_x,
                cy - self.holderOuterRadius * 0.62,
                self.holderButtressRib * 0.78,
            ))
            ribs.append((
                cx + side * (self.holderOuterRadius * 0.16),
                cy + self.holderOuterRadius * 0.36,
                outer_x,
                cy + self.holderOuterRadius * 0.62,
                self.holderButtressRib * 0.78,
            ))

        return ribs

    def handleReceiverRibs(self):
        ribs = []
        side_offset = self.holderOuterRadius + self.sideBandRib / 2.0 - 2.0
        receiver_y = 0.0
        receiver_span = self.rowSpacing * 0.54

        for column_x, side in ((self.leftX, -1), (self.rightX, 1)):
            outer_x = column_x + side * side_offset
            inner_x = outer_x - side * (self.handleReceiverRib * 1.4)
            ribs.append((outer_x, receiver_y - receiver_span / 2.0, outer_x, receiver_y + receiver_span / 2.0, self.handleReceiverRib))
            ribs.append((outer_x, receiver_y - receiver_span / 2.0, inner_x, receiver_y - receiver_span / 2.0, self.handleReceiverRib))
            ribs.append((outer_x, receiver_y + receiver_span / 2.0, inner_x, receiver_y + receiver_span / 2.0, self.handleReceiverRib))

        return ribs

    def icePackBridgeRibs(self):
        ribs = []
        rib_width = self.structuralRib * 0.65
        y_positions = [
            (self.rows[0] + self.rows[1]) / 2.0,
            (self.rows[1] + self.rows[2]) / 2.0,
        ]

        for y in y_positions:
            ribs.append((
                -self.iceThickness / 2.0 - self.iceRailWidth,
                y,
                self.leftX + self.holderInnerRadius,
                y,
                rib_width,
            ))
            ribs.append((
                self.iceThickness / 2.0 + self.iceRailWidth,
                y,
                self.rightX - self.holderInnerRadius,
                y,
                rib_width,
            ))

        return ribs

    def iceChannelShoulderRibs(self):
        ribs = []
        rail_left = -self.iceThickness / 2.0 - self.iceRailWidth / 2.0
        rail_right = self.iceThickness / 2.0 + self.iceRailWidth / 2.0

        for cy in self.rows:
            y_delta = self.holderOuterRadius * 0.46
            ribs.append((rail_left, cy - y_delta, self.leftX + self.holderOuterRadius * 0.32, cy, self.iceShoulderRib))
            ribs.append((rail_left, cy + y_delta, self.leftX + self.holderOuterRadius * 0.32, cy, self.iceShoulderRib))
            ribs.append((rail_right, cy - y_delta, self.rightX - self.holderOuterRadius * 0.32, cy, self.iceShoulderRib))
            ribs.append((rail_right, cy + y_delta, self.rightX - self.holderOuterRadius * 0.32, cy, self.iceShoulderRib))

        for y in (-self.iceHeight * 0.34, self.iceHeight * 0.34):
            ribs.append((rail_left, y, rail_right, y, self.iceShoulderRib * 0.78))

        return ribs

    def coolingWindows(self):
        windows = []
        window_height = min(46.0, self.rowSpacing - self.frameOpeningWeb)

        for x in (self.leftX, self.rightX):
            side = -1 if x < 0 else 1

            if side < 0:
                x1 = self.leftX + self.holderOuterRadius + 1.0
                x2 = -self.iceThickness / 2.0 - self.guideRail - 1.0
            else:
                x1 = self.iceThickness / 2.0 + self.guideRail + 1.0
                x2 = self.rightX - self.holderOuterRadius - 1.0

            width = max(4.0, abs(x2 - x1))
            start_x = min(x1, x2)

            for y in self.rows:
                windows.append((start_x, y - window_height / 2.0, width, window_height))

        return windows

    def centerAirOpening(self):
        width = max(6.0, self.iceThickness - 2.0 * self.guideRail)
        height = self.iceHeight - 2.0 * self.frameOpeningWeb
        return (-width / 2.0, -height / 2.0, width, height)

    def baseReliefOpenings(self):
        openings = [self.centerAirOpening()]
        x, y, width, height = self.base()
        relief_width = max(8.0, self.iceThickness + 2.0 * self.guideRail)
        relief_height = 18.0
        center_x = -relief_width / 2.0

        openings.append((center_x, y + self.frameOpeningWeb, relief_width, relief_height))
        openings.append((center_x, y + height - self.frameOpeningWeb - relief_height, relief_width, relief_height))

        return openings

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

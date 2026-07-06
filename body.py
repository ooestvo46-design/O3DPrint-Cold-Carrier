import math

import adsk.core
import adsk.fusion

from config import MM_TO_CM
from config import PARAMETERS
from geometry import Layout


SKETCH_NAME = "O3DPrint Carrier V2 Layout"
HOLDER_SKETCH_PREFIX = "O3DPrint Carrier V2 Holder "
EXTRA_SKETCH_PREFIX = "O3DPrint Carrier V2 Extra "
BODY_PREFIX = "O3DPrint Carrier V2 Body "
GENERATED_BODY_PREFIX = "O3DPrint Carrier V2"


def mm_point(x, y, z=0):
    return adsk.core.Point3D.create(x * MM_TO_CM, y * MM_TO_CM, z * MM_TO_CM)


def mm_value(value):
    return adsk.core.ValueInput.createByReal(value * MM_TO_CM)


def angle_value(degrees):
    return adsk.core.ValueInput.createByString(str(degrees) + " deg")


def collection_items(collection):
    return [collection.item(index) for index in range(collection.count)]


def remove_existing_layout_sketch(root):
    for sketch in collection_items(root.sketches):
        if sketch.name == SKETCH_NAME:
            sketch.deleteMe()


def remove_existing_bottom_frame(root):
    sketch_prefixes = [HOLDER_SKETCH_PREFIX, EXTRA_SKETCH_PREFIX]

    for body in collection_items(root.bRepBodies):
        if body.name.startswith(GENERATED_BODY_PREFIX):
            body.deleteMe()

    for sketch in collection_items(root.sketches):
        if any(sketch.name.startswith(prefix) for prefix in sketch_prefixes):
            sketch.deleteMe()


def create_layout_sketch(design):
    root = design.rootComponent
    remove_existing_layout_sketch(root)

    sketch = root.sketches.add(root.xYConstructionPlane)
    sketch.name = SKETCH_NAME

    layout = Layout()
    circles = sketch.sketchCurves.sketchCircles

    for x, y in layout.canCenters():
        circles.addByCenterRadius(mm_point(x, y), layout.canRadius * MM_TO_CM)

    x, y, width, height = layout.icePack()
    draw_rectangle(sketch, x, y, width, height)

    return sketch


def body_height():
    return PARAMETERS["bottomThickness"] + PARAMETERS["sidePanelHeight"]


def low_feature_height():
    return PARAMETERS["bottomThickness"] + PARAMETERS["guideRail"]


def extrude_profile(root, profile, height, operation, taper_angle=0.0):
    extrudes = root.features.extrudeFeatures
    extrude_input = extrudes.createInput(profile, operation)
    extent = adsk.fusion.DistanceExtentDefinition.create(mm_value(height))

    if taper_angle:
        try:
            extrude_input.setOneSideExtent(
                extent,
                adsk.fusion.ExtentDirections.PositiveExtentDirection,
                angle_value(taper_angle)
            )
        except TypeError:
            extrude_input.setOneSideExtent(
                extent,
                adsk.fusion.ExtentDirections.PositiveExtentDirection
            )
    else:
        extrude_input.setOneSideExtent(
            extent,
            adsk.fusion.ExtentDirections.PositiveExtentDirection
        )

    return extrudes.add(extrude_input)


def draw_rectangle(sketch, x, y, width, height):
    center = mm_point(x + width / 2.0, y + height / 2.0)
    corner = mm_point(x + width, y + height)
    sketch.sketchCurves.sketchLines.addCenterPointRectangle(center, corner)


def draw_polygon(sketch, points):
    lines = sketch.sketchCurves.sketchLines
    sketch_points = [mm_point(x, y) for x, y in points]

    for index, start in enumerate(sketch_points):
        end = sketch_points[(index + 1) % len(sketch_points)]
        lines.addByTwoPoints(start, end)


def arc_points(cx, cy, radius, start_degrees, end_degrees, segments):
    points = []
    for index in range(segments + 1):
        t = index / float(segments)
        angle = math.radians(start_degrees + (end_degrees - start_degrees) * t)
        points.append((cx + math.cos(angle) * radius, cy + math.sin(angle) * radius))
    return points


def primary_outline_points(layout):
    radius = layout.holderOuterRadius + PARAMETERS["holderBlendRib"] + 3.0
    points = []

    top_y = layout.rows[2]
    bottom_y = layout.rows[0]
    left_x = layout.leftX
    right_x = layout.rightX

    points.extend(arc_points(left_x, top_y, radius, 112, 70, 8))
    points.append((0.0, top_y + radius * 1.10))
    points.extend(arc_points(right_x, top_y, radius, 70, -62, 14))

    for row in (layout.rows[1], bottom_y):
        points.extend(arc_points(right_x, row, radius, 62, -62, 14))

    points.append((0.0, bottom_y - radius * 1.10))

    for row in (bottom_y, layout.rows[1], top_y):
        points.extend(arc_points(left_x, row, radius, 242, 118, 14))

    return points


def first_profile(sketch):
    for profile in collection_items(sketch.profiles):
        return profile
    raise RuntimeError("No closed profile was created.")


def create_primary_body(root, layout):
    sketch = root.sketches.add(root.xYConstructionPlane)
    sketch.name = EXTRA_SKETCH_PREFIX + "Primary Molded Body"
    draw_polygon(sketch, primary_outline_points(layout))

    feature = extrude_profile(
        root,
        first_profile(sketch),
        body_height(),
        adsk.fusion.FeatureOperations.NewBodyFeatureOperation,
        PARAMETERS["holderTaperAngle"]
    )
    feature.bodies.item(0).name = BODY_PREFIX + "Integrated Molded Body"
    return feature


def cut_can_pockets(root, layout):
    for index, (x, y) in enumerate(layout.canCenters()):
        sketch = root.sketches.add(root.xYConstructionPlane)
        sketch.name = EXTRA_SKETCH_PREFIX + "Can Pocket Cut " + str(index + 1)
        sketch.sketchCurves.sketchCircles.addByCenterRadius(
            mm_point(x, y),
            layout.holderInnerRadius * MM_TO_CM
        )
        extrude_profile(
            root,
            first_profile(sketch),
            body_height() + 2.0,
            adsk.fusion.FeatureOperations.CutFeatureOperation
        )


def cut_center_ice_channel(root, layout):
    sketch = root.sketches.add(root.xYConstructionPlane)
    sketch.name = EXTRA_SKETCH_PREFIX + "Ice Pack Channel Cut"

    x, y, width, height = layout.icePack()
    clearance = PARAMETERS["airGap"]
    draw_rectangle(
        sketch,
        x - clearance / 2.0,
        y,
        width + clearance,
        height
    )

    extrude_profile(
        root,
        first_profile(sketch),
        body_height() + 2.0,
        adsk.fusion.FeatureOperations.CutFeatureOperation
    )


def cut_cooling_openings(root, layout):
    sketch = root.sketches.add(root.xYConstructionPlane)
    sketch.name = EXTRA_SKETCH_PREFIX + "Molded Cooling Openings"

    for x, y, width, height in layout.coolingWindows():
        draw_rectangle(sketch, x, y, width, height)

    for x, y, width, height in layout.baseReliefOpenings()[1:]:
        draw_rectangle(sketch, x, y, width, height)

    for profile in collection_items(sketch.profiles):
        extrude_profile(
            root,
            profile,
            body_height() + 2.0,
            adsk.fusion.FeatureOperations.CutFeatureOperation
        )


def cut_side_wall_windows(root, layout):
    sketch = root.sketches.add(root.xYConstructionPlane)
    sketch.name = EXTRA_SKETCH_PREFIX + "Side Wall Window Cuts"

    for column_x, side in ((layout.leftX, -1), (layout.rightX, 1)):
        outside_x = column_x + side * (layout.holderOuterRadius + PARAMETERS["sideBandRib"] * 0.42)
        inside_x = column_x + side * (layout.holderOuterRadius * 0.42)
        start_x = min(outside_x, inside_x)
        width = abs(outside_x - inside_x)

        for lower, upper in zip(layout.rows, layout.rows[1:]):
            center_y = (lower + upper) / 2.0
            window_height = layout.rowSpacing * 0.44
            draw_rectangle(
                sketch,
                start_x,
                center_y - window_height / 2.0,
                width,
                window_height
            )

    for profile in collection_items(sketch.profiles):
        extrude_profile(
            root,
            profile,
            body_height() + 2.0,
            adsk.fusion.FeatureOperations.CutFeatureOperation
        )


def create_ice_pack_guides(root, layout):
    sketch = root.sketches.add(root.xYConstructionPlane)
    sketch.name = EXTRA_SKETCH_PREFIX + "Integrated Ice Pack Guides"

    for x, y, width, height in layout.iceGuideRails():
        draw_rectangle(sketch, x, y, width, height)

    for profile in collection_items(sketch.profiles):
        extrude_profile(
            root,
            profile,
            body_height(),
            adsk.fusion.FeatureOperations.JoinFeatureOperation
        )


def create_handle_receivers(root, layout):
    sketch = root.sketches.add(root.xYConstructionPlane)
    sketch.name = EXTRA_SKETCH_PREFIX + "Handle Receiver Bosses"

    boss_width = PARAMETERS["handleReceiverRib"]
    boss_height = layout.rowSpacing * 0.52

    for column_x, side in ((layout.leftX, -1), (layout.rightX, 1)):
        x = column_x + side * (layout.holderOuterRadius + PARAMETERS["sideBandRib"] * 0.18)
        draw_rectangle(
            sketch,
            x - boss_width / 2.0,
            -boss_height / 2.0,
            boss_width,
            boss_height
        )

    for profile in collection_items(sketch.profiles):
        extrude_profile(
            root,
            profile,
            body_height(),
            adsk.fusion.FeatureOperations.JoinFeatureOperation
        )


def create_cooling_supports(root, layout):
    sketch = root.sketches.add(root.xYConstructionPlane)
    sketch.name = EXTRA_SKETCH_PREFIX + "Cooling Supports"

    for x, y, width, height in layout.coolingRibs():
        draw_rectangle(sketch, x, y, width, height)

    for profile in collection_items(sketch.profiles):
        extrude_profile(
            root,
            profile,
            PARAMETERS["bottomThickness"] + 10.0,
            adsk.fusion.FeatureOperations.JoinFeatureOperation
        )


def create_drain_markers(root, layout):
    sketch = root.sketches.add(root.xYConstructionPlane)
    sketch.name = EXTRA_SKETCH_PREFIX + "Drain Hole Markers"

    circles = sketch.sketchCurves.sketchCircles
    drain_radius = 1.5
    for x, y in layout.drainPoints():
        circles.addByCenterRadius(mm_point(x, y), drain_radius * MM_TO_CM)

    return sketch


def soften_generated_edges(root):
    radius = PARAMETERS.get("softEdgeFillet", 0.0)
    if radius <= 0:
        return

    fillets = root.features.filletFeatures

    for body in collection_items(root.bRepBodies):
        if not body.name.startswith(GENERATED_BODY_PREFIX):
            continue

        edges = adsk.core.ObjectCollection.create()
        for edge in collection_items(body.edges):
            edges.add(edge)

        if edges.count == 0:
            continue

        try:
            fillet_input = fillets.createInput()
            fillet_input.addConstantRadiusEdgeSet(edges, mm_value(radius), True)
            fillets.add(fillet_input)
        except Exception:
            continue


def create_bottom_frame(design):
    root = design.rootComponent
    remove_existing_bottom_frame(root)

    layout = Layout()

    create_primary_body(root, layout)
    create_drain_markers(root, layout)
    cut_can_pockets(root, layout)
    cut_center_ice_channel(root, layout)
    cut_cooling_openings(root, layout)
    cut_side_wall_windows(root, layout)
    create_ice_pack_guides(root, layout)
    create_cooling_supports(root, layout)
    create_handle_receivers(root, layout)
    soften_generated_edges(root)

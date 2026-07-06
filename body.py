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


def raised_feature_height():
    return body_height() + 12.0


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


def create_integrated_holder_shoulders(root, layout):
    # Native, parametric holder shoulders inspired by the STL reference's
    # molded cradle logic. These are not mesh-derived and do not perform cuts.
    sketch = root.sketches.add(root.xYConstructionPlane)
    sketch.name = EXTRA_SKETCH_PREFIX + "Integrated Holder Shoulders"

    outer = layout.holderInnerRadius + PARAMETERS["wall"] + PARAMETERS["holderBlendRib"] * 0.25
    rib = PARAMETERS["moldedWebRib"]

    for x, y in layout.canCenters():
        draw_rectangle(
            sketch,
            x - outer * 0.56,
            y + outer * 0.62,
            outer * 1.12,
            rib
        )
        draw_rectangle(
            sketch,
            x - outer * 0.56,
            y - outer * 0.62 - rib,
            outer * 1.12,
            rib
        )

        side = -1 if x < 0 else 1
        draw_rectangle(
            sketch,
            x + side * outer * 0.68 - rib / 2.0,
            y - outer * 0.42,
            rib,
            outer * 0.84
        )

    for profile in collection_items(sketch.profiles):
        extrude_profile(
            root,
            profile,
            raised_feature_height(),
            adsk.fusion.FeatureOperations.JoinFeatureOperation
        )


def create_reference_side_wall_structure(root, layout):
    # The reference body uses high side walls with large windows. The cut-outs
    # remain marker sketches for now, while these raised rails make the side
    # wall logic visible without reintroducing unsafe Fusion cuts.
    sketch = root.sketches.add(root.xYConstructionPlane)
    sketch.name = EXTRA_SKETCH_PREFIX + "Reference Side Wall Structure"

    rail = PARAMETERS["sidePanelThickness"] + PARAMETERS["wall"]
    height = (layout.rows[-1] - layout.rows[0]) + layout.holderOuterRadius * 1.55

    for column_x, side in ((layout.leftX, -1), (layout.rightX, 1)):
        outside_x = column_x + side * (layout.holderOuterRadius + PARAMETERS["sideBandRib"] * 0.18)
        draw_rectangle(
            sketch,
            outside_x - rail / 2.0,
            layout.rows[0] - height / 2.0 + (layout.rows[-1] - layout.rows[0]) / 2.0,
            rail,
            height
        )

        for y in layout.rows:
            draw_rectangle(
                sketch,
                column_x + side * layout.holderOuterRadius * 0.42 - rail / 2.0,
                y - rail / 2.0,
                rail,
                rail
            )

    for profile in collection_items(sketch.profiles):
        extrude_profile(
            root,
            profile,
            raised_feature_height(),
            adsk.fusion.FeatureOperations.JoinFeatureOperation
        )


def create_can_pocket_markers(root, layout):
    # Temporarily disabled as cuts: can pocket profiles did not reliably
    # intersect Fusion's target body. Keep visible sketches until the
    # primary body shape is proven stable in Fusion.
    for index, (x, y) in enumerate(layout.canCenters()):
        sketch = root.sketches.add(root.xYConstructionPlane)
        sketch.name = EXTRA_SKETCH_PREFIX + "Can Pocket Marker " + str(index + 1)
        sketch.sketchCurves.sketchCircles.addByCenterRadius(
            mm_point(x, y),
            layout.holderInnerRadius * MM_TO_CM
        )


def create_center_ice_channel_marker(root, layout):
    # Temporarily disabled as a cut for the same target-body stability reason.
    # This sketch marks the exact ice pack channel until safe cuts are restored.
    sketch = root.sketches.add(root.xYConstructionPlane)
    sketch.name = EXTRA_SKETCH_PREFIX + "Ice Pack Channel Marker"

    x, y, width, height = layout.icePack()
    clearance = PARAMETERS["airGap"]
    draw_rectangle(
        sketch,
        x - clearance / 2.0,
        y,
        width + clearance,
        height
    )


def create_cooling_opening_markers(root, layout):
    # Temporarily disabled as cuts. These profiles remain visible markers so
    # opening placement can be checked without risking Fusion cut failures.
    sketch = root.sketches.add(root.xYConstructionPlane)
    sketch.name = EXTRA_SKETCH_PREFIX + "Molded Cooling Opening Markers"

    for x, y, width, height in layout.coolingWindows():
        draw_rectangle(sketch, x, y, width, height)

    for x, y, width, height in layout.baseReliefOpenings()[1:]:
        draw_rectangle(sketch, x, y, width, height)


def create_side_wall_window_markers(root, layout):
    # Temporarily disabled as cuts. These side window sketches show the
    # intended opening locations while preserving a runnable Fusion model.
    sketch = root.sketches.add(root.xYConstructionPlane)
    sketch.name = EXTRA_SKETCH_PREFIX + "Side Wall Window Markers"

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


def create_ice_pack_guides(root, layout):
    sketch = root.sketches.add(root.xYConstructionPlane)
    sketch.name = EXTRA_SKETCH_PREFIX + "Integrated Ice Pack Guides"

    for x, y, width, height in layout.iceGuideRails():
        draw_rectangle(sketch, x, y, width, height)

    for profile in collection_items(sketch.profiles):
        extrude_profile(
            root,
            profile,
            raised_feature_height(),
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
            raised_feature_height(),
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
    # Temporarily disabled as cuts. Drain positions are visible sketch markers
    # until real cuts are reintroduced with target-body checks.
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
    create_can_pocket_markers(root, layout)
    create_center_ice_channel_marker(root, layout)
    create_cooling_opening_markers(root, layout)
    create_side_wall_window_markers(root, layout)
    create_integrated_holder_shoulders(root, layout)
    create_reference_side_wall_structure(root, layout)
    create_ice_pack_guides(root, layout)
    create_cooling_supports(root, layout)
    create_handle_receivers(root, layout)
    soften_generated_edges(root)

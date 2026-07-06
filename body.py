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


def generated_bodies(root):
    return [
        body for body in collection_items(root.bRepBodies)
        if body.name.startswith(GENERATED_BODY_PREFIX)
    ]


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


def ring_profile(sketch):
    for index in range(sketch.profiles.count):
        profile = sketch.profiles.item(index)
        if profile.profileLoops.count == 2:
            return profile
    raise RuntimeError("No ring profile was created.")


def extrude_profile(root, profile, height, operation, taper_angle=0.0, direction=None):
    extrudes = root.features.extrudeFeatures
    extrude_input = extrudes.createInput(profile, operation)
    extent = adsk.fusion.DistanceExtentDefinition.create(mm_value(height))
    extent_direction = direction or adsk.fusion.ExtentDirections.PositiveExtentDirection

    if taper_angle:
        try:
            extrude_input.setOneSideExtent(
                extent,
                extent_direction,
                angle_value(taper_angle)
            )
        except TypeError:
            extrude_input.setOneSideExtent(
                extent,
                extent_direction
            )
    else:
        extrude_input.setOneSideExtent(
            extent,
            extent_direction
        )

    return extrudes.add(extrude_input)


def draw_rectangle(sketch, x, y, width, height):
    center = mm_point(x + width / 2.0, y + height / 2.0)
    corner = mm_point(x + width, y + height)
    sketch.sketchCurves.sketchLines.addCenterPointRectangle(center, corner)


def draw_capsule(sketch, x1, y1, x2, y2, width):
    radius = width / 2.0
    circles = sketch.sketchCurves.sketchCircles

    if abs(x1 - x2) >= abs(y1 - y2):
        left = min(x1, x2)
        right = max(x1, x2)
        y = (y1 + y2) / 2.0
        draw_rectangle(sketch, left, y - radius, right - left, width)
        circles.addByCenterRadius(mm_point(left, y), radius * MM_TO_CM)
        circles.addByCenterRadius(mm_point(right, y), radius * MM_TO_CM)
    else:
        x = (x1 + x2) / 2.0
        bottom = min(y1, y2)
        top = max(y1, y2)
        draw_rectangle(sketch, x - radius, bottom, width, top - bottom)
        circles.addByCenterRadius(mm_point(x, bottom), radius * MM_TO_CM)
        circles.addByCenterRadius(mm_point(x, top), radius * MM_TO_CM)


def create_can_holder(root, layout, index):
    sketch = root.sketches.add(root.xYConstructionPlane)
    sketch.name = HOLDER_SKETCH_PREFIX + str(index + 1)

    x, y = layout.canCenters()[index]
    circles = sketch.sketchCurves.sketchCircles
    center = mm_point(x, y)
    circles.addByCenterRadius(center, layout.holderOuterRadius * MM_TO_CM)
    circles.addByCenterRadius(center, layout.holderInnerRadius * MM_TO_CM)

    feature = extrude_profile(
        root,
        ring_profile(sketch),
        PARAMETERS["bottomThickness"] + PARAMETERS["guideRailHeight"],
        adsk.fusion.FeatureOperations.NewBodyFeatureOperation,
        PARAMETERS["holderTaperAngle"]
    )
    feature.bodies.item(0).name = BODY_PREFIX + "Can Holder " + str(index + 1)
    return feature


def create_holder_shoulders(root, layout):
    sketch = root.sketches.add(root.xYConstructionPlane)
    sketch.name = EXTRA_SKETCH_PREFIX + "Integrated Holder Shoulders"

    circles = sketch.sketchCurves.sketchCircles
    shoulder_radius = layout.holderOuterRadius + PARAMETERS["holderBlendRib"]

    for x, y in layout.canCenters():
        center = mm_point(x, y)
        circles.addByCenterRadius(center, shoulder_radius * MM_TO_CM)
        circles.addByCenterRadius(center, layout.holderInnerRadius * MM_TO_CM)

    features = []
    for profile in collection_items(sketch.profiles):
        if profile.profileLoops.count == 2:
            features.append(
                extrude_profile(
                    root,
                    profile,
                    PARAMETERS["bottomThickness"] + 16.0,
                    adsk.fusion.FeatureOperations.JoinFeatureOperation,
                    PARAMETERS["holderTaperAngle"]
                )
            )

    return features


def create_rectangular_join_feature(root, name, rectangles, height):
    sketch = root.sketches.add(root.xYConstructionPlane)
    sketch.name = EXTRA_SKETCH_PREFIX + name

    for rect in rectangles:
        draw_rectangle(sketch, *rect)

    features = []
    for profile in collection_items(sketch.profiles):
        features.append(
            extrude_profile(
                root,
                profile,
                height,
                adsk.fusion.FeatureOperations.JoinFeatureOperation
            )
        )
    return features


def create_capsule_join_feature(root, name, ribs, height):
    features = []

    for index, rib in enumerate(ribs):
        sketch = root.sketches.add(root.xYConstructionPlane)
        sketch.name = EXTRA_SKETCH_PREFIX + name + " " + str(index + 1)
        draw_capsule(sketch, *rib)

        for profile in collection_items(sketch.profiles):
            features.append(
                extrude_profile(
                    root,
                    profile,
                    height,
                    adsk.fusion.FeatureOperations.JoinFeatureOperation
                )
            )

    return features


def create_ice_pack_guides(root, layout):
    ribs = list(layout.iceGuideRibs())
    ribs.append(layout.centerStopRib())
    ribs.extend(layout.iceChannelBlendRibs())

    return create_capsule_join_feature(
        root,
        "Ice Pack Guides",
        ribs,
        PARAMETERS["bottomThickness"] + PARAMETERS["guideRailHeight"]
    )


def create_cooling_ribs(root, layout):
    return create_rectangular_join_feature(
        root,
        "Cooling Ribs",
        layout.coolingRibs(),
        PARAMETERS["bottomThickness"] + 18.0
    )


def side_truss_ribs(layout):
    ribs = []
    side_width = max(PARAMETERS["wall"], PARAMETERS["sideBandRib"] * 0.72)
    diagonal_width = max(PARAMETERS["wall"], PARAMETERS["sideBandRib"] * 0.62)

    for column_x, side in ((layout.leftX, -1), (layout.rightX, 1)):
        outer_x = column_x + side * (layout.holderOuterRadius + side_width * 0.42)
        inner_x = column_x + side * (layout.holderOuterRadius * 0.28)
        end_y = layout.holderOuterRadius * 0.72

        ribs.append((
            outer_x,
            layout.rows[0] - end_y,
            outer_x,
            layout.rows[2] + end_y,
            side_width,
        ))

        for lower, upper in zip(layout.rows, layout.rows[1:]):
            middle_y = (lower + upper) / 2.0
            opening = layout.rowSpacing * 0.30
            ribs.append((outer_x, lower + opening, inner_x, middle_y, diagonal_width))
            ribs.append((inner_x, middle_y, outer_x, upper - opening, diagonal_width))

        for y in layout.rows:
            ribs.append((
                outer_x,
                y - layout.holderOuterRadius * 0.34,
                column_x + side * (layout.holderOuterRadius + PARAMETERS["holderBlendRib"] * 0.25),
                y,
                diagonal_width,
            ))
            ribs.append((
                outer_x,
                y + layout.holderOuterRadius * 0.34,
                column_x + side * (layout.holderOuterRadius + PARAMETERS["holderBlendRib"] * 0.25),
                y,
                diagonal_width,
            ))

    return ribs


def create_side_wall_panels(root, layout):
    ribs = []
    ribs.extend(layout.sidePanelRibs())
    ribs.extend(layout.handleReceiverRibs())
    ribs.extend(layout.holderButtressRibs())
    ribs.extend(side_truss_ribs(layout))

    return create_capsule_join_feature(
        root,
        "Integrated Side Truss",
        ribs,
        PARAMETERS["bottomThickness"] + PARAMETERS["sidePanelHeight"]
    )


def create_ice_channel_shoulders(root, layout):
    return create_capsule_join_feature(
        root,
        "Ice Channel Shoulders",
        layout.iceChannelShoulderRibs(),
        PARAMETERS["bottomThickness"] + 22.0
    )


def create_structural_frame_ribs(root, layout):
    ribs = []
    ribs.extend(layout.structuralRibs())
    ribs.extend(layout.moldedWebRibs())
    ribs.extend(layout.holderBlendRibs())
    ribs.extend(layout.perimeterRibs())
    ribs.extend(layout.icePackBridgeRibs())

    return create_capsule_join_feature(
        root,
        "Structural Rib",
        ribs,
        PARAMETERS["bottomThickness"] + PARAMETERS["guideRail"],
    )


def create_raised_can_pads(root, layout):
    sketch = root.sketches.add(root.xYConstructionPlane)
    sketch.name = EXTRA_SKETCH_PREFIX + "Raised Can Pads"

    circles = sketch.sketchCurves.sketchCircles
    for x, y, radius in layout.raisedCanPads():
        circles.addByCenterRadius(mm_point(x, y), radius * MM_TO_CM)

    for profile in collection_items(sketch.profiles):
        extrude_profile(
            root,
            profile,
            PARAMETERS["bottomThickness"] + 1.2,
            adsk.fusion.FeatureOperations.JoinFeatureOperation
        )


def soften_generated_edges(root):
    radius = PARAMETERS.get("softEdgeFillet", 0.0)
    if radius <= 0:
        return

    fillets = root.features.filletFeatures

    for body in generated_bodies(root):
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

    for index in range(len(layout.canCenters())):
        create_can_holder(root, layout, index)

    create_holder_shoulders(root, layout)
    create_structural_frame_ribs(root, layout)
    create_ice_channel_shoulders(root, layout)
    create_ice_pack_guides(root, layout)
    create_side_wall_panels(root, layout)
    create_cooling_ribs(root, layout)
    create_raised_can_pads(root, layout)
    soften_generated_edges(root)

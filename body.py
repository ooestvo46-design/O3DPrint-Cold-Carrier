import adsk.core
import adsk.fusion

from config import MM_TO_CM
from config import PARAMETERS
from geometry import Layout


SKETCH_NAME = "O3DPrint Carrier V2 Layout"
BASE_SKETCH_NAME = "O3DPrint Carrier V2 Base"
HOLDER_SKETCH_PREFIX = "O3DPrint Carrier V2 Holder "
EXTRA_SKETCH_PREFIX = "O3DPrint Carrier V2 Extra "
BODY_NAME = "O3DPrint Carrier V2 Bottom Frame"
GENERATED_BODY_PREFIX = "O3DPrint Carrier V2"


def mm_point(x, y, z=0):
    return adsk.core.Point3D.create(x * MM_TO_CM, y * MM_TO_CM, z * MM_TO_CM)


def mm_value(value):
    return adsk.core.ValueInput.createByReal(value * MM_TO_CM)


def collection_items(collection):
    return [collection.item(index) for index in range(collection.count)]


def remove_existing_layout_sketch(root):
    for sketch in collection_items(root.sketches):
        if sketch.name == SKETCH_NAME:
            sketch.deleteMe()


def remove_existing_bottom_frame(root):
    sketch_names = [BASE_SKETCH_NAME]
    sketch_prefixes = [EXTRA_SKETCH_PREFIX]
    sketch_names.extend(
        HOLDER_SKETCH_PREFIX + str(index + 1)
        for index in range(PARAMETERS["canCount"])
    )

    for body in collection_items(root.bRepBodies):
        if body.name.startswith(GENERATED_BODY_PREFIX):
            body.deleteMe()

    for sketch in collection_items(root.sketches):
        if sketch.name in sketch_names:
            sketch.deleteMe()
        elif any(sketch.name.startswith(prefix) for prefix in sketch_prefixes):
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


def first_profile(sketch):
    if sketch.profiles.count < 1:
        raise RuntimeError("No sketch profile was created.")
    return sketch.profiles.item(0)


def largest_profile(sketch):
    return first_profile(sketch)


def ring_profile(sketch):
    for index in range(sketch.profiles.count):
        profile = sketch.profiles.item(index)
        if profile.profileLoops.count == 2:
            return profile
    raise RuntimeError("No ring profile was created.")


def extrude_profile(root, profile, height, operation):
    extrudes = root.features.extrudeFeatures
    extrude_input = extrudes.createInput(profile, operation)
    extent = adsk.fusion.DistanceExtentDefinition.create(mm_value(height))
    extrude_input.setOneSideExtent(
        extent,
        adsk.fusion.ExtentDirections.PositiveExtentDirection
    )
    return extrudes.add(extrude_input)


def draw_closed_polygon(sketch, points):
    lines = sketch.sketchCurves.sketchLines
    for index in range(len(points)):
        x1, y1 = points[index]
        x2, y2 = points[(index + 1) % len(points)]
        lines.addByTwoPoints(mm_point(x1, y1), mm_point(x2, y2))


def draw_rectangle(sketch, x, y, width, height):
    center = mm_point(x + width / 2.0, y + height / 2.0)
    corner = mm_point(x + width, y + height)
    sketch.sketchCurves.sketchLines.addCenterPointRectangle(center, corner)


def create_base(root, layout):
    sketch = root.sketches.add(root.xYConstructionPlane)
    sketch.name = BASE_SKETCH_NAME

    draw_closed_polygon(sketch, layout.basePolygon())

    feature = extrude_profile(
        root,
        largest_profile(sketch),
        PARAMETERS["bottomThickness"],
        adsk.fusion.FeatureOperations.NewBodyFeatureOperation
    )

    feature.bodies.item(0).name = BODY_NAME
    return feature


def create_can_holder(root, layout, index, center):
    sketch = root.sketches.add(root.xYConstructionPlane)
    sketch.name = HOLDER_SKETCH_PREFIX + str(index + 1)

    circles = sketch.sketchCurves.sketchCircles
    circle_center = mm_point(center[0], center[1])
    circles.addByCenterRadius(circle_center, layout.holderOuterRadius * MM_TO_CM)
    circles.addByCenterRadius(circle_center, layout.holderInnerRadius * MM_TO_CM)

    return extrude_profile(
        root,
        ring_profile(sketch),
        PARAMETERS["bottomThickness"] + PARAMETERS["guideRailHeight"],
        adsk.fusion.FeatureOperations.JoinFeatureOperation
    )


def create_rectangular_join_feature(root, name, rectangles, height):
    sketch = root.sketches.add(root.xYConstructionPlane)
    sketch.name = EXTRA_SKETCH_PREFIX + name

    for rect in rectangles:
        draw_rectangle(sketch, *rect)

    features = []
    profiles = collection_items(sketch.profiles)

    for profile in profiles:
        features.append(
            extrude_profile(
                root,
                profile,
                height,
                adsk.fusion.FeatureOperations.JoinFeatureOperation
            )
        )
    return features


def create_rectangular_cut_feature(root, name, rectangles, height):
    sketch = root.sketches.add(root.xYConstructionPlane)
    sketch.name = EXTRA_SKETCH_PREFIX + name

    for rect in rectangles:
        draw_rectangle(sketch, *rect)

    features = []
    profiles = collection_items(sketch.profiles)

    for profile in profiles:
        features.append(
            extrude_profile(
                root,
                profile,
                height,
                adsk.fusion.FeatureOperations.CutFeatureOperation
            )
        )
    return features


def create_ice_pack_guides(root, layout):
    rects = list(layout.iceGuideRails())
    rects.append(layout.centerStop())
    return create_rectangular_join_feature(
        root,
        "Ice Pack Guides",
        rects,
        PARAMETERS["bottomThickness"] + PARAMETERS["guideRailHeight"]
    )


def create_cooling_ribs(root, layout):
    return create_rectangular_join_feature(
        root,
        "Cooling Ribs",
        layout.coolingRibs(),
        PARAMETERS["bottomThickness"] + 18.0
    )


def create_handle_guide_rails(root, layout):
    return create_rectangular_join_feature(
        root,
        "Handle Guide Rails",
        layout.handleGuideRails(),
        PARAMETERS["bottomThickness"] + PARAMETERS["guideRailHeight"]
    )


def create_cooling_windows(root, layout):
    cut_height = PARAMETERS["bottomThickness"] + PARAMETERS["guideRailHeight"] + 5.0
    return create_rectangular_cut_feature(
        root,
        "Cooling Windows",
        layout.coolingWindows(),
        cut_height
    )


def create_base_relief_openings(root, layout):
    cut_height = PARAMETERS["bottomThickness"] + PARAMETERS["guideRailHeight"] + 5.0
    return create_rectangular_cut_feature(
        root,
        "Base Relief Openings",
        layout.baseReliefOpenings(),
        cut_height
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


def create_drain_holes(root, layout):
    sketch = root.sketches.add(root.xYConstructionPlane)
    sketch.name = EXTRA_SKETCH_PREFIX + "Drain Holes"

    circles = sketch.sketchCurves.sketchCircles
    for x, y in layout.drainPoints():
        circles.addByCenterRadius(mm_point(x, y), 2.5 * MM_TO_CM)

    for profile in collection_items(sketch.profiles):
        extrude_profile(
            root,
            profile,
            PARAMETERS["bottomThickness"] + 2.0,
            adsk.fusion.FeatureOperations.CutFeatureOperation
        )


def create_bottom_frame(design):
    root = design.rootComponent
    remove_existing_bottom_frame(root)

    layout = Layout()
    create_base(root, layout)

    for index, center in enumerate(layout.canCenters()):
        create_can_holder(root, layout, index, center)

    create_ice_pack_guides(root, layout)
    create_cooling_ribs(root, layout)
    create_handle_guide_rails(root, layout)
    create_cooling_windows(root, layout)
    create_base_relief_openings(root, layout)
    create_raised_can_pads(root, layout)
    create_drain_holes(root, layout)

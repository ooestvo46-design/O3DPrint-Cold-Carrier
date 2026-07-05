import adsk.core
import adsk.fusion

from config import MM_TO_CM
from config import PARAMETERS
from geometry import Layout


SKETCH_NAME = "O3DPrint Carrier V2 Layout"
BASE_SKETCH_NAME = "O3DPrint Carrier V2 Base"
HOLDER_SKETCH_PREFIX = "O3DPrint Carrier V2 Holder "
BODY_NAME = "O3DPrint Carrier V2 Bottom Frame"


def mm_point(x, y, z=0):
    return adsk.core.Point3D.create(x * MM_TO_CM, y * MM_TO_CM, z * MM_TO_CM)


def mm_value(value):
    return adsk.core.ValueInput.createByReal(value * MM_TO_CM)


def remove_existing_layout_sketch(root):
    matching_sketches = [sketch for sketch in root.sketches if sketch.name == SKETCH_NAME]

    for sketch in matching_sketches:
        sketch.deleteMe()


def remove_existing_bottom_frame(root):
    sketch_names = [BASE_SKETCH_NAME]
    sketch_names.extend(
        HOLDER_SKETCH_PREFIX + str(index + 1)
        for index in range(PARAMETERS["canCount"])
    )

    matching_bodies = [
        body for body in root.bRepBodies
        if body.name == BODY_NAME
    ]

    for body in matching_bodies:
        body.deleteMe()

    matching_sketches = [
        sketch for sketch in root.sketches
        if sketch.name in sketch_names
    ]

    for sketch in matching_sketches:
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
    center = mm_point(x + width / 2, y + height / 2)
    corner = mm_point(x + width, y + height)
    sketch.sketchCurves.sketchLines.addCenterPointRectangle(center, corner)

    return sketch


def first_profile(sketch):
    if sketch.profiles.count < 1:
        raise RuntimeError("No sketch profile was created.")

    return sketch.profiles.item(0)


def ring_profile(sketch):
    for profile in sketch.profiles:
        if profile.profileLoops.count == 2:
            return profile

    raise RuntimeError("No ring profile was created.")


def extrude_profile(root, profile, height, operation):
    extrudes = root.features.extrudeFeatures
    extrude_input = extrudes.createInput(profile, operation)
    extrude_input.setDistanceExtent(False, mm_value(height))
    return extrudes.add(extrude_input)


def create_base(root, layout):
    sketch = root.sketches.add(root.xYConstructionPlane)
    sketch.name = BASE_SKETCH_NAME

    x, y, width, height = layout.base()
    center = mm_point(x + width / 2, y + height / 2)
    corner = mm_point(x + width, y + height)
    sketch.sketchCurves.sketchLines.addCenterPointRectangle(center, corner)

    feature = extrude_profile(
        root,
        first_profile(sketch),
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
        PARAMETERS["bottomThickness"] + PARAMETERS["guideRail"],
        adsk.fusion.FeatureOperations.JoinFeatureOperation
    )


def create_bottom_frame(design):
    root = design.rootComponent
    remove_existing_bottom_frame(root)

    layout = Layout()
    create_base(root, layout)

    for index, center in enumerate(layout.canCenters()):
        create_can_holder(root, layout, index, center)

import adsk.core
import adsk.fusion


def create_components(design):

    root = design.rootComponent

    occs = root.occurrences

    components = {}

    names = [
        "Body",
        "Handle",
        "IcePack"
    ]

    for name in names:

        existing = None

        for occ in occs:

            if occ.component.name == name:
                existing = occ.component
                break

        if existing:
            components[name] = existing
            continue

        transform = adsk.core.Matrix3D.create()

        occ = occs.addNewComponent(transform)

        occ.component.name = name

        components[name] = occ.component

    return components

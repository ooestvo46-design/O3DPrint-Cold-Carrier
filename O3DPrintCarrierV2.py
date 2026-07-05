import adsk.core
import adsk.fusion
import os
import sys
import traceback

script_dir = os.path.dirname(os.path.realpath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

from body import create_bottom_frame
from body import create_layout_sketch

app = adsk.core.Application.get()
ui = app.userInterface


def get_active_design():
    design = adsk.fusion.Design.cast(app.activeProduct)

    if design:
        return design

    document = app.activeDocument

    if not document:
        return None

    return adsk.fusion.Design.cast(
        document.products.itemByProductType("DesignProductType")
    )


def run(context):

    try:

        design = get_active_design()

        if not design:
            ui.messageBox("Open a Fusion Design or Part Design document first.")
            return

        create_layout_sketch(design)
        create_bottom_frame(design)

    except Exception:
        ui.messageBox(traceback.format_exc())

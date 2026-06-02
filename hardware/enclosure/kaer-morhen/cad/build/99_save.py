import adsk.core, adsk.fusion, traceback
def run(_context):
    app = adsk.core.Application.get()
    try:
        doc = app.activeDocument
        ok = doc.save("kaer-morhen massing: base + towers + 65deg screen + shelf")
        design = adsk.fusion.Design.cast(app.activeProduct)
        print("saved=%s doc=%s bodies=%d params=%d" % (
            ok, doc.name, design.rootComponent.bRepBodies.count, design.userParameters.count))
    except:
        print("ERROR: " + traceback.format_exc())

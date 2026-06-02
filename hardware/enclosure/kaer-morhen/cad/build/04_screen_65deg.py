import adsk.core, adsk.fusion, traceback
def run(_context):
    app = adsk.core.Application.get()
    try:
        design = adsk.fusion.Design.cast(app.activeProduct)
        root = design.rootComponent
        P = adsk.core.Point3D.create
        VI = adsk.core.ValueInput.createByString
        HOR = adsk.fusion.DimensionOrientations.HorizontalDimensionOrientation
        VER = adsk.fusion.DimensionOrientations.VerticalDimensionOrientation
        # angled plane: screen_tilt from XY, hinged on the X axis (front-bottom, y=0 z=0)
        pin = root.constructionPlanes.createInput()
        pin.setByAngle(root.xConstructionAxis, VI("screen_tilt"), root.xYConstructionPlane)
        plane = root.constructionPlanes.add(pin); plane.name = "screen_plane"
        sk = root.sketches.add(plane); sk.name = "screen_sk"
        rect = sk.sketchCurves.sketchLines.addTwoPointRectangle(P(-9.7,0,0), P(9.7,11,0))
        ls = [rect.item(i) for i in range(rect.count)]
        bottom = min(ls, key=lambda l:(l.startSketchPoint.geometry.y+l.endSketchPoint.geometry.y))
        side = None
        for l in ls:
            a=l.startSketchPoint.geometry; b=l.endSketchPoint.geometry
            if abs(a.x-b.x)<1e-4 and abs(a.x)>1e-4: side=l
        sk.geometricConstraints.addMidPoint(sk.originPoint, bottom)
        D = sk.sketchDimensions
        dW=D.addDistanceDimension(bottom.startSketchPoint,bottom.endSketchPoint,HOR,P(0,-2,0)); dW.parameter.expression="screen_module_w"
        dH=D.addDistanceDimension(side.startSketchPoint,side.endSketchPoint,VER,P(11,5,0)); dH.parameter.expression="screen_module_h"
        prof = sk.profiles.item(0)
        ext = root.features.extrudeFeatures.addSimple(prof, VI("screen_module_t"),
                adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        ext.bodies.item(0).name = "screen"
        app.activeViewport.fit()
        b = ext.bodies.item(0).boundingBox
        print("OK screen. bbox(cm) min=(%.1f,%.1f,%.1f) max=(%.1f,%.1f,%.1f)  bodies=%d" % (
            b.minPoint.x,b.minPoint.y,b.minPoint.z,b.maxPoint.x,b.maxPoint.y,b.maxPoint.z, root.bRepBodies.count))
    except:
        print("ERROR: " + traceback.format_exc())

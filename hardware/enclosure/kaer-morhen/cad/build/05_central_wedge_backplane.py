import adsk.core, adsk.fusion, traceback, math
def run(_context):
    app = adsk.core.Application.get()
    try:
        design = adsk.fusion.Design.cast(app.activeProduct)
        root = design.rootComponent
        P = adsk.core.Point3D.create
        VI = adsk.core.ValueInput.createByString
        HOR = adsk.fusion.DimensionOrientations.HorizontalDimensionOrientation
        VER = adsk.fusion.DimensionOrientations.VerticalDimensionOrientation
        ALN = adsk.fusion.DimensionOrientations.AlignedDimensionOrientation

        for b in list(root.bRepBodies):
            if b.name == "central_body":
                b.deleteMe()

        # YZ-plane mapping observed: world_y = sketch_Y, world_z = -sketch_X.
        # screen-top B in world (mm): y=110*cos65, z=110*sin65
        by = 11.0*math.cos(math.radians(65)); bz = 11.0*math.sin(math.radians(65))  # cm
        sk = root.sketches.add(root.yZConstructionPlane); sk.name = "central_body_sk"
        L = sk.sketchCurves.sketchLines
        A=P(0,0,0); E=P(0,14,0); Dp=P(-4.5,14,0); B=P(-bz,by,0)
        l_bottom = L.addByTwoPoints(A, E)                              # A->E depth (+Y)
        l_back   = L.addByTwoPoints(l_bottom.endSketchPoint, Dp)       # E->D height (+Z)
        l_front  = L.addByTwoPoints(l_bottom.startSketchPoint, B)      # A->B screen
        l_plane  = L.addByTwoPoints(l_front.endSketchPoint, l_back.endSketchPoint)  # B->D backplane

        gc = sk.geometricConstraints
        gc.addCoincident(l_bottom.startSketchPoint, sk.originPoint)
        gc.addVertical(l_bottom)     # sketch-vertical == world +Y depth
        gc.addHorizontal(l_back)     # sketch-horizontal == world +Z height
        Dm = sk.sketchDimensions
        d1=Dm.addDistanceDimension(l_bottom.startSketchPoint, l_bottom.endSketchPoint, VER, P(2,7,0)); d1.parameter.expression="base_depth"
        d2=Dm.addDistanceDimension(l_back.startSketchPoint, l_back.endSketchPoint, HOR, P(-2,15,0)); d2.parameter.expression="base_height"
        d3=Dm.addDistanceDimension(l_front.startSketchPoint, l_front.endSketchPoint, ALN, P(-6,2,0)); d3.parameter.expression="screen_module_h"
        d4=Dm.addAngularDimension(l_bottom, l_front, P(-1,1,0)); d4.parameter.expression="screen_tilt"

        prof = sk.profiles.item(0)
        exts = root.features.extrudeFeatures
        ein = exts.createInput(prof, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        ein.setSymmetricExtent(VI("base_width"), True)
        ext = exts.add(ein)
        ext.bodies.item(0).name = "central_body"

        app.activeViewport.fit()
        b = root.bRepBodies.itemByName("central_body").boundingBox
        print("OK wedge. bbox(cm) min=(%.1f,%.1f,%.1f) max=(%.1f,%.1f,%.1f) constrained=%s" % (
            b.minPoint.x,b.minPoint.y,b.minPoint.z,b.maxPoint.x,b.maxPoint.y,b.maxPoint.z, sk.isFullyConstrained))
    except:
        print("ERROR: " + traceback.format_exc())

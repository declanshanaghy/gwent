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
        NEW = adsk.fusion.FeatureOperations.NewBodyFeatureOperation

        def lines_of(rect):
            ls=[rect.item(i) for i in range(rect.count)]
            return ls
        def horiz_at_miny(ls):
            return min(ls, key=lambda l:(l.startSketchPoint.geometry.y+l.endSketchPoint.geometry.y))
        def vert_with_x(ls, xc):
            best=None
            for l in ls:
                a=l.startSketchPoint.geometry; b=l.endSketchPoint.geometry
                if abs(a.x-b.x)<1e-4 and abs(((a.x+b.x)/2)-xc)<0.6: best=l
            return best

        def make_box(name, p0, p1, dims):
            sk=root.sketches.add(root.xYConstructionPlane); sk.name=name+"_sk"
            rect=sk.sketchCurves.sketchLines.addTwoPointRectangle(p0,p1)
            ls=lines_of(rect)
            front=horiz_at_miny(ls)
            xproj=sk.project(root.xConstructionAxis); xline=xproj.item(0)
            sk.geometricConstraints.addCollinear(front, xline)  # front edge on X axis (y=0)
            dims(sk, ls, front)
            prof=sk.profiles.item(0)
            ext=root.features.extrudeFeatures.addSimple(prof, VI(name_h[name]), NEW)
            b=ext.bodies.item(0); b.name=name
            return sk,b

        name_h={"tower_right":"tower_height","tower_left":"tower_height","front_shelf":"shelf_height"}

        # RIGHT TOWER: inner edge at base_width/2, width tower_width, depth tower_depth
        def dims_R(sk, ls, front):
            D=sk.sketchDimensions
            inner=vert_with_x(ls, 10.5)
            d1=D.addDistanceDimension(sk.originPoint, inner.startSketchPoint, HOR, P(5,-2,0)); d1.parameter.expression="base_width/2"
            d2=D.addDistanceDimension(front.startSketchPoint, front.endSketchPoint, HOR, P(13,-2,0)); d2.parameter.expression="tower_width"
            d3=D.addDistanceDimension(inner.startSketchPoint, inner.endSketchPoint, VER, P(9,3,0)); d3.parameter.expression="tower_depth"
        make_box("tower_right", P(10.5,0,0), P(16.2,6,0), dims_R)

        # LEFT TOWER (mirror)
        def dims_L(sk, ls, front):
            D=sk.sketchDimensions
            inner=vert_with_x(ls, -10.5)
            d1=D.addDistanceDimension(sk.originPoint, inner.startSketchPoint, HOR, P(-5,-2,0)); d1.parameter.expression="base_width/2"
            d2=D.addDistanceDimension(front.startSketchPoint, front.endSketchPoint, HOR, P(-13,-2,0)); d2.parameter.expression="tower_width"
            d3=D.addDistanceDimension(inner.startSketchPoint, inner.endSketchPoint, VER, P(-9,3,0)); d3.parameter.expression="tower_depth"
        make_box("tower_left", P(-16.2,0,0), P(-10.5,6,0), dims_L)

        # FRONT SHELF: protrudes forward (y negative), centered, width shelf_width depth shelf_depth
        def dims_S(sk, ls, back):
            D=sk.sketchDimensions
            sk.geometricConstraints.addMidPoint(sk.originPoint, back)  # center on X, back edge at y=0
            side=vert_with_x(ls, 4) or vert_with_x(ls, -4)
            dW=D.addDistanceDimension(back.startSketchPoint, back.endSketchPoint, HOR, P(0,2,0)); dW.parameter.expression="shelf_width"
            dD=D.addDistanceDimension(side.startSketchPoint, side.endSketchPoint, VER, P(5,-4,0)); dD.parameter.expression="shelf_depth"
        # shelf drawn in -y (front). back edge at y=0.
        skS=root.sketches.add(root.xYConstructionPlane); skS.name="front_shelf_sk"
        rectS=skS.sketchCurves.sketchLines.addTwoPointRectangle(P(-4,-9,0),P(4,0,0))
        lsS=lines_of(rectS)
        backS=max(lsS, key=lambda l:(l.startSketchPoint.geometry.y+l.endSketchPoint.geometry.y))  # y=0 edge
        dims_S(skS, lsS, backS)
        profS=skS.profiles.item(0)
        extS=root.features.extrudeFeatures.addSimple(profS, VI("shelf_height"), NEW)
        extS.bodies.item(0).name="front_shelf"

        app.activeViewport.fit()
        names=[b.name for b in root.bRepBodies]
        print("OK bodies=%d : %s" % (root.bRepBodies.count, ", ".join(names)))
    except:
        print("ERROR: "+traceback.format_exc())

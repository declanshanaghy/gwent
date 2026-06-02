import adsk.core, adsk.fusion, traceback
def run(_context):
    app = adsk.core.Application.get()
    try:
        design = adsk.fusion.Design.cast(app.activeProduct)
        design.designType = adsk.fusion.DesignTypes.ParametricDesignType
        up = design.userParameters
        SPEC = [
            ("nozzle_diameter","0.8 mm","mm"),("num_walls","2",""),
            ("wall_thickness","nozzle_diameter * num_walls","mm"),
            ("layer_height","0.4 mm","mm"),("fit_clearance","0.4 mm","mm"),
            ("hole_compensation","0.4 mm","mm"),("min_feature","nozzle_diameter","mm"),
            ("max_width","325 mm","mm"),("max_depth","250 mm","mm"),("max_height","250 mm","mm"),
            ("print_plate","256 mm","mm"),("screen_tilt","65 deg","deg"),
            ("screen_module_w","194 mm","mm"),("screen_module_h","110 mm","mm"),
            ("screen_module_t","20 mm","mm"),("screen_visible_w","155 mm","mm"),
            ("screen_visible_h","86 mm","mm"),("brick_length","112 mm","mm"),
            ("brick_width","76 mm","mm"),("brick_height","35 mm","mm"),
            ("pi_length","85 mm","mm"),("pi_width","56 mm","mm"),
            ("hat_length","65 mm","mm"),("hat_width","56.5 mm","mm"),
            ("score_display_w","50 mm","mm"),("score_display_h","25 mm","mm"),
            ("display_bezel","5 mm","mm"),
            ("score_aperture_w","score_display_w + 2 * display_bezel","mm"),
            ("score_aperture_h","score_display_h + 2 * display_bezel","mm"),
            ("gems_display_w","50 mm","mm"),("gems_display_h","25 mm","mm"),
            ("speaker_diameter","50 mm","mm"),("speaker_depth","25 mm","mm"),
            ("amp_length","55 mm","mm"),("amp_width","32 mm","mm"),
            ("isolator_length","120 mm","mm"),("isolator_width","20 mm","mm"),
            ("isolator_height","20 mm","mm"),("card_width","63 mm","mm"),
            ("card_height","88 mm","mm"),("base_width","210 mm","mm"),
            ("base_depth","140 mm","mm"),("base_height","45 mm","mm"),
            ("tower_width","57 mm","mm"),("tower_depth","60 mm","mm"),
            ("tower_height","130 mm","mm"),("tower_taper","12 mm","mm"),
            ("tower_toe_in","5 deg","deg"),("tower_plug_depth","15 mm","mm"),
            ("gems_crest_width","70 mm","mm"),("gems_crest_height","40 mm","mm"),
            ("shelf_width","80 mm","mm"),("shelf_depth","90 mm","mm"),
            ("shelf_height","12 mm","mm"),("shelf_ramp_length","25 mm","mm"),
            ("overall_width","base_width + 2 * tower_width","mm"),
        ]
        added=updated=0
        for name,expr,unit in SPEC:
            p=up.itemByName(name)
            if p:
                if p.expression!=expr:
                    p.expression=expr; updated+=1
            else:
                up.add(name, adsk.core.ValueInput.createByString(expr), unit, ''); added+=1
        removed=False
        old=up.itemByName('max_footprint')
        if old:
            try: old.deleteMe(); removed=True
            except: pass
        print("params=%d added=%d updated=%d removed_max_footprint=%s" % (up.count, added, updated, removed))
        for k in ("wall_thickness","overall_width","tower_width","base_width","screen_tilt"):
            pp=up.itemByName(k); print("  %s = %s -> %.3f %s" % (k, pp.expression, pp.value, pp.unit))
    except:
        print("ERROR: "+traceback.format_exc())

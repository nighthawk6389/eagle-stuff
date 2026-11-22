"""Build the unrouted menorah board: outline, footprints, nets, keep-outs. Writes menorah.kicad_pcb/.kicad_pro."""
import json
import os
import pcbnew
from pcbnew import FromMM, ToMM, VECTOR2I
from shapely.geometry import Point, box
import geometry as G
import netlist as N

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
os.makedirs(OUT, exist_ok=True)
PCB = f"{OUT}/menorah.kicad_pcb"


def V(x, y):
    return VECTOR2I(FromMM(x), FromMM(y))


board = pcbnew.BOARD()
nets = {}


def net(name):
    if name not in nets:
        ni = pcbnew.NETINFO_ITEM(board, name)
        board.Add(ni)
        nets[name] = ni
    return nets[name]


# ------------------------------------------------------------------ outline
outline = G.outline()
pts = list(outline.exterior.coords)
for a, b in zip(pts[:-1], pts[1:]):
    s = pcbnew.PCB_SHAPE(board)
    s.SetShape(pcbnew.SHAPE_T_SEGMENT)
    s.SetStart(V(*a))
    s.SetEnd(V(*b))
    s.SetLayer(pcbnew.Edge_Cuts)
    s.SetWidth(FromMM(0.05))
    board.Add(s)

# ------------------------------------------------------------------ parts
for p in N.PARTS:
    libdir = p["lib"] if p["lib"].startswith("/") else N.KL + p["lib"] + ".pretty"
    fp = pcbnew.FootprintLoad(libdir, p["fp"])
    assert fp is not None, p
    fp.SetReference(p["ref"])
    fp.SetValue(p["value"])
    if p["lcsc"]:
        fp.SetProperty("LCSC", p["lcsc"])
    fp.SetPosition(V(p["x"], p["y"]))
    fp.SetOrientationDegrees(p["rot"])
    board.Add(fp)
    fp.Flip(V(p["x"], p["y"]), True)
    if p["ref"] == "U1":   # 0.2 mm thermal vias are below the 2-layer drill minimum
        for pad in [q for q in fp.Pads() if q.GetAttribute() == pcbnew.PAD_ATTRIB_PTH]:
            fp.Remove(pad)
    if p.get("no_bom") or p["ref"].startswith("TP"):
        fp.SetAttributes(fp.GetAttributes() | pcbnew.FP_EXCLUDE_FROM_BOM | pcbnew.FP_EXCLUDE_FROM_POS_FILES)
    seen = set()
    for pad in fp.Pads():
        num = pad.GetNumber()
        if num == "":
            continue
        assert num in p["nets"], (p["ref"], num)
        seen.add(num)
        if p["nets"][num]:
            pad.SetNet(net(p["nets"][num]))
    assert seen == set(p["nets"]), (p["ref"], set(p["nets"]) - seen)
    ref = fp.Reference()
    ref.SetTextSize(VECTOR2I(FromMM(0.7), FromMM(0.7)))
    ref.SetTextThickness(FromMM(0.12))
    if p["ref"][0] in "CR" or p["ref"].startswith("D1") and len(p["ref"]) == 4:
        ref.SetVisible(False)
    fp.Value().SetVisible(False)


# ------------------------------------------------------------------ rule areas
def rule_area(poly, layers, tracks=True, vias=True, pour=False, name=""):
    z = pcbnew.ZONE(board)
    z.SetIsRuleArea(True)
    ls = pcbnew.LSET()
    for l in layers:
        ls.AddLayer(l)
    z.SetLayerSet(ls)
    z.SetDoNotAllowTracks(tracks)
    z.SetDoNotAllowVias(vias)
    z.SetDoNotAllowCopperPour(pour)
    z.SetDoNotAllowPads(False)
    z.SetDoNotAllowFootprints(False)
    z.SetZoneName(name)
    ol = z.Outline()
    ol.NewOutline()
    for x, y in list(poly.exterior.coords)[:-1]:
        ol.Append(FromMM(x), FromMM(y))
    board.Add(z)


F, B = pcbnew.F_Cu, pcbnew.B_Cu
rule_area(box(*G.ANT_KEEPOUT), [F, B], pour=True, name="antenna")
rule_area(box(*G.TEXT_BOX), [F], name="lettering")
rule_area(Point(*G.MIC).buffer(1.9, 8), [F], name="mic_ring")
for c in G.candles():
    art = c["drop"].union(c["neck"]).buffer(0.3, 4).intersection(outline).simplify(0.05)
    rule_area(art, [F], name=f"flame_{c['id']}")
    rule_area(Point(*c["hall"]).buffer(3.3, 8), [F], name=f"ring_{c['id']}")

# ------------------------------------------------------------------ back silk notes
def text(s, x, y, size=1.0, layer=pcbnew.B_SilkS):
    t = pcbnew.PCB_TEXT(board)
    t.SetText(s)
    t.SetPosition(V(x, y))
    t.SetLayer(layer)
    t.SetTextSize(VECTOR2I(FromMM(size), FromMM(size)))
    t.SetTextThickness(FromMM(size * 0.15))
    t.SetMirrored(layer == pcbnew.B_SilkS)
    board.Add(t)


bz = G.BATTERY_ZONE
for a, b in [((bz[0], bz[1]), (bz[2], bz[1])), ((bz[2], bz[1]), (bz[2], bz[3])),
             ((bz[2], bz[3]), (bz[0], bz[3])), ((bz[0], bz[3]), (bz[0], bz[1]))]:
    s = pcbnew.PCB_SHAPE(board)
    s.SetShape(pcbnew.SHAPE_T_SEGMENT)
    s.SetStart(V(*a)); s.SetEnd(V(*b)); s.SetLayer(pcbnew.B_SilkS); s.SetWidth(FromMM(0.15))
    board.Add(s)
text("LiPo 3.7V (max 32x30mm)", 126, 135.5, 1.2)
text("CHECK POLARITY", 126, 138.5, 1.0)
text("Menorah v1  5787", 126, 148.5, 1.0)

pcbnew.SaveBoard(PCB, board)

# ------------------------------------------------------------------ project file (rules + net classes)
def nc(name, w, clr=0.2):
    return {"name": name, "clearance": clr, "track_width": w, "via_diameter": 0.7, "via_drill": 0.3,
            "bus_width": 12, "diff_pair_gap": 0.25, "diff_pair_via_gap": 0.25, "diff_pair_width": 0.2,
            "line_style": 0, "microvia_diameter": 0.3, "microvia_drill": 0.1,
            "pcb_color": "rgba(0, 0, 0, 0.000)", "schematic_color": "rgba(0, 0, 0, 0.000)", "wire_width": 6}


pro = {
    "board": {"design_settings": {"rules": {
        "min_clearance": 0.15, "min_copper_edge_clearance": 0.25, "min_track_width": 0.15,
        "min_via_diameter": 0.6, "min_via_annular_width": 0.13, "min_through_hole_diameter": 0.3,
        "min_hole_clearance": 0.2, "min_hole_to_hole": 0.25, "min_silk_clearance": 0.0,
        "solder_mask_to_copper_clearance": 0.0, "min_text_height": 0.5, "min_text_thickness": 0.08}}},
    "net_settings": {"classes": [nc("Default", 0.2), nc("Power", 0.5)], "meta": {"version": 3},
                     "net_colors": None, "netclass_assignments": None,
                     "netclass_patterns": [{"netclass": "Power", "pattern": n} for n in N.POWER_NETS]},
    "meta": {"filename": "menorah.kicad_pro", "version": 1},
}
json.dump(pro, open(PCB.replace(".kicad_pcb", ".kicad_pro"), "w"), indent=1)

# ------------------------------------------------------------------ report
b2 = pcbnew.LoadBoard(PCB)
ds = b2.GetDesignSettings()
print("edge clearance", ToMM(ds.m_CopperEdgeClearance), "| netclass VLED:", b2.FindNet("VLED").GetNetClassName(),
      "| LED_D5:", b2.FindNet("LED_D5").GetNetClassName())
print("footprints", len(b2.GetFootprints()), "nets", b2.GetNetCount())
for ref in ["U1", "J1", "J2", "U11", "D101", "MK1", "SW1", "D1"]:
    fp = b2.FindFootprintByReference(ref)
    ps = {q.GetNumber(): (round(ToMM(q.GetPosition().x), 2), round(ToMM(q.GetPosition().y), 2)) for q in fp.Pads() if q.GetNumber()}
    keys = list(ps)[:4] + list(ps)[-3:] if len(ps) > 8 else list(ps)
    print(ref, "layer", fp.GetLayerName(), {k: ps[k] for k in keys})

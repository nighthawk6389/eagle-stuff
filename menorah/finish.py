"""Finish the routed board: GND pours, front gold artwork (F.Mask openings over the pour), back silk labels.

    /usr/bin/python3.12 finish.py        out/menorah_routed.kicad_pcb -> out/menorah_final.kicad_pcb
"""
import os, shutil, sys
import pcbnew
from pcbnew import FromMM, ToMM, VECTOR2I
from shapely.geometry import Polygon, Point, LineString, box, MultiPolygon
from shapely.ops import unary_union
from shapely import affinity
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import DecomposingRecordingPen
import geometry as G

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "out", "menorah_routed.kicad_pcb")
DST = os.path.join(HERE, "out", "menorah_final.kicad_pcb")
FONT = "/usr/share/fonts/truetype/freefont/FreeSerifBold.ttf"
TEXT = "נס גדול היה שם"          # "a great miracle happened there"

FLAME_INSET = 0.5     # gold flame stops this far from the board edge / LED window (black rim)
BORDER_IN, BORDER_W = 0.6, 0.5
RING_R, RING_W = 3.0, 0.6


def V(x, y):
    return VECTOR2I(FromMM(x), FromMM(y))


def chain_pts(ch):
    return [(ToMM(ch.CPoint(j).x), ToMM(ch.CPoint(j).y)) for j in range(ch.PointCount())]


def polyset_to_shapely(ps):
    out = []
    for i in range(ps.OutlineCount()):
        ext = chain_pts(ps.Outline(i))
        if len(ext) < 3:
            continue
        holes = [chain_pts(ps.Hole(i, h)) for h in range(ps.HoleCount(i))]
        p = Polygon(ext, [h for h in holes if len(h) >= 3])
        out.append(p if p.is_valid else p.buffer(0))
    return unary_union(out) if out else Polygon()


def polys(g):
    if g.is_empty:
        return []
    if g.geom_type == "Polygon":
        return [g]
    return [p for p in getattr(g, "geoms", []) if p.geom_type == "Polygon"]


def split_holes(p):
    """KiCad graphic polygons cannot have holes: cut the polygon with a vertical line through every hole."""
    if not p.interiors:
        return [p]
    x = p.interiors[0].centroid.x
    minx, miny, maxx, maxy = p.bounds
    out = []
    for half in (box(minx - 1, miny - 1, x, maxy + 1), box(x, miny - 1, maxx + 1, maxy + 1)):
        for q in polys(p.intersection(half)):
            out += split_holes(q)
    return out


def add_poly(board, poly, layer):
    n = 0
    for p in polys(poly):
        for q in split_holes(p):
            if q.area < 0.01:
                continue
            s = pcbnew.PCB_SHAPE(board)
            s.SetShape(pcbnew.SHAPE_T_POLY)
            s.SetLayer(layer)
            s.SetFilled(True)
            s.SetWidth(0)
            pts = pcbnew.VECTOR_VECTOR2I()
            for x, y in list(q.exterior.coords)[:-1]:
                pts.append(V(x, y))
            s.SetPolyPoints(pts)
            board.Add(s)
            n += 1
    return n


def add_text(board, s, x, y, size=1.0, layer=pcbnew.B_SilkS, thick=None):
    t = pcbnew.PCB_TEXT(board)
    t.SetText(s)
    t.SetPosition(V(x, y))
    t.SetLayer(layer)
    t.SetTextSize(VECTOR2I(FromMM(size), FromMM(size)))
    t.SetTextThickness(FromMM(thick or size * 0.15))
    t.SetMirrored(layer == pcbnew.B_SilkS)
    board.Add(t)


# ---------------------------------------------------------------------------------------------- lettering
def glyph_polygon(font, gs, name, steps=10):
    pen = DecomposingRecordingPen(gs)
    gs[name].draw(pen)
    rings, cur = [], []

    def quad(p0, p1, p2):
        return [((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0],
                 (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1]) for t in [i / steps for i in range(1, steps + 1)]]

    def cubic(p0, p1, p2, p3):
        return [((1 - t) ** 3 * p0[0] + 3 * (1 - t) ** 2 * t * p1[0] + 3 * (1 - t) * t * t * p2[0] + t ** 3 * p3[0],
                 (1 - t) ** 3 * p0[1] + 3 * (1 - t) ** 2 * t * p1[1] + 3 * (1 - t) * t * t * p2[1] + t ** 3 * p3[1])
                for t in [i / steps for i in range(1, steps + 1)]]

    for op, args in pen.value:
        if op == "moveTo":
            cur = [args[0]]
        elif op == "lineTo":
            cur.append(args[0])
        elif op == "qCurveTo":
            pts = list(args)
            if pts[-1] is None:                      # closed TrueType contour without on-curve points (rare)
                pts = pts[:-1] + [pts[0]]
            p0 = cur[-1]
            for i in range(len(pts) - 1):            # implied on-curve points between consecutive off-curve points
                c = pts[i]
                e = pts[i + 1] if i == len(pts) - 2 else ((pts[i][0] + pts[i + 1][0]) / 2, (pts[i][1] + pts[i + 1][1]) / 2)
                cur += quad(p0, c, e)
                p0 = e
        elif op == "curveTo":
            cur += cubic(cur[-1], *args)
        elif op in ("closePath", "endPath"):
            if len(cur) >= 3:
                rings.append(cur)
            cur = []
    shape = Polygon()
    for r in rings:                                  # even-odd fill
        p = Polygon(r)
        if not p.is_valid:
            p = p.buffer(0)
        shape = shape.symmetric_difference(p)
    return shape


def lettering(text, x0, y0, x1, y1, pad=0.6):
    """Hebrew text as polygons, right-to-left, centred in the box (front view, y down)."""
    font = TTFont(FONT)
    gs, cmap, hmtx = font.getGlyphSet(), font.getBestCmap(), font["hmtx"]
    glyphs, x = [], 0.0
    for ch in text:                                  # logical order; each glyph is placed to the LEFT of the previous one
        name = cmap[ord(ch)]
        adv = hmtx[name][0]
        x -= adv
        if ch != " ":
            glyphs.append(affinity.translate(glyph_polygon(font, gs, name), xoff=x))
    shape = unary_union(glyphs)
    minx, miny, maxx, maxy = shape.bounds
    s = min((x1 - x0 - 2 * pad) / (maxx - minx), (y1 - y0 - 2 * pad) / (maxy - miny))
    shape = affinity.scale(shape, xfact=s, yfact=-s, origin=(0, 0))          # font y is up, board y is down
    minx, miny, maxx, maxy = shape.bounds
    return affinity.translate(shape, xoff=(x0 + x1) / 2 - (minx + maxx) / 2, yoff=(y0 + y1) / 2 - (miny + maxy) / 2)


# ---------------------------------------------------------------------------------------------- main
def main():
    board = pcbnew.LoadBoard(SRC)
    gnd = board.FindNet("GND")
    outline = G.outline()
    minx, miny, maxx, maxy = outline.bounds

    # ---- GND pours, both layers
    for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
        z = pcbnew.ZONE(board)
        z.SetLayer(layer)
        z.SetNet(gnd)
        z.SetZoneName("GND_F" if layer == pcbnew.F_Cu else "GND_B")
        z.SetLocalClearance(FromMM(0.25))
        z.SetMinThickness(FromMM(0.2))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
        z.SetThermalReliefGap(FromMM(0.25))
        z.SetThermalReliefSpokeWidth(FromMM(0.4))
        z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
        ol = z.Outline()
        ol.NewOutline()
        for x, y in ((minx - 1, miny - 1), (maxx + 1, miny - 1), (maxx + 1, maxy + 1), (minx - 1, maxy + 1)):
            ol.Append(FromMM(x), FromMM(y))
        board.Add(z)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())

    front = Polygon()
    for z in board.Zones():
        if not z.GetIsRuleArea() and z.GetLayer() == pcbnew.F_Cu:
            front = polyset_to_shapely(z.GetFilledPolysList(pcbnew.F_Cu))
    print("front pour: %.0f mm2 in %d piece(s)" % (front.area, len(polys(front))))
    safe = front.buffer(-0.15)                        # artwork must sit on pour, never on a pour edge

    # non-GND copper on the front (hops, base routing): gold artwork keeps away from it
    other = []
    for t in board.GetTracks():
        if t.GetNetname() != "GND" and t.IsOnLayer(pcbnew.F_Cu):
            if t.Type() == pcbnew.PCB_VIA_T:
                other.append(Point(ToMM(t.GetPosition().x), ToMM(t.GetPosition().y)).buffer(ToMM(t.GetWidth()) / 2))
            else:
                other.append(LineString([(ToMM(t.GetStart().x), ToMM(t.GetStart().y)),
                                         (ToMM(t.GetEnd().x), ToMM(t.GetEnd().y))]).buffer(ToMM(t.GetWidth()) / 2))
    other = unary_union(other).buffer(0.45) if other else Polygon()

    mask = pcbnew.F_Mask
    n = 0
    # ---- flames
    board_in = outline.buffer(-FLAME_INSET)
    for c in G.candles():
        n += add_poly(board, c["drop"].intersection(board_in).intersection(safe).buffer(-0.05).buffer(0.05), mask)
        # ring over the hall sensor
        s = pcbnew.PCB_SHAPE(board)
        s.SetShape(pcbnew.SHAPE_T_CIRCLE)
        s.SetLayer(mask)
        s.SetCenter(V(*c["hall"]))
        s.SetEnd(V(c["hall"][0] + RING_R, c["hall"][1]))
        s.SetWidth(FromMM(RING_W))
        s.SetFilled(False)
        board.Add(s)
    # ---- ring round the microphone port
    s = pcbnew.PCB_SHAPE(board)
    s.SetShape(pcbnew.SHAPE_T_CIRCLE)
    s.SetLayer(mask)
    s.SetCenter(V(*G.MIC))
    s.SetEnd(V(G.MIC[0] + 1.3, G.MIC[1]))
    s.SetWidth(FromMM(0.5))
    s.SetFilled(False)
    board.Add(s)
    # ---- border line just inside the outer outline
    ext = Polygon(outline.exterior)
    band = ext.buffer(-BORDER_IN).difference(ext.buffer(-(BORDER_IN + BORDER_W)))
    band = band.intersection(safe).difference(other)
    band = unary_union([p for p in polys(band) if p.area > 0.8])          # drop slivers
    n += add_poly(board, band, mask)
    # ---- lettering
    letters = lettering(TEXT, *G.TEXT_BOX)
    assert safe.contains(letters), "lettering is not fully on the front GND pour"
    n += add_poly(board, letters, mask)
    print("artwork polygons:", n, "| lettering bounds", [round(v, 2) for v in letters.bounds],
          "| border length ~%.0f mm" % (band.area / BORDER_W))

    # ---- back silk labels
    j2 = board.FindFootprintByReference("J2")
    for pad in j2.Pads():
        if pad.GetNumber() in ("1", "2"):
            x, y = ToMM(pad.GetPosition().x), ToMM(pad.GetPosition().y)
            # printed just outside the connector mouth, in line with the wire that lands on this pin
            add_text(board, "+" if pad.GetNumber() == "1" else "-", 143.2, y + (0.5 if pad.GetNumber() == "1" else -0.5), 1.4, thick=0.25)
    for ref, label in (("SW1", "BOOT"), ("SW2", "RESET")):
        fp = board.FindFootprintByReference(ref)
        add_text(board, label, ToMM(fp.GetPosition().x), ToMM(fp.GetPosition().y) + 0.2, 0.8)
        fp.Reference().SetVisible(False)
    for ref in ("U2", "Q1", "Q2", "Q3", "MK1"):  # reference texts that sat on top of neighbouring silk
        board.FindFootprintByReference(ref).Reference().SetVisible(False)
    # test pads: label with the signal name instead of TPn
    for fp in board.GetFootprints():
        if fp.GetReference().startswith("TP"):
            fp.Reference().SetVisible(False)
            x, y = ToMM(fp.GetPosition().x), ToMM(fp.GetPosition().y)
            add_text(board, fp.GetValue(), x, y + (-1.9 if fp.GetReference() in ("TP2", "TP3") else 1.9), 0.6)
        # footprint silk that hangs over the board edge (USB connector front, module antenna end) is dropped
        for g in list(fp.GraphicalItems()):
            if g.GetLayer() == pcbnew.B_SilkS and g.GetClass() == "MGRAPHIC":
                bb = g.GetBoundingBox()
                gb = box(ToMM(bb.GetLeft()), ToMM(bb.GetTop()), ToMM(bb.GetRight()), ToMM(bb.GetBottom()))
                if not outline.buffer(-0.3).contains(gb):
                    fp.Remove(g)

    pcbnew.SaveBoard(DST, board)
    shutil.copy(SRC.replace(".kicad_pcb", ".kicad_pro"), DST.replace(".kicad_pcb", ".kicad_pro"))
    print("wrote", DST)


if __name__ == "__main__":
    main()

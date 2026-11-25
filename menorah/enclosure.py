"""3D-printable enclosure for the menorah PCB, generated from the board itself.

    /usr/bin/python3.12 enclosure.py        -> out/enclosure/*.stl, menorah_enclosure.3mf, preview PNGs

Three parts, all printed flat with no supports:
  menorah_back.stl     one-piece back.  The board drops into its pocket, parts side down.
  menorah_front.stl    open front frame.  It lies on the board and clips onto the back with 28 small lugs.
  menorah_stand.stl    stand.  The assembled menorah drops into its trough and leans back a few degrees.
plus menorah_fit_test_back.stl / menorah_fit_test_front.stl: one candle of each, to try the clip fit first.

How the clip works: the frame is a flat lattice of ~3 mm strips.  Each lug hangs from the middle of a straight
strip, outside the back's wall, and has a small bead that drops into a groove in the wall.  The strip bows and
twists a little to let the bead pass (in the strong direction of the print), so nothing thin has to bend across
the layers.  Lugs are only placed where the strip is long enough to do that.

Needs: pip install manifold3d trimesh.   NOT fit-tested against a real board or a real print.
"""
import math
import os
import subprocess
import numpy as np
import pcbnew
from pcbnew import ToMM
import trimesh
from manifold3d import Manifold, CrossSection, FillRule
from shapely.geometry import Polygon, Point, box
from shapely.ops import unary_union
from shapely import set_precision
import geometry as G

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "out", "menorah_final.kicad_pcb")
OUT = os.path.join(HERE, "out", "enclosure")

# ---------------------------------------------------------------- dimensions (mm)
T_PCB = 1.6
CL = 0.30            # gap between PCB edge and the pocket wall, each side
WALL = 1.6           # side wall thickness of the back
LEDGE = 0.8          # the PCB rests on a ledge this wide round its edge
BACK = 1.6           # rear wall behind the base cavity
CAV_BASE = 8.0       # behind the base: module 3.3, USB-C 3.3, JST ~6, battery up to ~7
CAV_TOP = 2.5        # behind candles, crossbar, upper stem: SOT-23s, 0603/0805, LEDs, mic (all < 1.5 mm)
Y_SPLIT = 108.0      # board y where the shallow cavity ends and the deep one starts (across the stem)
SEAT = 0.1           # the wall top stops this far below the board's front face, so the frame clamps the board

OVERLAP = 1.2        # how far the frame reaches over the board edge (hides the edge and the gold border line)
TF = 1.6             # frame thickness
EDGE = 0.4           # bevel on the frame's front edges and on the back's top outer edge (a shadow line)
LUG_T, LUG_GAP = 1.6, 0.2      # clip lug thickness, and its clearance to the wall
BEAD, GROOVE = 0.45, 0.55      # bead height on the lug, groove depth in the wall (snap interference = BEAD - LUG_GAP)
PLAY = 0.1                     # vertical play of the bead in the groove

USB_Y = (124.5, 137.5)                    # opening for the USB-C plug overmould (connector centre y = 131)
BUTTONS = [(150.5, 140.2), (150.5, 146.4)]   # RESET, BOOT (board coordinates), reached through 4 mm holes
LEAN = 4.0                                # the stand leans the menorah back by this many degrees

ZB = BACK + CAV_BASE        # back face of the PCB (z = 0 is the rear of the enclosure, z grows towards the front)
ZF = ZB + T_PCB             # front face of the PCB = underside of the frame
ZT = ZF - SEAT              # top of the back's wall
ZTOP = ZF + TF              # front face of the frame
W0 = CL + WALL              # outer wall surface, measured out from the board edge

# part heights above the back of the board, used only for the interference check
HEIGHT = {"U1": 3.4, "J1": 3.4, "J2": 6.5, "SW": 1.8, "D1": 2.5, "MK": 1.2, "D": 1.3, "TP": 0.1}


def height_of(ref):
    for k in ("U1", "J1", "J2", "D1"):
        if ref == k:
            return HEIGHT[k]
    for k in ("SW", "MK", "TP"):
        if ref.startswith(k):
            return HEIGHT[k]
    if ref.startswith("D"):
        return HEIGHT["D"]
    return 1.6


# ---------------------------------------------------------------- 2D -> 3D helpers
def snap(g):
    """Everything on a 0.01 mm grid: no near-coincident vertices in the exported mesh."""
    return set_precision(g, 0.01)


def prism(geom, z0, z1):
    """Extrude a shapely (multi)polygon given in BOARD coordinates (x right, y down) between z0 and z1.
    Model axes: X = board x, Y = -board y, Z = towards the front of the menorah."""
    out = Manifold()
    geom = snap(geom)
    polys = [geom] if geom.geom_type == "Polygon" else [g for g in getattr(geom, "geoms", []) if g.geom_type == "Polygon"]
    for p in polys:
        if p.is_empty or p.area < 1e-4:
            continue
        rings = [np.array([(x, -y) for x, y in list(p.exterior.coords)[:-1]])]
        rings += [np.array([(x, -y) for x, y in list(h.coords)[:-1]]) for h in p.interiors]
        cs = CrossSection([r.tolist() for r in rings], FillRule.EvenOdd)
        out += Manifold.extrude(cs, z1 - z0).translate([0, 0, z0])
    return out


def slices(z_from, z_to, p_from, p_to, step=0.1):
    """A 45-degree face as a stack of thin slabs: yields (z_low, z_high, protrusion)."""
    n = max(1, int(round(abs(z_to - z_from) / step)))
    for i in range(n):
        za, zb_ = z_from + (z_to - z_from) * i / n, z_from + (z_to - z_from) * (i + 1) / n
        yield min(za, zb_), max(za, zb_), p_from + (p_to - p_from) * (i + 0.5) / n


def to_trimesh(m):
    mesh = m.to_mesh()
    return trimesh.Trimesh(vertices=np.asarray(mesh.vert_properties)[:, :3], faces=np.asarray(mesh.tri_verts), process=False)


def poly_from_set(ps):
    out = []
    for i in range(ps.OutlineCount()):
        ol = ps.Outline(i)
        pts = [(ToMM(ol.CPoint(j).x), ToMM(ol.CPoint(j).y)) for j in range(ol.PointCount())]
        if len(pts) >= 3:
            out.append(Polygon(pts).buffer(0))
    return unary_union(out) if out else Polygon()


# ---------------------------------------------------------------- board geometry
def board_data():
    board = pcbnew.LoadBoard(PCB)
    parts = []
    for fp in board.GetFootprints():
        ref = fp.GetReference()
        if ref == "U1":       # its courtyard includes the antenna keep-out; use the module body instead
            g = box(60.5, 118.0, 79.5, 144.4)
        else:
            g = poly_from_set(fp.GetCourtyard(pcbnew.B_CrtYd))
            if g.is_empty:
                bb = fp.GetBoundingBox(False, False)
                g = box(ToMM(bb.GetLeft()), ToMM(bb.GetTop()), ToMM(bb.GetRight()), ToMM(bb.GetBottom()))
        parts.append((ref, g, height_of(ref)))
    return parts


def frame_layout():
    """Where the frame's cross bars and clip lugs go (board coordinates).  A lug is the piece of the offset
    outline that falls inside its box, so the boxes only have to straddle the right stretch of edge."""
    root = G.BAR_TOP - 0.8                                         # top edge of the bar across each candle's foot
    bars, lugs = [], []
    for c in G.candles():
        cx, hw = c["x"], c["w"] / 2
        bars.append(box(cx - hw - 1.5, root, cx + hw + 1.5, root + 2.0))
        mid = (c["top"] + root) / 2                                # lugs near the middle of each side, staggered
        lugs.append(box(cx - hw - 4.5, mid - 7.1, cx - hw - 0.5, mid - 0.1))
        lugs.append(box(cx + hw + 0.5, mid + 0.1, cx + hw + 4.5, mid + 7.1))
    bars += [box(41, G.BAR_TOP, 43, G.BAR_BOT), box(157, G.BAR_TOP, 159, G.BAR_BOT)]          # crossbar uprights
    bars += [box(G.STEM_X0 - 2.5, G.BAR_BOT - 1.2, G.STEM_X1 + 2.5, G.BAR_BOT + 0.8),          # top of the stem
             box(G.STEM_X0 - 2.5, G.BASE_TOP - 0.8, G.STEM_X1 + 2.5, G.BASE_TOP + 1.2)]        # foot of the stem
    bar_y = G.TEXT_BOX[1] - 3.2                                    # bar above the lettering
    bars.append(box(G.BASE_X0 - 1, bar_y, G.BASE_X1 + 1, bar_y + 2.0))
    slot_top = G.BASE_BOT - G.FOOT_SLOT_DEPTH - G.FOOT_SLOT_W / 2  # hide the foot slots and the gold line round them
    bars += [box(fx - 2.4, slot_top - 1.0, fx + 2.4, G.BASE_BOT + 1) for fx in G.FOOT_SLOT_X]
    lugs += [box(x, G.BAR_BOT + 0.5, x + 7, G.BAR_BOT + 5) for x in (20, 61.5, 131.5, 173)]   # under the crossbar
    lugs += [box(G.STEM_X0 - 5, 97.5, G.STEM_X0 - 0.5, 104.5), box(G.STEM_X1 + 0.5, 97.5, G.STEM_X1 + 5, 104.5)]
    lugs += [box(x, G.BASE_TOP - 5, x + 7, G.BASE_TOP - 0.5) for x in (63, 130)]              # on top of the base
    bottom = [box(x, G.BASE_BOT + 0.5, x + 7, G.BASE_BOT + 5) for x in (71.5, 121.5)]         # under the base
    return unary_union(bars), lugs + bottom, bottom


def build():
    os.makedirs(OUT, exist_ok=True)
    parts = board_data()
    board_shape = Polygon(G.outline().exterior)
    # the foot slots are not used by this enclosure: treat them as part of the board outline
    filled = snap(unary_union([board_shape] + [box(fx - 1.5, G.BASE_BOT - G.FOOT_SLOT_DEPTH - 1.5, fx + 1.5, G.BASE_BOT)
                                               for fx in G.FOOT_SLOT_X]))
    cache = {}

    def off(d):                                  # the board outline grown (or shrunk) by d
        if d not in cache:
            cache[d] = snap(filled.buffer(d, 16))
        return cache[d]

    def band(d0, d1):                            # the strip between two offsets
        return off(round(d1, 3)).difference(off(round(d0, 3)))

    pocket, outer = off(CL), off(W0)
    keep = unary_union([g.buffer(0.35) for ref, g, h in parts if h > 0.2]).intersection(pocket)
    cavity = snap(unary_union([off(-LEDGE), keep]).intersection(pocket))
    bars, lug_boxes, bottom_lugs = frame_layout()
    lug_zone = unary_union(lug_boxes)
    near_lugs = unary_union([b.buffer(1.0, join_style=2) for b in lug_boxes])

    # ---------------------------------------------------------------- back
    back = prism(outer, 0, ZT)
    back -= prism(pocket, ZB, ZT + 1)
    back -= prism(cavity.intersection(box(-20, -20, 220, Y_SPLIT)), ZB - CAV_TOP, ZB)     # shallow: thick floor
    back -= prism(cavity.intersection(box(-20, Y_SPLIT, 220, 180)), BACK, ZB)             # deep, behind the base
    for za, zb_, p in slices(ZT - EDGE, ZT, 0, EDGE, 0.2):                                # bevel = lead-in for the lugs
        back -= prism(band(W0 - p, W0 + 1), za, ZT + 1)
    g_top = ZB - 0.10                                                                     # groove for the lug beads
    prof = list(slices(g_top, g_top - GROOVE, 0, GROOVE)) + [(g_top - GROOVE - 0.35, g_top - GROOVE, GROOVE)]
    prof += list(slices(g_top - GROOVE - 0.35, g_top - 2 * GROOVE - 0.35, GROOVE, 0))
    for za, zb_, p in prof:
        back -= prism(band(W0 - p, W0 + 1).intersection(near_lugs), za, zb_)
    # USB-C: slot through the left wall, open to the front so the board can still drop in
    back -= prism(box(G.BASE_X0 - W0 - 1, USB_Y[0], G.BASE_X0 + 1.6, USB_Y[1]), ZB - 5.2, ZT + 1)
    for bx, by in BUTTONS:
        back -= prism(Point(bx, by).buffer(2.0, 24), -1, BACK + 0.5)

    # ---------------------------------------------------------------- front frame
    rings = unary_union([Point(c["hall"]).buffer(3.75, 32) for c in G.candles()])        # show the whole touch ring
    window = unary_union([off(-OVERLAP), rings.intersection(off(-0.45))]).difference(bars)
    ears = band(W0 - 0.3, W0 + LUG_GAP + LUG_T).intersection(near_lugs)
    plate = unary_union([outer.difference(window), ears])
    plate = plate.buffer(0.5, 8).buffer(-1.0, 8).buffer(0.5, 8)             # fillet inside corners, round outside ones
    frame = prism(plate, ZF, ZTOP - EDGE)
    for za, zb_, p in slices(ZTOP - EDGE, ZTOP, 0, EDGE, 0.2):              # bevelled front edges
        frame += prism(plate.buffer(-p, 8), za, zb_)
    lug_bot = ZB - BEAD - 0.3 - BEAD - 0.1
    frame += prism(band(W0 + LUG_GAP, W0 + LUG_GAP + LUG_T).intersection(lug_zone), lug_bot, ZF + 0.2)
    b_top = g_top + LUG_GAP - PLAY                                          # bead: mirror image of the groove
    prof = list(slices(b_top, b_top - BEAD, 0, BEAD)) + [(b_top - BEAD - 0.3, b_top - BEAD, BEAD)]
    prof += list(slices(b_top - BEAD - 0.3, b_top - 2 * BEAD - 0.3, BEAD, 0))
    for za, zb_, p in prof:
        frame += prism(band(W0 + LUG_GAP - p, W0 + LUG_GAP + 0.2).intersection(lug_zone), za, zb_)
    # room for a fat USB-C plug overmould, which stands a little proud of the board's front face
    frame -= prism(box(G.BASE_X0 - W0 - 3, USB_Y[0], G.BASE_X0 - 0.1, USB_Y[1]), ZF - 1, ZF + 0.5)

    # ---------------------------------------------------------------- checks on the assembled pair
    pcb = prism(board_shape.buffer(-0.02), ZB + 0.02, ZF - 0.02)
    report = [f"back: overlap with PCB {(back ^ pcb).volume():.3f} mm3; frame: overlap with PCB {(frame ^ pcb).volume():.3f} mm3, "
              f"with the back {(frame ^ back).volume():.3f} mm3"]
    worst = 0.0
    for ref, g, hgt in parts:
        v = (back ^ prism(g, ZB - hgt - 0.3, ZB + 0.005)).volume()
        worst = max(worst, v)
        if v > 1e-3:
            report.append(f"   {ref} touches the back ({v:.2f} mm3)")
    report.append(f"back: worst overlap with a part {worst:.3f} mm3")
    lifted = frame.translate([0, 0, BEAD + 0.6])                     # beads level with the wall just above the groove
    report.append(f"clip: {len(lug_boxes)} lugs, snap interference {BEAD - LUG_GAP:.2f} mm "
                  f"(frame lifted {BEAD + 0.6:.2f} mm overlaps the wall by {(lifted ^ back).volume():.2f} mm3)")
    report.append(f"frame: {len(window.geoms) if window.geom_type == 'MultiPolygon' else 1} windows, "
                  f"{window.area / filled.area * 100:.0f} % of the board's face is open")

    # ---------------------------------------------------------------- stand
    # Built in the menorah's own tilted frame (x, v = depth from the front, w = up along the menorah), then leaned back.
    xb = outer.intersection(box(-20, 140, 220, 180)).bounds
    tx0, tx1, ty1 = xb[0] - 0.2, xb[2] + 0.2, ZTOP + 0.4            # trough: 0.2 clearance each side, 0.4 in depth
    y_out = G.BASE_BOT + W0                                          # board y of the enclosure's bottom face
    PL, WT, DEEP = 3.0, 3.0, 8.0
    lip = W0 + OVERLAP                                               # front lip: level with the frame's bottom strip
    s, c = math.sin(math.radians(LEAN)), math.cos(math.radians(LEAN))
    lean = [[1, 0, 0, 0], [0, c, s, 0], [0, -s, c, PL + 0.3 + ty1 * s]]   # (x, v, w) -> world; trough floor just above the plate

    def block(xa, xb_, va, vb, wa, wb):
        return Manifold.cube([xb_ - xa, vb - va, wb - wa]).translate([xa, va, wa])

    cradle = block(tx0 - WT, tx1 + WT, -WT, ty1 + WT, -DEEP, 0)                 # floor wedge
    cradle += block(tx0 - WT, tx1 + WT, -WT, 0, -DEEP, lip)                     # front lip
    cradle += block(tx0 - WT, tx1 + WT, ty1, ty1 + WT, -DEEP, lip)              # low back wall (clear of the BOOT hole)
    cradle += block(tx0 - WT, tx0, -WT, ty1 + WT, -DEEP, 8)                     # sides
    cradle += block(tx1, tx1 + WT, -WT, ty1 + WT, -DEEP, 8)
    cradle += block(62, 138, ty1, ty1 + 4, -DEEP, 34)                           # rear buttress the menorah leans on
    tri = Manifold.extrude(CrossSection([[[ty1 + 3, -DEEP], [ty1 + 30, -DEEP], [ty1 + 30, 0], [ty1 + 3, 32]]], FillRule.EvenOdd), 4)
    for gx in (62, 98, 134):                                                    # gussets: (v, w, x) -> (x, v, w)
        cradle += tri.transform([[0, 0, 1, gx], [1, 0, 0, 0], [0, 1, 0, 0]])
    plate2d = box(tx0 - 13, -18, tx1 + 13, 50).buffer(-6).buffer(6, 16)
    stand = Manifold.extrude(CrossSection([np.array(plate2d.exterior.coords[:-1]).tolist()], FillRule.EvenOdd), PL)
    stand += cradle.transform(lean)
    stand -= Manifold.cube([400, 400, 50]).translate([-100, -100, -50])         # nothing below the table
    for lb in bottom_lugs:                                                      # pockets for the two lugs under the base
        stand -= block(lb.bounds[0] - 2.5, lb.bounds[2] + 2.5, 0, ZTOP - lug_bot + 1.2, -(LUG_GAP + LUG_T + 0.6), 1).transform(lean)
    # the assembled menorah in the stand: model (X, Y = -board y, Z) -> (x, v, w) -> world
    seat = [[1, 0, 0, 0], [0, 0, -1, ZTOP + 0.2], [0, 1, 0, y_out]]
    placed = lambda m: m.transform(seat).transform(lean)
    report.append(f"stand: overlap with the seated menorah {(stand ^ placed(back + frame)).volume():.3f} mm3")

    # ---------------------------------------------------------------- fit-test coupon: candle C1 of both parts
    cut = prism(box(-8, 10, 18.9, 95), -5, 30)
    solids = dict(menorah_back=back, menorah_front=frame, menorah_stand=stand,
                  menorah_fit_test_back=back ^ cut, menorah_fit_test_front=frame ^ cut)
    info = dict(plate=plate, outer=outer, board=board_shape, placed=placed, pcb=pcb,
                thickness=ZTOP, trough=(round(tx1 - tx0, 1), ty1))
    return solids, report, info


# ---------------------------------------------------------------- previews
def render(items, elev, azim, size=900):
    """Tiny z-buffer renderer (orthographic, Lambert shading) for a list of (mesh, rgb)."""
    e, a = np.radians(elev), np.radians(azim)
    view = np.array([np.cos(e) * np.cos(a), np.cos(e) * np.sin(a), np.sin(e)])          # from the part towards the eye
    right = np.cross([0, 0, 1], view); right /= np.linalg.norm(right)
    up = np.cross(view, right)
    allv = np.vstack([m.vertices for m, _ in items])
    mid = (allv.min(axis=0) + allv.max(axis=0)) / 2
    proj = [np.c_[(m.vertices - mid) @ right, (m.vertices - mid) @ up, (m.vertices - mid) @ view] for m, _ in items]
    allp = np.vstack(proj)
    lo, hi = allp.min(axis=0), allp.max(axis=0)
    scale = (size - 40) / max(hi[0] - lo[0], hi[1] - lo[1])
    w, h = int((hi[0] - lo[0]) * scale) + 40, int((hi[1] - lo[1]) * scale) + 40
    img = np.full((h, w, 3), 255, np.uint8)
    zbuf = np.full((h, w), -1e9)
    light = np.array([-0.35, -0.45, 0.82]); light /= np.linalg.norm(light)
    for (mesh, rgb), p in zip(items, proj):
        px = (p[:, 0] - lo[0]) * scale + 20
        py = (hi[1] - p[:, 1]) * scale + 20
        shade = 0.25 + 0.75 * np.clip(mesh.face_normals @ light, 0, 1)
        facing = mesh.face_normals @ view > 0
        for f, sh in zip(mesh.faces[facing], shade[facing]):
            x, y, z = px[f], py[f], p[f, 2]
            x0, x1 = int(max(np.floor(x.min()), 0)), int(min(np.ceil(x.max()), w - 1))
            y0, y1 = int(max(np.floor(y.min()), 0)), int(min(np.ceil(y.max()), h - 1))
            if x1 < x0 or y1 < y0:
                continue
            gx, gy = np.meshgrid(np.arange(x0, x1 + 1), np.arange(y0, y1 + 1))
            d = (y[1] - y[2]) * (x[0] - x[2]) + (x[2] - x[1]) * (y[0] - y[2])
            if abs(d) < 1e-9:
                continue
            l0 = ((y[1] - y[2]) * (gx - x[2]) + (x[2] - x[1]) * (gy - y[2])) / d
            l1 = ((y[2] - y[0]) * (gx - x[2]) + (x[0] - x[2]) * (gy - y[2])) / d
            l2 = 1 - l0 - l1
            inside = (l0 >= -1e-3) & (l1 >= -1e-3) & (l2 >= -1e-3)
            zz = l0 * z[0] + l1 * z[1] + l2 * z[2]
            sub = zbuf[y0:y1 + 1, x0:x1 + 1]
            hit = inside & (zz > sub)
            sub[hit] = zz[hit]
            img[y0:y1 + 1, x0:x1 + 1][hit] = (np.array(rgb) * sh).astype(np.uint8)
    return img


def stack(shots, path):
    from PIL import Image
    w = max(s.shape[1] for s in shots)
    canvas = np.full((sum(s.shape[0] for s in shots) + 20 * (len(shots) - 1), w, 3), 255, np.uint8)
    y = 0
    for s in shots:
        canvas[y:y + s.shape[0], (w - s.shape[1]) // 2:(w - s.shape[1]) // 2 + s.shape[1]] = s
        y += s.shape[0] + 20
    Image.fromarray(canvas).save(path)


def front_view(info, path, px=8):
    """What you see from the front: the board (black, gold artwork, LED windows) behind the frame."""
    from PIL import Image, ImageDraw
    x0, y0, x1, y1 = -4.0, -2.0, 204.0, 160.0
    size = (int((x1 - x0) * px), int((y1 - y0) * px))

    def mask(geom):
        m = Image.new("L", size, 0)
        d = ImageDraw.Draw(m)
        for p in ([geom] if geom.geom_type == "Polygon" else geom.geoms):
            d.polygon([((x - x0) * px, (y - y0) * px) for x, y in p.exterior.coords], fill=255)
            for h in p.interiors:
                d.polygon([((x - x0) * px, (y - y0) * px) for x, y in h.coords], fill=0)
        return m

    img = Image.new("RGB", size, (236, 234, 228))
    img.paste((34, 37, 43), mask=mask(info["outer"]))                      # the back's wall top, seen through gaps
    img.paste((16, 16, 16), mask=mask(info["board"]))                      # black solder mask
    try:                                                                   # gold = openings in the front mask layer
        import re, cairosvg
        svg_path = os.path.join(OUT, "_mask.svg")
        subprocess.run(["kicad-cli", "pcb", "export", "svg", "-o", svg_path, "--layers", "F.Mask", "--black-and-white",
                        "--exclude-drawing-sheet", "--page-size-mode", "0", PCB], check=True, capture_output=True)
        svg = open(svg_path).read()                                        # page mode 0: SVG units are board mm
        os.remove(svg_path)
        svg = re.sub(r'viewBox="[^"]+"', f'viewBox="{x0} {y0} {x1 - x0} {y1 - y0}"', svg, 1)
        svg = re.sub(r'width="[^"]+"', f'width="{x1 - x0}mm"', svg, 1)
        svg = re.sub(r'height="[^"]+"', f'height="{y1 - y0}mm"', svg, 1)
        png = cairosvg.svg2png(bytestring=svg.encode(), output_width=size[0], output_height=size[1], background_color="white")
        import io
        gold = np.asarray(Image.open(io.BytesIO(png)).convert("L")) < 128
        gold &= np.asarray(mask(info["board"])) > 0
        img.paste((203, 168, 72), mask=Image.fromarray((gold * 255).astype(np.uint8)))
    except Exception as e:                                                 # preview only: carry on without the artwork
        print("front view without gold artwork:", e)
    leds = unary_union([box(x - 1.7, y - 1.5, x + 1.7, y + 1.5).buffer(0.3) for x, y in (l["pos"] for l in G.chain_order())])
    img.paste((255, 236, 170), mask=mask(leds))
    img.paste((58, 63, 74), mask=mask(info["plate"]))                      # the frame
    img.paste((90, 97, 112), mask=mask(info["plate"].buffer(-0.4).buffer(0)))   # its flat face inside the bevel
    img.save(path)


def main():
    solids, report, info = build()
    meshes = {}
    scene = trimesh.Scene()
    yoff = 0.0
    for name, s in solids.items():
        m = to_trimesh(s)
        if name.endswith("front"):                        # the frame prints face down, lugs up
            m.apply_transform(trimesh.transformations.rotation_matrix(math.pi, [1, 0, 0]))
        m.apply_translation(-m.bounds[0])                 # each part starts at the origin, resting on z = 0
        assert m.is_watertight and len(s.decompose()) == 1, (name, len(s.decompose()))
        m.export(os.path.join(OUT, name + ".stl"))
        back = trimesh.load(os.path.join(OUT, name + ".stl"))
        assert back.is_watertight, name + ": exported STL is not a closed solid after vertex merging"
        meshes[name] = m
        if "fit_test" not in name:
            placed = m.copy()
            placed.apply_translation([0, yoff, 0])
            scene.add_geometry(placed, node_name=name, geom_name=name)
            yoff += m.extents[1] + 8
        print(f"{name}: {m.extents[0]:.1f} x {m.extents[1]:.1f} x {m.extents[2]:.1f} mm, {m.volume/1000:.1f} cm3, "
              f"{len(m.faces)} triangles, watertight={m.is_watertight}")
    scene.export(os.path.join(OUT, "menorah_enclosure.3mf"))

    blue, grey, dark, gold = (70, 110, 190), (150, 156, 170), (40, 40, 44), (203, 168, 72)
    front_view(info, os.path.join(OUT, "preview_front.png"))
    stack([render([(meshes["menorah_back"], blue)], 50, -100, 1100),
           render([(meshes["menorah_front"], grey)], 50, -100, 1100),
           render([(meshes["menorah_stand"], blue)], 30, -60, 800)], os.path.join(OUT, "preview_parts.png"))
    seated = [(to_trimesh(info["placed"](solids["menorah_back"])), blue), (to_trimesh(info["placed"](solids["menorah_front"])), grey),
              (to_trimesh(info["placed"](info["pcb"])), dark), (to_trimesh(solids["menorah_stand"]), blue)]
    stack([render(seated, 12, -62, 1100), render(seated, 8, 25, 700)], os.path.join(OUT, "preview_assembled.png"))
    print("\n".join(report))
    print({k: v for k, v in info.items() if k in ("thickness", "trough")})


if __name__ == "__main__":
    main()

"""3D-printable enclosure for the menorah PCB, generated from the board itself.

    /usr/bin/python3.12 enclosure.py        -> out/enclosure/*.stl, menorah_enclosure.3mf, preview PNGs

Three parts, all printed flat with no supports:
  menorah_back_top.stl    thin back shell for the candles, crossbar and upper stem
  menorah_back_base.stl   deeper back box for the base (ESP32, battery, USB-C, buttons)
  menorah_stand.stl       stand: the base box drops into its trough

The PCB presses into each shell from the front and is held by small snap ridges on the rim.  The front of
the board stays fully visible inside a 1.6 mm frame.  Needs: pip install manifold3d trimesh matplotlib.

NOT fit-tested against a real board: dimensions come from the board file and typical part heights.
"""
import os
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
WALL = 1.6           # rim / side wall thickness
LEDGE = 0.8          # the PCB rests on a ledge this wide round its edge
LIP = 0.8            # rim height above the PCB front face
RIDGE = 0.45         # how far a snap ridge reaches over the PCB edge
Y_SPLIT, GAP, ENDW = 108.0, 0.3, 1.2      # the two shells meet across the stem at this board y

TOP = dict(back=1.2, cavity=2.5)          # behind the candles: SOT-23s, 0603/0805, LEDs, mic (all < 1.5 mm)
BASE = dict(back=1.6, cavity=8.0)         # behind the base: module 3.3, USB-C 3.3, JST ~6, battery up to ~7

USB_Y = (124.5, 137.5)                    # opening for the USB-C plug overmould (connector centre y = 131)
BUTTONS = [(150.5, 140.2), (150.5, 146.4)]   # RESET, BOOT (board coordinates), reached through 4 mm holes

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
def prism(geom, z0, z1):
    """Extrude a shapely (multi)polygon given in BOARD coordinates (x right, y down) between z0 and z1.
    Model axes: X = board x, Y = -board y, Z = towards the front of the menorah (z = 0 is the print bed)."""
    out = Manifold()
    polys = [geom] if geom.geom_type == "Polygon" else [g for g in getattr(geom, "geoms", []) if g.geom_type == "Polygon"]
    for p in polys:
        if p.is_empty or p.area < 1e-4:
            continue
        rings = [np.array([(x, -y) for x, y in list(p.exterior.coords)[:-1]])]
        rings += [np.array([(x, -y) for x, y in list(h.coords)[:-1]]) for h in p.interiors]
        cs = CrossSection([r.tolist() for r in rings], FillRule.EvenOdd)
        out += Manifold.extrude(cs, z1 - z0).translate([0, 0, z0])
    return out


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


def build():
    os.makedirs(OUT, exist_ok=True)
    parts = board_data()
    o = G.outline()
    board_shape = Polygon(o.exterior)
    # the foot slots are not used by this enclosure: treat them as part of the board outline
    def snap(g):                 # everything on a 0.01 mm grid: no near-coincident vertices in the exported mesh
        return set_precision(g, 0.01)
    filled = snap(unary_union([board_shape] + [box(fx - 1.5, G.BASE_BOT - G.FOOT_SLOT_DEPTH - 1.5, fx + 1.5, G.BASE_BOT)
                                               for fx in G.FOOT_SLOT_X]))
    pocket = snap(filled.buffer(CL, 16))
    outer = snap(filled.buffer(CL + WALL, 16))
    keep = unary_union([g.buffer(0.35) for ref, g, h in parts if h > 0.2]).intersection(pocket)
    cavity = snap(unary_union([filled.buffer(-LEDGE, 16), keep]).intersection(pocket))
    rooted = filled.buffer(CL + 0.4, 16)                            # ridges start 0.4 mm inside the wall, so they fuse with it
    band_full = snap(rooted.difference(filled.buffer(-RIDGE, 16)))  # snap ridge, full reach
    band_step = snap(rooted.difference(filled.buffer(-0.05, 16)))   # its lead-in step (keeps the overhang small)

    big = box(-20, -20, 220, 180)
    top_half = box(-20, -20, 220, Y_SPLIT - GAP / 2)
    base_half = box(-20, Y_SPLIT + GAP / 2, 220, 180)

    def shell(dim, half, cav_half, ridge_boxes):
        zb = dim["back"] + dim["cavity"]            # back face of the PCB
        zf = zb + T_PCB                              # front face of the PCB
        h = zf + LIP
        s = prism(snap(outer.intersection(half)), 0, h)
        s -= prism(pocket, zb, h + 1)
        s -= prism(snap(cavity.intersection(cav_half)), dim["back"], zb)
        for b in ridge_boxes:
            s += prism(snap(band_step.intersection(b).intersection(half)), zf + 0.15, zf + 0.35)
            s += prism(snap(band_full.intersection(b).intersection(half)), zf + 0.35, h)
        return s, zb, zf, h

    # ---- top shell: ridges on the crossbar's lower edge and on its upper edge between candles
    top_ridges = [box(x0, 83.0, x1, 85.5) for x0, x1 in ((25, 45), (60, 80), (120, 140), (155, 175))]
    top_ridges += [box(x0, 68.5, x1, 71.0) for x0, x1 in ((17.5, 22.5), (61.5, 66.5), (133.5, 138.5), (177.5, 182.5))]
    top, zb_t, zf_t, h_t = shell(TOP, top_half, box(-20, -20, 220, Y_SPLIT - GAP / 2 - ENDW), top_ridges)

    # ---- base box: ridges on the base's top, bottom and side edges
    base_ridges = [box(62, 116.5, 78, 119.5), box(122, 116.5, 138, 119.5),          # top edge of the base
                   box(65, 150.5, 85, 153.5), box(115, 150.5, 135, 153.5),          # bottom edge
                   box(153.5, 124, 156.5, 134), box(43.5, 139.5, 46.5, 146.5)]      # right side, left side below USB
    base, zb_b, zf_b, h_b = shell(BASE, base_half, box(-20, Y_SPLIT + GAP / 2 + ENDW, 220, 180), base_ridges)
    # USB-C: slot through the left wall, open to the front so the board can still drop in
    base -= prism(box(G.BASE_X0 - CL - WALL - 1, USB_Y[0], G.BASE_X0 + 1.6, USB_Y[1]), zb_b - 5.2, h_b + 1)
    for bx, by in BUTTONS:
        base -= prism(Point(bx, by).buffer(2.0, 24), -1, BASE["back"] + 0.5)

    # ---- interference check: no shell material inside the PCB or inside any part's volume
    report = []
    for name, s, zb in (("top", top, zb_t), ("base", base, zb_b)):
        pcb_vol = (s ^ prism(board_shape.buffer(-0.02), zb + 0.02, zb + T_PCB - 0.02)).volume()
        worst = 0.0
        for ref, g, hgt in parts:
            v = (s ^ prism(g, zb - hgt - 0.3, zb + 0.005)).volume()
            if v > 1e-3:
                report.append(f"   {name}: {ref} touches the shell ({v:.2f} mm3)")
            worst = max(worst, v)
        report.insert(0, f"{name}: overlap with PCB {pcb_vol:.3f} mm3, worst part overlap {worst:.3f} mm3")

    # ---- stand: plate + trough for the base box + rear buttress.  X = board x, Y = depth (front is -Y), Z up
    x0, x1 = outer.intersection(box(-20, 140, 220, 180)).bounds[0], outer.intersection(box(-20, 140, 220, 180)).bounds[2]
    tx0, tx1, ty1 = x0 - 0.2, x1 + 0.2, h_b + 0.4                  # trough: 0.2 clearance each side, 0.4 in depth
    PL, WT = 3.0, 3.0

    def block(xa, xb, ya, yb, za, zb_):
        return Manifold.cube([xb - xa, yb - ya, zb_ - za]).translate([xa, ya, za])

    plate2d = box(tx0 - 13, -18, tx1 + 13, 50).buffer(-6).buffer(6, 16)
    rings = [np.array(plate2d.exterior.coords[:-1]).tolist()]
    stand = Manifold.extrude(CrossSection(rings, FillRule.EvenOdd), PL)
    lip = CL + WALL + 2.5                                           # front lip stops below the Hebrew lettering
    stand += block(tx0 - WT, tx1 + WT, -WT, 0, PL, PL + lip)        # front lip
    stand += block(tx0 - WT, tx1 + WT, ty1, ty1 + WT, PL, PL + lip) # low back wall (clear of the BOOT hole)
    stand += block(tx0 - WT, tx0, -WT, ty1 + WT, PL, PL + 8)        # sides
    stand += block(tx1, tx1 + WT, -WT, ty1 + WT, PL, PL + 8)
    stand += block(62, 138, ty1, ty1 + 4, PL, PL + 34)              # rear buttress behind the battery area
    tri = Manifold.extrude(CrossSection([[[0, 0], [26, 0], [0, 32]]], FillRule.EvenOdd), 4)
    for gx in (62, 98, 134):                                        # gussets: local (u,v,w) -> (Y,Z,X)
        stand += tri.transform([[0, 0, 1, gx], [1, 0, 0, ty1 + 4], [0, 1, 0, PL]])

    return dict(menorah_back_top=top, menorah_back_base=base, menorah_stand=stand), report, dict(
        top_thickness=h_t, base_thickness=h_b, trough=(tx1 - tx0, ty1))


def render(mesh, elev, azim, size=900):
    """Tiny z-buffer renderer (orthographic, Lambert shading): good enough to see what the part looks like."""
    e, a = np.radians(elev), np.radians(azim)
    view = np.array([np.cos(e) * np.cos(a), np.cos(e) * np.sin(a), np.sin(e)])          # from the part towards the eye
    right = np.cross([0, 0, 1], view); right /= np.linalg.norm(right)
    up = np.cross(view, right)
    v = mesh.vertices - mesh.bounds.mean(axis=0)
    p = np.c_[v @ right, v @ up, v @ view]
    scale = (size - 40) / max(np.ptp(p[:, 0]), np.ptp(p[:, 1]))
    w, h = int(np.ptp(p[:, 0]) * scale) + 40, int(np.ptp(p[:, 1]) * scale) + 40
    px = (p[:, 0] - p[:, 0].min()) * scale + 20
    py = (p[:, 1].max() - p[:, 1]) * scale + 20
    img = np.full((h, w, 3), 255, np.uint8)
    zbuf = np.full((h, w), -1e9)
    light = np.array([-0.35, -0.45, 0.82]); light /= np.linalg.norm(light)
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
        img[y0:y1 + 1, x0:x1 + 1][hit] = (np.array([70, 110, 190]) * sh).astype(np.uint8)
    return img


def preview(meshes, path):
    from PIL import Image
    shots = [render(meshes["menorah_back_top"], 50, -100, 1100), render(meshes["menorah_back_base"], 45, -115, 800),
             render(meshes["menorah_stand"], 30, -60, 800)]
    w = max(s.shape[1] for s in shots)
    canvas = np.full((sum(s.shape[0] for s in shots) + 20 * (len(shots) - 1), w, 3), 255, np.uint8)
    y = 0
    for s in shots:
        canvas[y:y + s.shape[0], (w - s.shape[1]) // 2:(w - s.shape[1]) // 2 + s.shape[1]] = s
        y += s.shape[0] + 20
    Image.fromarray(canvas).save(path)


def main():
    solids, report, info = build()
    meshes = {}
    scene = trimesh.Scene()
    xoff = 0.0
    for name, s in solids.items():
        m = to_trimesh(s)
        m.apply_translation(-m.bounds[0])                 # each part starts at the origin, resting on z = 0
        assert m.is_watertight and len(s.decompose()) == 1, (name, len(s.decompose()))
        m.export(os.path.join(OUT, name + ".stl"))
        back = trimesh.load(os.path.join(OUT, name + ".stl"))
        assert back.is_watertight, name + ": exported STL is not a closed solid after vertex merging"
        meshes[name] = m
        placed = m.copy()
        placed.apply_translation([0, xoff, 0])
        scene.add_geometry(placed, node_name=name, geom_name=name)
        xoff += m.extents[1] + 8
        print(f"{name}: {m.extents[0]:.1f} x {m.extents[1]:.1f} x {m.extents[2]:.1f} mm, {m.volume/1000:.1f} cm3, "
              f"{len(m.faces)} triangles, watertight={m.is_watertight}")
    scene.export(os.path.join(OUT, "menorah_enclosure.3mf"))
    preview(meshes, os.path.join(OUT, "preview.png"))
    print("\n".join(report))
    print(info)


if __name__ == "__main__":
    main()

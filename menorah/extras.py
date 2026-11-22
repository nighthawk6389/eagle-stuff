"""Two small bare boards that go with the menorah (separate JLCPCB orders, no assembly):

  foot  80 x 18 mm, 1.6 mm: slot 1.75 x 1.5 mm from the top edge; two of them half-lap into the
        15.5 mm slots in the menorah base.  Both slots end in a semicircle, so each board slides about
        0.35 mm past the nominal depth; with a 1.5 mm slot the feet end up about 0.3 mm below the base
        edge, so the menorah stands on its feet and not on the board.  The foot must
        not reach above y = 134 on the board: J2 (right) and C3/U5 (left) sit just above the slots.
  wand  candle-shaped "shamash" stick with a 5.1 mm hole for a glued 5 x 2 mm disc magnet.

    /usr/bin/python3.12 extras.py     -> out/extras/{foot,wand}.kicad_pcb + gerber zips
"""
import os, shutil, subprocess, zipfile
import pcbnew
from pcbnew import FromMM, VECTOR2I
from shapely.geometry import Point, box
from shapely.ops import unary_union
import geometry as G

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out", "extras")


def V(x, y):
    return VECTOR2I(FromMM(float(x)), FromMM(float(y)))


def make(name, shape, holes=(), label=None):
    board = pcbnew.BOARD()
    rings = [shape.exterior] + list(shape.interiors)
    for ring in rings:
        pts = list(ring.coords)
        for a, b in zip(pts[:-1], pts[1:]):
            s = pcbnew.PCB_SHAPE(board)
            s.SetShape(pcbnew.SHAPE_T_SEGMENT)
            s.SetStart(V(*a)); s.SetEnd(V(*b)); s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(FromMM(0.05))
            board.Add(s)
    for x, y, d in holes:
        c = pcbnew.PCB_SHAPE(board)
        c.SetShape(pcbnew.SHAPE_T_CIRCLE)
        c.SetCenter(V(x, y)); c.SetEnd(V(x + d / 2, y)); c.SetLayer(pcbnew.Edge_Cuts); c.SetWidth(FromMM(0.05))
        board.Add(c)
    if label:
        t = pcbnew.PCB_TEXT(board)
        t.SetText(label[0]); t.SetPosition(V(label[1], label[2])); t.SetLayer(pcbnew.B_SilkS)
        t.SetTextSize(VECTOR2I(FromMM(1.0), FromMM(1.0))); t.SetTextThickness(FromMM(0.15)); t.SetMirrored(True)
        board.Add(t)
    pcb = os.path.join(OUT, name + ".kicad_pcb")
    pcbnew.SaveBoard(pcb, board)
    ger = os.path.join(OUT, name + "_gerber")
    os.makedirs(ger)
    subprocess.run(["kicad-cli", "pcb", "export", "gerbers", "-o", ger + "/", "--layers",
                    "F.Cu,B.Cu,F.Mask,B.Mask,F.SilkS,B.SilkS,Edge.Cuts", pcb], check=True, capture_output=True)
    subprocess.run(["kicad-cli", "pcb", "export", "drill", "-o", ger + "/", "--format", "excellon",
                    "--excellon-units", "mm", pcb], check=True, capture_output=True)
    with zipfile.ZipFile(os.path.join(OUT, name + "-gerbers.zip"), "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(os.listdir(ger)):
            if not f.endswith(".gbrjob"):
                z.write(os.path.join(ger, f), f)
    shutil.rmtree(ger)
    print(name, [round(v, 2) for v in shape.bounds])


def main():
    shutil.rmtree(OUT, ignore_errors=True)
    os.makedirs(OUT)
    # ---- foot: 80 x 18, slot from the top in the middle
    w, h, sw, sd = 80.0, 18.0, G.FOOT_SLOT_W, 1.5
    body = box(0, 0, w, h).buffer(-3).buffer(3, 16)
    slot = unary_union([box(w / 2 - sw / 2, -1, w / 2 + sw / 2, sd), Point(w / 2, sd).buffer(sw / 2, 16)])
    make("foot", body.difference(slot).simplify(0.01), label=("Menorah v1 foot", w / 2, 12.0))
    # ---- wand: 10 mm wide stick with a flame-shaped tip; magnet hole near the tip
    drop, neck, (cx, cy) = G.flame(5.0, 22.0)
    stick = box(0, 22.0, 10.0, 95.0).buffer(-2).buffer(2, 16)
    shape = unary_union([stick, drop, neck]).buffer(1.2, 12).buffer(-1.2, 12)
    make("wand", shape.simplify(0.01), holes=[(cx, cy, 5.1)], label=("shamash", 5.0, 60.0))


if __name__ == "__main__":
    main()

#!/usr/bin/python3
"""Finish the routed board: ground pours on the outer layers, silkscreen, refill.

    /usr/bin/python3 gen/finish.py

Works on pod/emg-pod.kicad_pcb in place (run after gen/route.py).
"""
import os
import sys

import pcbnew
from pcbnew import FromMM, VECTOR2I

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import board as B  # noqa: E402

PCB = sys.argv[1] if len(sys.argv) > 1 else os.path.join(B.POD, "emg-pod.kicad_pcb")
KEEP_REF = ("U", "J")            # references left on the silkscreen; the rest are on the fab layer only


def main():
    brd = pcbnew.LoadBoard(PCB)
    gnd = brd.FindNet("GND")
    # outer-layer ground pours
    names = {z.GetZoneName() for z in brd.Zones()}
    for layer, name in ((pcbnew.F_Cu, "top ground pour"), (pcbnew.B_Cu, "bottom ground pour")):
        if name in names:
            continue
        z = pcbnew.ZONE(brd)
        z.SetLayer(layer)
        z.SetNet(gnd)
        z.SetZoneName(name)
        o = z.Outline()
        o.NewOutline()
        for x, y in [(0, 0), (B.W, 0), (B.W, B.H), (0, B.H)]:
            o.Append(FromMM(B.OX + x), FromMM(B.OY + y))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
        z.SetLocalClearance(FromMM(0.2))
        z.SetMinThickness(FromMM(0.2))
        z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
        brd.Add(z)
    # silkscreen: only a few references, plus labels a person needs with the board in hand
    for fp in brd.GetFootprints():
        ref = fp.GetReference()
        t = fp.Reference()
        if ref.startswith(KEEP_REF) and not ref.startswith(("U10", "U20")) or ref in ("U100", "U200"):
            t.SetVisible(True)
        else:
            t.SetVisible(False)
        t.SetTextSize(VECTOR2I(FromMM(0.8), FromMM(0.8)))
        t.SetTextThickness(FromMM(0.13))
    for d in list(brd.GetDrawings()):
        if d.GetLayer() == pcbnew.F_SilkS and isinstance(d, pcbnew.PCB_TEXT):
            brd.Remove(d)

    def text(s, x, y, size=1.0, layer=pcbnew.F_SilkS):
        t = pcbnew.PCB_TEXT(brd)
        t.SetText(s)
        t.SetPosition(B.V(x, y))
        t.SetLayer(layer)
        t.SetTextSize(VECTOR2I(FromMM(size), FromMM(size)))
        t.SetTextThickness(FromMM(size * 0.15))
        brd.Add(t)

    text("EMG POD", B.W / 2, 43.0, 1.2)
    text("rev A", B.W / 2, 45.0, 1.0)
    text("A", B.W / 2 - 3.4, 47.2, 1.3)
    text("B", B.W / 2 + 3.4, 47.2, 1.3)
    text("BAT", 6.0, 12.3, 0.9)
    text("+", 7.0, 11.0, 1.0)
    text("-", 5.0, 11.0, 1.0)
    text("MOTOR", 14.9, 0.9, 0.8)
    for v in [x for x in brd.GetTracks() if isinstance(x, pcbnew.PCB_VIA) and x.GetNetname() == "GND"
              and not x.IsLocked()]:
        brd.Remove(v)                                   # stitching vias from an earlier run
    pcbnew.ZONE_FILLER(brd).Fill(brd.Zones())
    n = stitch(brd)
    pcbnew.ZONE_FILLER(brd).Fill(brd.Zones())
    pcbnew.SaveBoard(PCB, brd)
    print("ground stitching vias:", n)
    return 0


def islands(zone, layer, shrink):
    """Each filled island of a zone as its own polygon set, shrunk by `shrink` mm."""
    polys = zone.GetFilledPolysList(layer)
    out = []
    for i in range(polys.OutlineCount()):
        s = pcbnew.SHAPE_POLY_SET()
        s.AddOutline(polys.Outline(i))
        for h in range(polys.HoleCount(i)):
            s.AddHole(polys.Hole(i, h))
        s.Deflate(FromMM(shrink), pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS, FromMM(0.01))
        if s.OutlineCount():
            out.append(s)
    return out


def stitch(brd, spacing=3.0):
    """Join the outer ground pours to the planes: at least one via in every island that has room."""
    zones = {z.GetZoneName(): z for z in brd.Zones()}
    need = B.VIA_D / 2 + 0.03
    top = islands(zones["top ground pour"], pcbnew.F_Cu, need)
    bot = islands(zones["bottom ground pour"], pcbnew.B_Cu, need)
    pads = []
    for fp in brd.GetFootprints():
        for pad in fp.Pads():
            bb = pad.GetBoundingBox()
            bb.Inflate(FromMM(B.VIA_D / 2 + 0.15))
            pads.append(bb)
    gnd = brd.FindNet("GND")
    placed = []
    step = 0.25
    nx, ny = int(B.W / step), int(B.H / step)

    def free(pt):
        return not any(bb.Contains(pt) for bb in pads)

    def far(x, y, d):
        return all((x - a) ** 2 + (y - b) ** 2 >= d * d for a, b in placed)

    count = 0
    for layer_islands, other in ((top, bot), (bot, top)):
        for isl in layer_islands:
            bb = isl.BBox()
            got = 0
            for d in (spacing, 0.9):                     # second round only if the island got none
                if d != spacing and got:
                    break
                for iy in range(ny):
                    y = iy * step
                    if not (bb.GetTop() <= FromMM(B.OY + y) <= bb.GetBottom()):
                        continue
                    for ix in range(nx):
                        x = ix * step
                        pt = B.V(x, y)
                        if not bb.Contains(pt) or not isl.Contains(pt) or not far(x, y, d) or not free(pt):
                            continue
                        if not any(o.Contains(pt) for o in other):
                            continue
                        v = pcbnew.PCB_VIA(brd)
                        v.SetPosition(pt)
                        v.SetViaType(pcbnew.VIATYPE_THROUGH)
                        v.SetWidth(pcbnew.F_Cu, FromMM(B.VIA_D))
                        v.SetDrill(FromMM(B.VIA_DRILL))
                        v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
                        v.SetNet(gnd)
                        brd.Add(v)
                        placed.append((x, y))
                        got += 1
                        count += 1
                        if d != spacing:
                            break                        # one via is enough for a small island
                    if d != spacing and got:
                        break
    return count


if __name__ == "__main__":
    sys.exit(main())

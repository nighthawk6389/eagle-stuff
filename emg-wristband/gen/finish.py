#!/usr/bin/python3
"""Finish the routed board: ground pours on the outer layers, silkscreen, refill.

    /usr/bin/python3 gen/finish.py

Reads out/route/routed.kicad_pcb (from gen/route.py) and writes pod/emg-pod.kicad_pcb.
"""
import math
import os
import shutil
import sys

import pcbnew
from pcbnew import FromMM, VECTOR2I

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import board as B  # noqa: E402

RAW = sys.argv[1] if len(sys.argv) > 1 else os.path.join(B.ROOT, "out", "route", "routed.kicad_pcb")
PCB = sys.argv[2] if len(sys.argv) > 2 else os.path.join(B.POD, "emg-pod.kicad_pcb")
KEEP_REF = ("U", "J")            # references left on the silkscreen; the rest are on the fab layer only


def main():
    shutil.copy(RAW.replace('.kicad_pcb', '.kicad_pro'), PCB.replace('.kicad_pcb', '.kicad_pro'))
    brd = pcbnew.LoadBoard(RAW)
    links = link_neighbours(brd, "GND")
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
        z.SetLocalClearance(FromMM(0.15))
        z.SetMinThickness(FromMM(0.15))
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
    pcbnew.ZONE_FILLER(brd).Fill(brd.Zones())
    a = plane_vias(brd, "AVDD", (1.5, 23.0, B.W - 1.5, B.H - 1.5))
    pcbnew.ZONE_FILLER(brd).Fill(brd.Zones())
    n = stitch(brd)
    pcbnew.ZONE_FILLER(brd).Fill(brd.Zones())
    pcbnew.SaveBoard(PCB, brd)
    print("ground links", links, "| vias added: AVDD", a, "ground", n)
    return 0


def islands(zone, layer, shrink):
    """Each filled island of a zone as (shrunk polygon set, full polygon set)."""
    polys = zone.GetFilledPolysList(layer)
    out = []
    for i in range(polys.OutlineCount()):
        s = pcbnew.SHAPE_POLY_SET()
        s.AddOutline(polys.Outline(i))
        for h in range(polys.HoleCount(i)):
            s.AddHole(polys.Hole(i, h))
        full = pcbnew.SHAPE_POLY_SET(s)
        s.Deflate(FromMM(shrink), pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS, FromMM(0.01))
        out.append((s, full))
    return out


def add_via(brd, pt, net):
    v = pcbnew.PCB_VIA(brd)
    v.SetPosition(pt)
    v.SetViaType(pcbnew.VIATYPE_THROUGH)
    v.SetWidth(pcbnew.F_Cu, FromMM(B.VIA_D))
    v.SetDrill(FromMM(B.VIA_DRILL))
    v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    v.SetNet(net)
    brd.Add(v)
    return v


class Space:
    """Where a via or a short track of one net may go without coming too close to other copper."""

    def __init__(self, brd, netname):
        self.brd, self.netname, self.net = brd, netname, brd.FindNet(netname)
        self.via_no = {lay: self._others(lay, B.CLEAR + B.VIA_D / 2 + 0.02) for lay in (pcbnew.F_Cu, pcbnew.B_Cu)}
        self.track_no = self._others(pcbnew.F_Cu, B.CLEAR + 0.1 + 0.02)
        self.pads_no = pcbnew.SHAPE_POLY_SET()           # no via on or touching any pad
        for fp in brd.GetFootprints():
            for pad in fp.Pads():
                for lay in (pcbnew.F_Cu, pcbnew.B_Cu):
                    if pad.IsOnLayer(lay):
                        pad.TransformShapeToPolygon(self.pads_no, lay, FromMM(B.VIA_D / 2 + 0.1), FromMM(0.01),
                                                    pcbnew.ERROR_OUTSIDE)
        self.pads_no.Simplify()
        self.holes = [(v.GetPosition().x, v.GetPosition().y) for v in brd.GetTracks() if isinstance(v, pcbnew.PCB_VIA)]

    def _others(self, layer, margin):
        ps = pcbnew.SHAPE_POLY_SET()
        for t in self.brd.GetTracks():
            if t.GetNetname() == self.netname:
                continue
            if isinstance(t, pcbnew.PCB_VIA) or t.GetLayer() == layer:
                t.TransformShapeToPolygon(ps, layer, FromMM(margin), FromMM(0.01), pcbnew.ERROR_OUTSIDE)
        for fp in self.brd.GetFootprints():
            for pad in fp.Pads():
                if pad.GetNetname() != self.netname and pad.IsOnLayer(layer):
                    pad.TransformShapeToPolygon(ps, layer, FromMM(margin), FromMM(0.01), pcbnew.ERROR_OUTSIDE)
        for z in self.brd.Zones():
            if z.GetIsRuleArea():
                for i in range(z.Outline().OutlineCount()):
                    ps.AddOutline(z.Outline().Outline(i))
        ps.Simplify()
        return ps

    def via_ok(self, x, y):
        """x, y in board millimetres."""
        e = B.VIA_D / 2 + 0.35
        if not (e <= x <= B.W - e and e <= y <= B.H - e):
            return False
        pt = B.V(x, y)
        if self.via_no[pcbnew.F_Cu].Contains(pt) or self.via_no[pcbnew.B_Cu].Contains(pt) or self.pads_no.Contains(pt):
            return False
        lim = FromMM(B.VIA_DRILL + 0.27) ** 2
        return all((pt.x - hx) ** 2 + (pt.y - hy) ** 2 >= lim for hx, hy in self.holes)

    def track_ok(self, a, b):
        n = max(2, int(math.hypot(b[0] - a[0], b[1] - a[1]) / 0.05))
        return not any(self.track_no.Contains(B.V(a[0] + (b[0] - a[0]) * i / n, a[1] + (b[1] - a[1]) * i / n))
                       for i in range(n + 1))

    def rescue(self, pad, reach=2.6):
        """Give one pad its own via to the plane, with a short track. True if it fitted."""
        p = pad.GetPosition()
        px, py = pcbnew.ToMM(p.x) - B.OX, pcbnew.ToMM(p.y) - B.OY
        r = 0.45
        while r <= reach:
            for k in range(24):
                x, y = px + r * math.cos(k * math.pi / 12), py + r * math.sin(k * math.pi / 12)
                if self.via_ok(x, y) and self.track_ok((px, py), (x, y)):
                    v = add_via(self.brd, B.V(x, y), self.net)
                    self.holes.append((v.GetPosition().x, v.GetPosition().y))
                    t = pcbnew.PCB_TRACK(self.brd)
                    t.SetStart(p)
                    t.SetEnd(B.V(x, y))
                    t.SetWidth(FromMM(0.2))
                    t.SetLayer(pcbnew.F_Cu)
                    t.SetNet(self.net)
                    self.brd.Add(t)
                    return True
            r += 0.15
        return False


def link_neighbours(brd, netname, reach=1.7):
    """Short tracks between pads of one net that sit next to each other (capacitors in a column, for example)."""
    space = Space(brd, netname)
    pads = [pad for fp in brd.GetFootprints() for pad in fp.Pads()
            if pad.GetNetname() == netname and pad.IsOnLayer(pcbnew.F_Cu) and pad.GetAttribute() == pcbnew.PAD_ATTRIB_SMD]
    xy = [(pcbnew.ToMM(p.GetPosition().x) - B.OX, pcbnew.ToMM(p.GetPosition().y) - B.OY) for p in pads]
    n = 0
    for i in range(len(pads)):
        for j in range(i + 1, len(pads)):
            if pads[i].GetParentFootprint() == pads[j].GetParentFootprint():
                continue
            d = math.hypot(xy[i][0] - xy[j][0], xy[i][1] - xy[j][1])
            if d <= reach and space.track_ok(xy[i], xy[j]):
                t = pcbnew.PCB_TRACK(brd)
                t.SetStart(pads[i].GetPosition())
                t.SetEnd(pads[j].GetPosition())
                t.SetWidth(FromMM(0.2))
                t.SetLayer(pcbnew.F_Cu)
                t.SetNet(space.net)
                brd.Add(t)
                n += 1
    return n


def stitch(brd, spacing=3.0):
    """Join the outer ground pours to the planes: at least one via in every island that has room."""
    zones = {z.GetZoneName(): z for z in brd.Zones()}
    need = B.VIA_D / 2 - 0.02          # the pour keeps 0.15 from other copper, a via needs only 0.127
    top = islands(zones["top ground pour"], pcbnew.F_Cu, need)
    bot = islands(zones["bottom ground pour"], pcbnew.B_Cu, need)
    space = Space(brd, "GND")
    gnd = space.net
    placed = []
    step = 0.25
    nx, ny = int(B.W / step), int(B.H / step)

    def far(x, y, d):
        return all((x - a) ** 2 + (y - b) ** 2 >= d * d for a, b in placed)

    count, starved = 0, []
    for layer_islands, other in ((top, bot), (bot, top)):
        for isl, full in layer_islands:
            got = 0
            if isl.OutlineCount():
                bb = isl.BBox()
                for d in (spacing, 0.9):                     # second round only if the island got none
                    if got:
                        break
                    for iy in range(ny):
                        y = iy * step
                        if not (bb.GetTop() <= FromMM(B.OY + y) <= bb.GetBottom()):
                            continue
                        for ix in range(nx):
                            x = ix * step
                            pt = B.V(x, y)
                            if not bb.Contains(pt) or not isl.Contains(pt) or not far(x, y, d):
                                continue
                            if not any(o.Contains(pt) for o, _ in other) or not space.via_ok(x, y):
                                continue
                            add_via(brd, pt, gnd)
                            space.holes.append((pt.x, pt.y))
                            placed.append((x, y))
                            got += 1
                            count += 1
                            if d != spacing:
                                break                        # one via is enough for a small island
                        if d != spacing and got:
                            break
            if not got and layer_islands is top:
                starved.append(full)
    # top islands with no room for a via of their own: give one of their pads a via beside the island
    lost = []
    for full in starved:
        pads = [pad for fp in brd.GetFootprints() for pad in fp.Pads()
                if pad.GetNetname() == "GND" and pad.IsOnLayer(pcbnew.F_Cu) and full.Contains(pad.GetPosition())]
        if pads and not any(space.rescue(pad) for pad in pads):
            lost.append(pads[0].GetParentFootprint().GetReference() + "." + pads[0].GetNumber())
        count += bool(pads)
    if lost:
        print("ground pads with no room for a via:", ", ".join(lost))
    return count


def plane_vias(brd, netname, box):
    """A via to the plane beside every pad of this net inside box that has none close by."""
    space = Space(brd, netname)
    vias = [v.GetPosition() for v in brd.GetTracks() if isinstance(v, pcbnew.PCB_VIA) and v.GetNetname() == netname]
    n = 0
    for fp in brd.GetFootprints():
        for pad in fp.Pads():
            if pad.GetNetname() != netname or not pad.IsOnLayer(pcbnew.F_Cu):
                continue
            p = pad.GetPosition()
            x, y = pcbnew.ToMM(p.x) - B.OX, pcbnew.ToMM(p.y) - B.OY
            if not (box[0] <= x <= box[2] and box[1] <= y <= box[3]):
                continue
            if any((p.x - q.x) ** 2 + (p.y - q.y) ** 2 < FromMM(1.3) ** 2 for q in vias):
                continue
            if space.rescue(pad, 1.4):
                vias.append(p)
                n += 1
    return n


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/python3
"""Finish the routed board: complete leftovers, pour ground, tie planes, silkscreen.

    /usr/bin/python3 gen/finish.py

Reads out/route/routed.kicad_pcb (from gen/route.py) and writes pod/emg-pod.kicad_pcb.
"""
import json
import math
import os
import re
import shutil
import subprocess
import sys

import pcbnew
from pcbnew import FromMM, VECTOR2I

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import board as B  # noqa: E402
import lastmile as L  # noqa: E402

RAW = sys.argv[1] if len(sys.argv) > 1 else os.path.join(B.ROOT, "out", "route", "routed.kicad_pcb")
PCB = sys.argv[2] if len(sys.argv) > 2 else os.path.join(B.POD, "emg-pod.kicad_pcb")
PLANES = ("GND", "AVDD", "+3V3")
KEEP_REF = ("U100", "U200", "U1", "U2", "J1", "J2", "J100", "J200")


def mm(p):
    return pcbnew.ToMM(p.x) - B.OX, pcbnew.ToMM(p.y) - B.OY


def unconnected(brd):
    """What KiCad's DRC reports as unconnected: [(net, (x, y, layer), (x, y, layer))]. Layer None = either."""
    tmp = PCB + ".check.kicad_pcb"
    pcbnew.SaveBoard(tmp, brd)
    shutil.copy(PCB.replace(".kicad_pcb", ".kicad_pro"), tmp.replace(".kicad_pcb", ".kicad_pro"))
    rep = tmp + ".json"
    subprocess.run(["kicad-cli", "pcb", "drc", "--severity-error", "--format", "json", "-o", rep, tmp],
                   capture_output=True)
    data = json.load(open(rep))
    for f in (tmp, rep, tmp.replace(".kicad_pcb", ".kicad_pro"), tmp.replace(".kicad_pcb", ".kicad_prl")):
        if os.path.exists(f):
            os.remove(f)
    out = []
    for u in data.get("unconnected_items", []):
        ends = []
        for it in u["items"]:
            d = it["description"]
            net = re.search(r"\[([^\]]+)\]", d)
            if d.startswith("Zone") or not net:
                ends = []
                break
            lay = None if (d.startswith("Via") or "F.Cu - B.Cu" in d) else (L.F if "on F.Cu" in d else L.BK)
            ends.append((net.group(1), (it["pos"]["x"] - B.OX, it["pos"]["y"] - B.OY, lay)))
        if len(ends) == 2 and ends[0][0] == ends[1][0]:
            out.append((ends[0][0], ends[0][1], ends[1][1]))
    return out, len(data.get("unconnected_items", [])), len(data.get("violations", []))


def complete_signals(brd, skip=PLANES):
    """Route the connections the autorouter gave up on."""
    done = 0
    for _ in range(3):
        todo = [u for u in unconnected(brd)[0] if u[0] not in skip]
        if not todo:
            break
        progress = 0
        for net, a, b in todo:
            space = L.Space(brd, net, B.TRACK)
            short = math.hypot(a[0] - b[0], a[1] - b[1]) < 4.0
            kw = dict(margin=3.0, step=0.05) if short else dict(margin=6.0)
            start = (a[0], a[1], a[2] if a[2] is not None else L.F)
            res = L.maze(space, start, b, **kw)
            if res is None and a[2] is None:
                start = (a[0], a[1], L.BK)
                res = L.maze(space, start, b, **kw)
            if res:
                L.lay_down(space, start, res, b)
                progress += 1
        done += progress
        if not progress:
            break
    return done


def link_neighbours(brd, netname, reach=1.7):
    """Short tracks between pads of one net that sit next to each other (capacitors in a column, for example)."""
    space = L.Space(brd, netname)
    pads = [pad for fp in brd.GetFootprints() for pad in fp.Pads()
            if pad.GetNetname() == netname and pad.IsOnLayer(L.F) and pad.GetAttribute() == pcbnew.PAD_ATTRIB_SMD]
    xy = [mm(p.GetPosition()) for p in pads]
    n = 0
    for i in range(len(pads)):
        for j in range(i + 1, len(pads)):
            if pads[i].GetParentFootprint().GetReference() == pads[j].GetParentFootprint().GetReference():
                continue
            if math.hypot(xy[i][0] - xy[j][0], xy[i][1] - xy[j][1]) <= reach and space.track_ok(xy[i], xy[j]):
                L.add_track(brd, xy[i], xy[j], space.net, L.F, 0.2)
                n += 1
    return n


def to_plane(space, pad):
    """Give a pad a short track to a via that reaches its plane. True if it fitted."""
    x, y = mm(pad.GetPosition())
    res = L.maze(space, (x, y, L.F), None, margin=6.0)
    if res is None:
        return False
    L.lay_down(space, (x, y, L.F), res)
    return True


def plane_vias(brd, netname, box):
    """A via to the plane for every pad of this net inside box that has none within 1.3 mm."""
    space = L.Space(brd, netname)
    vias = [v.GetPosition() for v in brd.GetTracks() if isinstance(v, pcbnew.PCB_VIA) and v.GetNetname() == netname]
    n = 0
    for fp in brd.GetFootprints():
        for pad in fp.Pads():
            if pad.GetNetname() != netname or not pad.IsOnLayer(L.F):
                continue
            p = pad.GetPosition()
            x, y = mm(p)
            if not (box[0] <= x <= box[2] and box[1] <= y <= box[3]):
                continue
            if any((p.x - q.x) ** 2 + (p.y - q.y) ** 2 < FromMM(1.3) ** 2 for q in vias):
                continue
            if to_plane(space, pad):
                vias.append(p)
                n += 1
    return n


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


def stitch(brd, spacing=3.0):
    """Join the outer ground pours to the planes: at least one via in every island."""
    zones = {z.GetZoneName(): z for z in brd.Zones()}
    need = B.VIA_D / 2 - 0.02          # the pour keeps 0.15 from other copper, a via needs only 0.127
    top = islands(zones["top ground pour"], L.F, need)
    bot = islands(zones["bottom ground pour"], L.BK, need)
    space = L.Space(brd, "GND")
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
                            L.add_via(brd, pt, space.net)
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
    # top islands with no room for a via of their own: lead one of their pads to a via nearby
    lost = []
    for full in starved:
        pads = [pad for fp in brd.GetFootprints() for pad in fp.Pads()
                if pad.GetNetname() == "GND" and pad.IsOnLayer(L.F) and full.Contains(pad.GetPosition())]
        if pads and not any(to_plane(space, pad) for pad in pads):
            lost.append(pads[0].GetParentFootprint().GetReference() + "." + pads[0].GetNumber())
        count += bool(pads)
    if lost:
        print("ground pads with no room for a via:", ", ".join(lost))
    return count


def silkscreen(brd):
    """Only a few references, plus the labels a person needs with the board in hand."""
    for fp in brd.GetFootprints():
        t = fp.Reference()
        t.SetVisible(fp.GetReference() in KEEP_REF)
        t.SetTextSize(VECTOR2I(FromMM(0.8), FromMM(0.8)))
        t.SetTextThickness(FromMM(0.13))

    def text(s, x, y, size=1.0):
        t = pcbnew.PCB_TEXT(brd)
        t.SetText(s)
        t.SetPosition(B.V(x, y))
        t.SetLayer(pcbnew.F_SilkS)
        t.SetTextSize(VECTOR2I(FromMM(size), FromMM(size)))
        t.SetTextThickness(FromMM(size * 0.15))
        brd.Add(t)

    text("EMG POD rev A", B.W / 2, 41.3, 0.9)
    text("A", B.BX["A"], 41.0, 1.2)
    text("B", B.BX["B"], 41.0, 1.2)
    text("BAT", 6.0, 12.4, 0.9)
    text("+", 7.0, 11.1, 1.0)
    text("-", 5.0, 11.1, 1.0)
    text("MOTOR", 14.9, 0.8, 0.7)


def ground_pours(brd):
    gnd = brd.FindNet("GND")
    for layer, name in ((L.F, "top ground pour"), (L.BK, "bottom ground pour")):
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


def main():
    shutil.copy(RAW.replace(".kicad_pcb", ".kicad_pro"), PCB.replace(".kicad_pcb", ".kicad_pro"))
    brd = pcbnew.LoadBoard(RAW)
    sig = complete_signals(brd)
    links = link_neighbours(brd, "GND")
    ground_pours(brd)
    filler = pcbnew.ZONE_FILLER(brd)
    filler.Fill(brd.Zones())
    avdd = plane_vias(brd, "AVDD", (1.5, B.SPLIT_Y + 0.6, B.W - 1.5, B.H - 1.5))
    avdd += plane_vias(brd, "+3V3", (1.5, 1.5, B.W - 1.5, B.SPLIT_Y - 0.6))
    filler.Fill(brd.Zones())
    gnd = stitch(brd)
    filler.Fill(brd.Zones())
    sig += complete_signals(brd, skip=())             # whatever is still open, plane nets included
    filler.Fill(brd.Zones())
    silkscreen(brd)
    pcbnew.SaveBoard(PCB, brd)
    left, total, viol = unconnected(brd)
    print(f"completed by the last-mile router: {sig} signal connections | ground links {links} | vias added: "
          f"supplies {avdd}, ground {gnd}")
    print(f"DRC: {viol} violations, {total} unconnected")
    for net, a, b in left:
        print(f"   still open: {net} ({a[0]:.1f}, {a[1]:.1f}) to ({b[0]:.1f}, {b[1]:.1f})")
    return 0


if __name__ == "__main__":
    sys.exit(main())

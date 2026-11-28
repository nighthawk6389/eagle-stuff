#!/usr/bin/python3
"""The assembly frame: the finished pod board held in a 74 x 74 mm frame by break-off tabs.

    /usr/bin/python3 gen/panel.py

JLCPCB's Standard assembly takes nothing smaller than 70 x 70 mm and wants rails and fiducials
(docs/sources.md); the frame is 4 mm larger than that so the limit is not met with nothing to spare. Reads pod/emg-pod.kicad_pcb and writes pod/emg-pod-panel.kicad_pcb, the files for
ordering in out/fab-panel/, a DRC report and a picture. The board is not moved, its copper is not touched
and its zones are not refilled, so what was checked on the single board is what is in the frame, and the
placement file has the same coordinates.

The board's outline stays as drawn except where a tab joins it; there the edge line is left out, and a row
of small holes just outside the edge lets the tab be cut off.
"""
import json
import math
import os
import shutil
import subprocess
import sys

import pcbnew
from pcbnew import FromMM, ToMM

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import board as B  # noqa: E402
import fab  # noqa: E402

SRC = os.path.join(B.POD, "emg-pod.kicad_pcb")
PANEL = os.path.join(B.POD, "emg-pod-panel.kicad_pcb")
OUT = os.path.join(B.ROOT, "out", "fab-panel")

SIZE = 74.0                      # outer size of the frame: JLCPCB's minimum for Standard assembly is 70
GAP = 2.0                        # routed slot between board and frame
GAP_USB = 3.0                    # wider on the right, where the XIAO's USB socket overhangs the board
TAB = 5.0                        # width of a tab
BITE, WEB, END = 0.5, 0.3, 0.25  # perforation diameter, web between two holes, web between the last hole and the slot
# Tabs: (edge, from, to) in board mm. Kept away from the ceramic capacitors that stand 1.35 mm from the left and
# right edges below y = 26, from the XIAO, and from the strip connectors' mouths on the bottom edge.
TABS = [("top", 15.5, 20.5), ("right", 19.0, 24.0), ("bottom", 22.0, 27.0), ("left", 17.5, 22.5), ("left", 9.0, 14.0)]
FID = 3.85                       # centres of fiducials and tooling holes from the panel edges
TEXT_CLEAR = 3.0                 # the frame's text stays this far from the centre of every fiducial and tooling hole
EDGE_BACK = 0.3                  # copper stays this far inside the board edge (board.py's edge clearance)
EDGE_W = 0.15                    # line width JLCPCB's ordering notes suggest for outline, slots and cut-outs

# the frame's inner edge, in board mm
FX0, FY0, FX1, FY1 = -GAP, -GAP, B.W + GAP_USB, B.H + GAP
# the panel's outer edge, in board mm: what is left of 70 mm is shared between the two rails of each pair
PX0 = FX0 - (SIZE - (FX1 - FX0)) / 2
PY0 = FY0 - (SIZE - (FY1 - FY0)) / 2
PX1, PY1 = PX0 + SIZE, PY0 + SIZE

# for each edge: its fixed coordinate on the board, the same on the frame, whether it runs along x, the way out
EDGES = {"top": (0.0, FY0, True, (0, -1)), "bottom": (B.H, FY1, True, (0, 1)),
         "left": (0.0, FX0, False, (-1, 0)), "right": (B.W, FX1, False, (1, 0))}


def at(edge, t, on_frame=False):
    """The point at t along an edge, on the board or opposite it on the frame."""
    on_board, frame, along_x, _ = EDGES[edge]
    c = frame if on_frame else on_board
    return (t, c) if along_x else (c, t)


def without_tabs(edge, lo, hi):
    """The stretches of [lo, hi] along an edge that no tab covers, and how many tabs fell inside."""
    cuts = sorted((t0, t1) for e, t0, t1 in TABS if e == edge and lo - 1e-6 <= t0 and t1 <= hi + 1e-6)
    out, t = [], lo
    for t0, t1 in cuts:
        out.append((t, t0))
        t = t1
    out.append((t, hi))
    return out, len(cuts)


def copper(path):
    """Everything conductive on a board file that belongs to the pod: tracks, vias, pads with their nets, and the
    filled area of every zone on every layer."""
    brd = pcbnew.LoadBoard(path)
    items = set()
    for t in brd.GetTracks():
        via = t.Type() == pcbnew.PCB_VIA_T
        items.add((t.GetClass(), t.GetLayerName(), t.GetStart().x, t.GetStart().y, t.GetEnd().x, t.GetEnd().y,
                   t.GetWidth(pcbnew.F_Cu) if via else t.GetWidth(), t.GetDrillValue() if via else 0, t.GetNetname()))
    for fp in brd.GetFootprints():
        if fp.GetReference().startswith(("MB", "H", "FID")):
            continue
        for pad in fp.Pads():
            items.add((fp.GetReference(), pad.GetNumber(), pad.GetPosition().x, pad.GetPosition().y, pad.GetNetname()))
    for z in brd.Zones():
        if z.GetIsRuleArea():
            continue
        for layer in z.GetLayerSet().Seq():
            polys = z.GetFilledPolysList(layer)
            items.add((z.GetZoneName(), brd.GetLayerName(layer), polys.OutlineCount(), round(polys.Area())))
    return items


def main():
    shutil.copy(SRC.replace(".kicad_pcb", ".kicad_pro"), PANEL.replace(".kicad_pcb", ".kicad_pro"))
    brd = pcbnew.LoadBoard(SRC)

    def line(a, b):
        s = pcbnew.PCB_SHAPE(brd)
        s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(B.V(*a))
        s.SetEnd(B.V(*b))
        s.SetLayer(pcbnew.Edge_Cuts)
        s.SetWidth(FromMM(EDGE_W))
        brd.Add(s)

    def hole(x, y, dia, ref):
        fp = pcbnew.FOOTPRINT(brd)
        fp.SetReference(ref)
        fp.Reference().SetVisible(False)
        fp.Value().SetVisible(False)
        fp.SetPosition(B.V(x, y))
        fp.SetAttributes(pcbnew.FP_EXCLUDE_FROM_BOM | pcbnew.FP_EXCLUDE_FROM_POS_FILES | pcbnew.FP_BOARD_ONLY)
        pad = pcbnew.PAD(fp)
        pad.SetNumber("")
        pad.SetAttribute(pcbnew.PAD_ATTRIB_NPTH)
        pad.SetShape(pcbnew.F_Cu, pcbnew.PAD_SHAPE_CIRCLE)
        pad.SetSize(pcbnew.F_Cu, pcbnew.VECTOR2I(FromMM(dia), FromMM(dia)))
        pad.SetDrillSize(pcbnew.VECTOR2I(FromMM(dia), FromMM(dia)))
        pad.SetLayerSet(pcbnew.PAD.UnplatedHoleMask())
        pad.SetPosition(B.V(x, y))
        fp.Add(pad)
        brd.Add(fp)

    # ---- the board's own edge: straight stretches lose the part a tab joins, everything else stays
    used = 0
    for d in list(brd.GetDrawings()):
        if d.GetLayer() != pcbnew.Edge_Cuts or d.GetShape() != pcbnew.SHAPE_T_SEGMENT:
            continue
        (x0, y0), (x1, y1) = [(ToMM(p.x) - B.OX, ToMM(p.y) - B.OY) for p in (d.GetStart(), d.GetEnd())]
        for name, (c, _, along_x, _) in EDGES.items():
            if along_x and abs(y0 - c) < 1e-6 and abs(y1 - c) < 1e-6:
                lo, hi = sorted((x0, x1))
            elif not along_x and abs(x0 - c) < 1e-6 and abs(x1 - c) < 1e-6:
                lo, hi = sorted((y0, y1))
            else:
                continue
            parts, n = without_tabs(name, lo, hi)
            if n:
                used += n
                brd.Delete(d)
                for t0, t1 in parts:
                    line(at(name, t0), at(name, t1))
            break
    assert used == len(TABS), f"{used} of {len(TABS)} tabs lie on a straight stretch of the board edge"
    for d in brd.GetDrawings():
        if d.GetLayer() == pcbnew.Edge_Cuts:
            d.SetWidth(FromMM(EDGE_W))

    # ---- the frame: inner edge with the same gaps, the two sides of each tab, outer edge
    for name, (lo, hi) in (("top", (FX0, FX1)), ("bottom", (FX0, FX1)), ("left", (FY0, FY1)), ("right", (FY0, FY1))):
        for t0, t1 in without_tabs(name, lo, hi)[0]:
            line(at(name, t0, True), at(name, t1, True))
    for name, t0, t1 in TABS:
        assert abs((t1 - t0) - TAB) < 1e-6, (name, t0, t1)
        for t in (t0, t1):
            line(at(name, t), at(name, t, True))
    for a, b in (((PX0, PY0), (PX1, PY0)), ((PX1, PY0), (PX1, PY1)), ((PX1, PY1), (PX0, PY1)), ((PX0, PY1), (PX0, PY0))):
        line(a, b)

    # ---- perforations across each tab, touching the board edge from outside, so the board's own edge stays whole
    pitch = BITE + WEB
    per_tab = int((TAB - 2 * END - BITE) / pitch + 1e-6) + 1
    n = 0
    for name, t0, t1 in TABS:
        ox, oy = EDGES[name][3]
        for i in range(per_tab):
            x, y = at(name, (t0 + t1) / 2 + (i - (per_tab - 1) / 2) * pitch)
            n += 1
            hole(x + ox * BITE / 2, y + oy * BITE / 2, BITE, f"MB{n}")

    # ---- no pour may grow into a tab if somebody refills the zones in this file
    for k, (name, t0, t1) in enumerate(TABS):
        ox, oy = EDGES[name][3]
        (ax, ay), (bx, by) = at(name, t0 - 0.5), at(name, t1 + 0.5)
        (cx, cy), (dx, dy) = at(name, t1 + 0.5, True), at(name, t0 - 0.5, True)
        z = pcbnew.ZONE(brd)
        z.SetIsRuleArea(True)
        z.SetZoneName(f"tab {k + 1}")
        z.SetLayerSet(pcbnew.LSET.AllCuMask(4))
        z.SetDoNotAllowCopperPour(True)
        z.SetDoNotAllowTracks(False)
        z.SetDoNotAllowVias(False)
        z.SetDoNotAllowPads(False)
        z.SetDoNotAllowFootprints(False)
        z.AddPolygon(pcbnew.VECTOR_VECTOR2I([B.V(ax - ox * EDGE_BACK, ay - oy * EDGE_BACK),
                                             B.V(bx - ox * EDGE_BACK, by - oy * EDGE_BACK), B.V(cx, cy), B.V(dx, dy)]))
        brd.Add(z)

    # ---- tooling holes in the corners; three fiducials, not symmetric, so the panel has only one way up
    marks = [(PX0 + FID, PY0 + FID), (PX1 - FID, PY0 + FID), (PX0 + FID, PY1 - FID), (PX1 - FID, PY1 - FID)]
    for i, (x, y) in enumerate(marks):
        hole(x, y, 2.0, f"H{i + 1}")
    fids = [(PX0 + 12.0, PY0 + FID), (PX1 - 12.0, PY0 + FID), (PX0 + 12.0, PY1 - FID)]
    for i, (x, y) in enumerate(fids):
        fp = B.load("Fiducial:Fiducial_1mm_Mask2mm")
        fp.SetReference(f"FID{i + 1}")
        fp.SetPosition(B.V(x, y))
        fp.Reference().SetVisible(False)
        fp.Value().SetVisible(False)
        fp.SetAttributes(fp.GetAttributes() | pcbnew.FP_EXCLUDE_FROM_BOM | pcbnew.FP_EXCLUDE_FROM_POS_FILES)
        brd.Add(fp)

    # ---- a line of text in the middle of the bottom rail, clear of the fiducial and the tooling holes there
    t = pcbnew.PCB_TEXT(brd)
    t.SetText("EMG POD rev A   cut the tabs, do not snap them")
    t.SetPosition(B.V((fids[2][0] + marks[3][0]) / 2, (FY1 + PY1) / 2))
    t.SetLayer(pcbnew.F_SilkS)
    t.SetTextSize(pcbnew.VECTOR2I(FromMM(1.0), FromMM(1.0)))
    t.SetTextThickness(FromMM(0.15))
    brd.Add(t)
    bb = t.GetBoundingBox()
    tx0, ty0, tx1, ty1 = [ToMM(v) for v in (bb.GetLeft() - B.V(0, 0).x, bb.GetTop() - B.V(0, 0).y,
                                            bb.GetRight() - B.V(0, 0).x, bb.GetBottom() - B.V(0, 0).y)]
    text_gap = min(math.hypot(max(tx0 - x, 0, x - tx1), max(ty0 - y, 0, y - ty1)) for x, y in marks + fids)
    assert text_gap >= TEXT_CLEAR, f"text {text_gap:.2f} mm from a fiducial or tooling hole"
    pcbnew.SaveBoard(PANEL, brd)

    # ---- files for the order, checks, picture
    files, rows = fab.export(PANEL, OUT, "emg-pod-panel-gerbers")
    same = open(os.path.join(OUT, "cpl-jlcpcb.csv")).read() == open(os.path.join(fab.FAB, "cpl-jlcpcb.csv")).read()
    before, after = copper(SRC), copper(PANEL)
    rpt = os.path.join(B.ROOT, "out", "drc-panel.rpt")
    js = os.path.join(OUT, "drc.json")
    subprocess.run(["kicad-cli", "pcb", "drc", "--severity-all", "-o", rpt, PANEL], capture_output=True)
    subprocess.run(["kicad-cli", "pcb", "drc", "--severity-all", "--format", "json", "-o", js, PANEL], capture_output=True)
    d = json.load(open(js))
    os.remove(js)
    err = [v for v in d.get("violations", []) if v.get("severity") == "error"]
    warn = [v for v in d.get("violations", []) if v.get("severity") != "error"]
    open_ = d.get("unconnected_items", [])
    subprocess.run(["kicad-cli", "pcb", "render", "--side", "top", "--width", "1800", "--height", "1800",
                    "-o", os.path.join(B.ROOT, "out", "panel-top.png"), PANEL], capture_output=True)
    bb = brd.GetBoardEdgesBoundingBox()
    print(f"text on the rail: {text_gap:.1f} mm from the nearest fiducial or tooling-hole centre")
    print(f"frame {ToMM(bb.GetWidth()) - EDGE_W:.2f} x {ToMM(bb.GetHeight()) - EDGE_W:.2f} mm; rails left {FX0 - PX0:g}, "
          f"right {PX1 - FX1:g}, top {FY0 - PY0:g}, bottom {PY1 - FY1:g} mm; slot {GAP:g} mm ({GAP_USB:g} on the right)")
    print(f"{len(TABS)} tabs of {TAB:g} mm with {per_tab} holes of {BITE:g} mm each ({n} holes), 4 tooling holes, 3 fiducials")
    print(f"{files} gerber and drill files, {rows} placements, placement file "
          + ("identical to the single board's" if same else "DIFFERS from the single board's"))
    print(f"copper compared with the single board ({len(before)} tracks, vias, pads and zone fills): "
          + ("identical" if before == after else f"DIFFERENT in {len(before ^ after)} items"))
    print(f"DRC: {len(err)} errors, {len(warn)} warnings, {len(open_)} unconnected")
    for v in (err + warn)[:10]:
        print("  ", v["severity"], v["type"], "|", "; ".join(i["description"][:60] for i in v["items"]))
    return 1 if (err or open_ or not same or before != after) else 0


if __name__ == "__main__":
    sys.exit(main())

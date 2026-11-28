#!/usr/bin/python3
"""Fabrication outputs for JLCPCB from pod/emg-pod.kicad_pcb: Gerbers, drill files, placement file.

    /usr/bin/python3 gen/fab.py

Also writes KiCad's DRC report (out/drc.rpt), two pictures of the board, checks every pad's net against
the design tables, and checks that the routers kept out of the areas reserved for the input lines.
Exits non-zero if any of these fails.
"""
import csv
import os
import shutil
import subprocess
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import board as B  # noqa: E402
import design  # noqa: E402

ROOT = os.path.dirname(HERE)
PCB = os.path.join(ROOT, "pod", "emg-pod.kicad_pcb")
FAB = os.path.join(ROOT, "out", "fab")
LAYERS = "F.Cu,In1.Cu,In2.Cu,B.Cu,F.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts"

# The rotation column is KiCad's own footprint angle, unchanged. JLCPCB's reels do not all share KiCad's
# zero direction, and which packages differ was not checked against a JLCPCB source, so no correction
# is applied here: every polarised part has to be looked at in JLCPCB's placement preview (OPEN.md).
ROTATION_FIX = {}


def check_nets(board):
    """Every pad of the board against gen/design.py. Returns the number of pads checked."""
    import tempfile
    design.build(tempfile.mkdtemp(), "")
    n, wrong = 0, []
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            if pad.GetNumber() == "":
                continue
            want = design.NET[(fp.GetReference(), pad.GetNumber())] or ""
            n += 1
            if pad.GetNetname() != want:
                wrong.append((fp.GetReference(), pad.GetNumber(), pad.GetNetname(), want))
    assert not wrong, wrong[:10]
    return n


QUIET_NETS = ("GND", "AVDD", "+3V3", "VBAT", "BIAS", "RLDINV", "A_RLDOUT", "B_RLDINV", "A_SHIELD", "B_SHIELD")


def check_quiet(board):
    """The areas kept for the input lines, and how close other signals come to those lines.

    Returns (tracks the routers laid inside a reserved area, [(distance mm, net, x, y)] nearest first).
    Distances are between track centre lines and via centres on the same layer, sampled every 0.1 mm.
    """
    import collections
    import math
    import re
    inside = []
    for t in board.GetTracks():
        if isinstance(t, pcbnew.PCB_VIA) or t.IsLocked():
            continue
        for layer, x0, y0, x1, y1 in B.quiet_zones():
            box = pcbnew.BOX2I(pcbnew.VECTOR2I(pcbnew.FromMM(B.OX + x0), pcbnew.FromMM(B.OY + y0)),
                               pcbnew.VECTOR2I(pcbnew.FromMM(x1 - x0), pcbnew.FromMM(y1 - y0)))
            if t.GetLayer() == layer and t.HitTest(box, False):
                p = t.GetStart()
                inside.append((t.GetNetname(), t.GetLayerName(), round(pcbnew.ToMM(p.x) - B.OX, 2),
                               round(pcbnew.ToMM(p.y) - B.OY, 2)))
    is_input = re.compile(r"^[AB]_(E|IN)\d")
    is_quiet = re.compile(r"^[AB]_(VCAP|VREFP|WCT)")
    grid = collections.defaultdict(list)                   # input-line points by layer and 1 mm cell
    other = collections.defaultdict(list)
    for t in board.GetTracks():
        net = t.GetNetname()
        if isinstance(t, pcbnew.PCB_VIA):
            p = t.GetPosition()
            pts = [(pcbnew.ToMM(p.x) - B.OX, pcbnew.ToMM(p.y) - B.OY)]
            layers = (pcbnew.F_Cu, pcbnew.B_Cu)
        else:
            a, b = t.GetStart(), t.GetEnd()
            ax, ay, bx, by = (pcbnew.ToMM(v) for v in (a.x, a.y, b.x, b.y))
            n = max(1, int(math.hypot(bx - ax, by - ay) / 0.1))
            pts = [(ax + (bx - ax) * i / n - B.OX, ay + (by - ay) * i / n - B.OY) for i in range(n + 1)]
            layers = (t.GetLayer(),)
        for lay in layers:
            for x, y in pts:
                if is_input.match(net):
                    grid[(lay, int(x), int(y))].append((x, y))
                elif net not in QUIET_NETS and not is_quiet.match(net):
                    other[net].append((lay, x, y))
    near = []
    for net, pts in other.items():
        best = (9.9, 0.0, 0.0)
        for lay, x, y in pts:
            for cx in (int(x) - 1, int(x), int(x) + 1):
                for cy in (int(y) - 1, int(y), int(y) + 1):
                    for px, py in grid.get((lay, cx, cy), ()):
                        d = math.hypot(px - x, py - y)
                        if d < best[0]:
                            best = (d, x, y)
        if best[0] < 9.9:
            near.append((round(best[0], 2), net, round(best[1], 1), round(best[2], 1)))
    return inside, sorted(near)


def drc():
    """Full DRC, every severity. Returns (errors, warnings, unconnected)."""
    import json
    rpt = os.path.join(ROOT, "out", "drc.rpt")
    js = os.path.join(FAB, "drc.json")
    subprocess.run(["kicad-cli", "pcb", "drc", "--severity-all", "-o", rpt, PCB], capture_output=True)
    subprocess.run(["kicad-cli", "pcb", "drc", "--severity-all", "--format", "json", "-o", js, PCB], capture_output=True)
    d = json.load(open(js))
    os.remove(js)
    err = sum(1 for v in d.get("violations", []) if v.get("severity") == "error")
    warn = sum(1 for v in d.get("violations", []) if v.get("severity") != "error")
    return err, warn, len(d.get("unconnected_items", []))


def main():
    shutil.rmtree(FAB, ignore_errors=True)
    os.makedirs(os.path.join(FAB, "gerber"))
    g = os.path.join(FAB, "gerber")
    subprocess.run(["kicad-cli", "pcb", "export", "gerbers", "--layers", LAYERS, "--subtract-soldermask",
                    "--no-x2", "-o", g + "/", PCB], check=True, capture_output=True)
    subprocess.run(["kicad-cli", "pcb", "export", "drill", "--format", "excellon", "--excellon-units", "mm",
                    "--excellon-separate-th", "--generate-map", "--map-format", "gerberx2", "-o", g + "/", PCB],
                   check=True, capture_output=True)
    shutil.make_archive(os.path.join(FAB, "emg-pod-gerbers"), "zip", g)
    board = pcbnew.LoadBoard(PCB)
    rows = []
    for fp in board.GetFootprints():
        if fp.GetAttributes() & pcbnew.FP_EXCLUDE_FROM_POS_FILES:
            continue
        name = str(fp.GetFPID().GetLibItemName())
        p = fp.GetPosition()
        rot = (fp.GetOrientationDegrees() + ROTATION_FIX.get(name, 0)) % 360
        rows.append((fp.GetReference(), fp.GetValue(), name, round(pcbnew.ToMM(p.x), 4), round(-pcbnew.ToMM(p.y), 4),
                     rot, "top"))
    rows.sort(key=lambda r: (r[0].rstrip("0123456789"), int("".join(c for c in r[0] if c.isdigit()))))
    with open(os.path.join(FAB, "cpl-jlcpcb.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Designator", "Val", "Package", "Mid X", "Mid Y", "Rotation", "Layer"])
        w.writerows(rows)
    shutil.copy(os.path.join(ROOT, "out", "bom-jlcpcb.csv"), os.path.join(FAB, "bom-jlcpcb.csv"))
    for side in ("top", "bottom"):
        subprocess.run(["kicad-cli", "pcb", "render", "--side", side, "--width", "1800", "--height", "1800",
                        "-o", os.path.join(ROOT, "out", f"board-{side}.png"), PCB], capture_output=True)
    pads = check_nets(board)
    inside, near = check_quiet(board)
    err, warn, open_ = drc()
    print(f"{len(os.listdir(g))} gerber and drill files, {len(rows)} placements, {pads} pads on the right nets")
    print(f"DRC: {err} errors, {warn} warnings, {open_} unconnected")
    print(f"router tracks inside the areas kept for the input lines: {len(inside)}" + (f" {inside[:6]}" if inside else ""))
    print("other signals nearest to an input line on the same layer (mm between centre lines, complete up to 1 mm): "
          + (", ".join(f"{net} {d} at ({x}, {y})" for d, net, x, y in near[:6]) or "none"))
    return 1 if (err or open_ or inside) else 0


if __name__ == "__main__":
    sys.exit(main())

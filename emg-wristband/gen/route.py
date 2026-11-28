#!/usr/bin/python3
"""Autoroute the pod: export to Freerouting, bring the result back, fill the planes.

    /usr/bin/python3 gen/route.py <freerouting.jar> [passes]

Reads pod/emg-pod-unrouted.kicad_pcb (from gen/board.py), writes out/route/routed.kicad_pcb,
which gen/finish.py turns into pod/emg-pod.kicad_pcb.
The electrode lines are routed by board.py and locked; Freerouting does the rest.
"""
import os
import shutil
import subprocess
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import board as B  # noqa: E402
POD = os.path.join(os.path.dirname(HERE), "pod")
SRC = os.path.join(POD, "emg-pod-unrouted.kicad_pcb")
DST = os.path.join(os.path.dirname(HERE), "out", "route", "routed.kicad_pcb")


def main():
    jar = sys.argv[1]
    passes = sys.argv[2] if len(sys.argv) > 2 else "30"
    work = os.path.join(os.path.dirname(HERE), "out", "route")
    os.makedirs(work, exist_ok=True)
    dsn, ses = os.path.join(work, "pod.dsn"), os.path.join(work, "pod.ses")
    board = pcbnew.LoadBoard(SRC)
    # The areas kept for the input lines become keep-outs for the router (only on this copy of the board).
    for layer, qx0, qy0, qx1, qy1 in B.quiet_zones():
        k = pcbnew.ZONE(board)
        k.SetIsRuleArea(True)
        k.SetLayer(layer)
        k.SetDoNotAllowTracks(True)
        k.SetDoNotAllowVias(True)
        k.SetDoNotAllowPads(False)
        k.SetDoNotAllowFootprints(False)
        (k.SetDoNotAllowZoneFills if hasattr(k, "SetDoNotAllowZoneFills") else k.SetDoNotAllowCopperPour)(True)
        k.AddPolygon(pcbnew.VECTOR_VECTOR2I([pcbnew.VECTOR2I(pcbnew.FromMM(B.OX + qx), pcbnew.FromMM(B.OY + qy))
                                             for qx, qy in ((qx0, qy0), (qx1, qy0), (qx1, qy1), (qx0, qy1))]))
        board.Add(k)
    # The router keeps copper off the outline only by the track clearance, so give it an outline
    # drawn 0.4 mm inside the real one (this copy of the board is not saved).
    bb = board.GetBoardEdgesBoundingBox()
    for d in list(board.GetDrawings()):
        if d.GetLayer() == pcbnew.Edge_Cuts:
            board.Remove(d)
    m = pcbnew.FromMM(0.45)
    x0, y0, x1, y1 = bb.GetLeft() + m, bb.GetTop() + m, bb.GetRight() - m, bb.GetBottom() - m
    for a, b in (((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))):
        s = pcbnew.PCB_SHAPE(board)
        s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(pcbnew.VECTOR2I(*a))
        s.SetEnd(pcbnew.VECTOR2I(*b))
        s.SetLayer(pcbnew.Edge_Cuts)
        s.SetWidth(pcbnew.FromMM(0.1))
        board.Add(s)
    assert pcbnew.ExportSpecctraDSN(board, dsn), "DSN export failed"
    # Ground is not autorouted: its pads are joined by the pours and planes (gen/finish.py).
    text = open(dsn).read()
    a = text.index("(net GND")
    depth, j = 0, a
    while True:
        depth += {"(": 1, ")": -1}.get(text[j], 0)
        j += 1
        if depth == 0:
            break
    text = text[:a] + "(net GND)" + text[j:]
    open(dsn, "w").write(text)
    if os.path.exists(ses):
        os.remove(ses)
    cmd = ["java", "-Djava.awt.headless=true", "-jar", jar, "-de", dsn, "-do", ses, "-mp", passes, "-mt", "1",
           "-da", f"--router.max_passes={passes}", "--router.job_timeout=00:08:00", "--gui.enabled=false"]
    log = open(os.path.join(work, "freerouting.log"), "w")
    subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, timeout=3000)
    assert os.path.exists(ses), "Freerouting wrote no session file; see out/route/freerouting.log"
    # bring the result back in a fresh interpreter: pcbnew is not reliable after the edits above
    return subprocess.run([sys.executable, os.path.abspath(__file__), "--import"]).returncode


def bring_back():
    ses = os.path.join(os.path.dirname(HERE), "out", "route", "pod.ses")
    shutil.copy(SRC, DST)
    shutil.copy(SRC.replace(".kicad_pcb", ".kicad_pro"), DST.replace(".kicad_pcb", ".kicad_pro"))   # rules, net classes
    board = pcbnew.LoadBoard(DST)
    assert pcbnew.ImportSpecctraSES(board, ses), "SES import failed"
    pcbnew.SaveBoard(DST, board)
    print("tracks and vias:", len(board.GetTracks()))
    return 0


if __name__ == "__main__":
    sys.exit(bring_back() if "--import" in sys.argv else main())

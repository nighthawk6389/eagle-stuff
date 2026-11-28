#!/usr/bin/python3
"""Autoroute the pod: export to Freerouting, bring the result back, fill the planes.

    /usr/bin/python3 gen/route.py <freerouting.jar> [passes]

Reads pod/emg-pod-unrouted.kicad_pcb (from gen/board.py), writes pod/emg-pod.kicad_pcb.
The electrode lines are routed by board.py and locked; Freerouting does the rest.
"""
import os
import shutil
import subprocess
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
POD = os.path.join(os.path.dirname(HERE), "pod")
SRC = os.path.join(POD, "emg-pod-unrouted.kicad_pcb")
DST = os.path.join(POD, "emg-pod.kicad_pcb")


def main():
    jar = sys.argv[1]
    passes = sys.argv[2] if len(sys.argv) > 2 else "30"
    work = os.path.join(os.path.dirname(HERE), "out", "route")
    os.makedirs(work, exist_ok=True)
    dsn, ses = os.path.join(work, "pod.dsn"), os.path.join(work, "pod.ses")
    board = pcbnew.LoadBoard(SRC)
    assert pcbnew.ExportSpecctraDSN(board, dsn), "DSN export failed"
    if os.path.exists(ses):
        os.remove(ses)
    cmd = ["java", "-Djava.awt.headless=true", "-jar", jar, "-de", dsn, "-do", ses, "-mp", passes, "-mt", "1"]
    log = open(os.path.join(work, "freerouting.log"), "w")
    subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, timeout=3000)
    assert os.path.exists(ses), "Freerouting wrote no session file; see out/route/freerouting.log"
    shutil.copy(SRC, DST)
    board = pcbnew.LoadBoard(DST)
    assert pcbnew.ImportSpecctraSES(board, ses), "SES import failed"
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcbnew.SaveBoard(DST, board)
    print("tracks", len(board.GetTracks()))
    return 0


if __name__ == "__main__":
    sys.exit(main())

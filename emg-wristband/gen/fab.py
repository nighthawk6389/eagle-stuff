#!/usr/bin/python3
"""Fabrication outputs for JLCPCB from pod/emg-pod.kicad_pcb: Gerbers, drill files, placement file.

    /usr/bin/python3 gen/fab.py
"""
import csv
import os
import shutil
import subprocess
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PCB = os.path.join(ROOT, "pod", "emg-pod.kicad_pcb")
FAB = os.path.join(ROOT, "out", "fab")
LAYERS = "F.Cu,In1.Cu,In2.Cu,B.Cu,F.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts"

# Angle to add to KiCad's footprint angle so the part sits right in JLCPCB's placement preview.
# These are the usual corrections for JLCPCB's reel orientations; confirm each in the preview.
ROTATION_FIX = {"SOT-23": 180, "SOT-23-5": 180, "SOT-563": 0, "TQFP-64_10x10mm_P0.5mm": 270,
                "CP_EIA-3528-21_Kemet-B": 180}


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
    print(f"{len(os.listdir(g))} gerber and drill files, {len(rows)} placements")
    return 0


if __name__ == "__main__":
    sys.exit(main())

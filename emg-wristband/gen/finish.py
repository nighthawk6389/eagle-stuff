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

PCB = os.path.join(B.POD, "emg-pod.kicad_pcb")
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
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
        z.SetThermalReliefGap(FromMM(0.2))
        z.SetThermalReliefSpokeWidth(FromMM(0.25))
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
    pcbnew.ZONE_FILLER(brd).Fill(brd.Zones())
    pcbnew.SaveBoard(PCB, brd)
    print("zones", len(brd.Zones()))
    return 0


if __name__ == "__main__":
    sys.exit(main())

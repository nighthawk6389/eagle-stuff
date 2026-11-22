"""Run KiCad 7 DRC in a fresh process: python3.12 drc.py out/menorah.kicad_pcb out/drc.rpt"""
import sys, re, collections, pcbnew
pcb, rpt = sys.argv[1], sys.argv[2]
b = pcbnew.LoadBoard(pcb)
pcbnew.WriteDRCReport(b, rpt, pcbnew.EDA_UNITS_MILLIMETRES, True)
c = collections.Counter(re.findall(r"^\[(\w+)\]", open(rpt).read(), re.M))
for k, v in sorted(c.items()):
    print(f"{v:5d} {k}")

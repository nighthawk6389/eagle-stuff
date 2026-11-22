"""Export Specctra DSN for Freerouting: python3.12 route_export.py out/menorah.kicad_pcb out/menorah.dsn"""
import sys, pcbnew
b = pcbnew.LoadBoard(sys.argv[1])
ok = pcbnew.ExportSpecctraDSN(b, sys.argv[2])
print("DSN export", ok)

"""Fabrication outputs for JLCPCB from out/menorah_final.kicad_pcb -> out/fab/

    gerbers + drill (zipped), bom_jlc.csv, cpl_jlc.csv
All parts are on the BACK of the board.  Rotations in the CPL use JLCPCB's bottom-side convention
(180 - KiCad angle) plus a per-part offset (ROT_FIX) fitted to JLCPCB's published footprints.  JLCPCB's
placement preview must still be checked by eye: especially D101..D147, U1, J1, J2, MK1 and every SOT-23.
"""
import collections, csv, os, shutil, subprocess, sys, zipfile
import netlist as N

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "out", "menorah_final.kicad_pcb")
FAB = os.path.join(HERE, "out", "fab")
GER = os.path.join(FAB, "gerber")
LAYERS = "F.Cu,B.Cu,F.Mask,B.Mask,F.Paste,B.Paste,F.SilkS,B.SilkS,Edge.Cuts"

# Extra rotation per LCSC part: the angle that makes the footprint JLCPCB/LCSC publish for that exact part land on
# our pads (fitted against the EasyEDA footprints in the second review, REVIEW2.md N1).  KiCad and JLCPCB draw these
# packages with a different zero orientation.
ROT_FIX = {"C140921": 180, "C15127": 180, "C8545": 180, "C100024": 180,      # SOT-23 / SOT-23-5 (DRV5032, AO3401A, 2N7002, LV1T34)
           "C12044": 270, "C7519": 270, "C51118": 270,                       # TP4057, USBLC6-2, AP2112K
           "C574021": 90}                                                    # ICS-43432
# JLCPCB places by the centre of the pad pattern; for these two KiCad's footprint anchor is somewhere else.
POS_FIX = {"U1": ("70.000000", "-134.380000"), "J1": ("49.770000", "-131.000000")}


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        sys.exit("FAILED: " + " ".join(cmd) + "\n" + r.stdout + r.stderr)


def main():
    shutil.rmtree(FAB, ignore_errors=True)
    os.makedirs(GER)
    run(["kicad-cli", "pcb", "export", "gerbers", "-o", GER + "/", "--layers", LAYERS, PCB])
    run(["kicad-cli", "pcb", "export", "drill", "-o", GER + "/", "--format", "excellon", "--excellon-units", "mm",
         "--excellon-separate-th", "--generate-map", "--map-format", "gerberx2", PCB])
    for f in os.listdir(GER):
        if f.endswith(".gbrjob"):
            os.remove(os.path.join(GER, f))
    with zipfile.ZipFile(os.path.join(FAB, "menorah-v1-gerbers.zip"), "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(os.listdir(GER)):
            z.write(os.path.join(GER, f), f)

    # ---- BOM (JLCPCB format), grouped by part
    groups = collections.OrderedDict()
    for p in N.PARTS:
        if p.get("no_bom") or not p["lcsc"]:
            continue
        groups.setdefault((p["value"], p["fp"], p["lcsc"]), []).append(p["ref"])
    with open(os.path.join(FAB, "bom_jlc.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["Comment", "Designator", "Footprint", "LCSC Part #"])
        for (value, fp, lcsc), refs in groups.items():
            w.writerow([value, ",".join(refs), fp, lcsc])

    # ---- CPL (JLCPCB format) from KiCad's own position file
    pos = os.path.join(FAB, "pos_kicad.csv")
    run(["kicad-cli", "pcb", "export", "pos", "-o", pos, "--format", "csv", "--units", "mm", "--side", "back", PCB])
    rows = list(csv.DictReader(open(pos)))
    bom_refs = {r for refs in groups.values() for r in refs}
    lcsc_of = {r: key[2] for key, refs in groups.items() for r in refs}
    with open(os.path.join(FAB, "cpl_jlc.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
        n = 0
        for r in rows:
            if r["Ref"] in bom_refs:
                # JLCPCB measures bottom-side rotation mirrored: (180 - KiCad angle), as kicad-jlcpcb-tools does
                rot = (180.0 - float(r["Rot"]) + ROT_FIX.get(lcsc_of[r["Ref"]], 0)) % 360.0
                x, y = POS_FIX.get(r["Ref"], (r["PosX"], r["PosY"]))
                w.writerow([r["Ref"], x + "mm", y + "mm", "Bottom", "%.1f" % rot])
                n += 1
    os.remove(pos)
    assert n == len(bom_refs), (n, len(bom_refs))
    print("gerbers:", len(os.listdir(GER)), "files | BOM lines:", len(groups), "| placements:", n)


if __name__ == "__main__":
    main()
